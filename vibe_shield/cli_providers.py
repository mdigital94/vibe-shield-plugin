"""Non-interactive CLI review with no model tools (POSIX only).

Claude flags: https://code.claude.com/docs/en/cli-reference
Only reviewed text goes on stdin. Authentication stays with the user's CLI.
"""
import math
import os
import selectors
import shutil
import signal
import subprocess
import tempfile
import time

from .contracts import ProviderError, ReviewResult
from .cli_stream import parse_stream

MAX_STREAM_BYTES = 1_048_576
MAX_PROMPT_BYTES = 1_048_576
SUPPORTED_CLI_PROVIDERS = ("claude",)


class _ProcessFailure(ProviderError):
    def __init__(self, message, output):
        super().__init__(message)
        self.output = output


def _kill_group(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def _execute(argv, prompt, cwd, env, timeout):
    """Bound both pipes while writing input; kill descendants on all exits."""
    try:
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, cwd=cwd, env=env,
                                   start_new_session=True)
    except OSError:
        raise ProviderError("Impossibile avviare il CLI selezionato.") from None
    output = bytearray()
    sizes = {"stdout": 0, "stderr": 0}
    remaining = memoryview(prompt)
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            for pipe, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, name)
            os.set_blocking(process.stdin.fileno(), False)
            if remaining:
                selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
            else:
                process.stdin.close()
            while selector.get_map():
                left = deadline - time.monotonic()
                if left <= 0:
                    raise ProviderError("Timeout del CLI: revisione interrotta.")
                for key, _ in selector.select(min(left, 0.1)):
                    if key.data == "stdin":
                        try:
                            sent = os.write(key.fd, remaining[:8192])
                            remaining = remaining[sent:]
                        except BrokenPipeError:
                            remaining = memoryview(b"")
                        if not remaining:
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                        continue
                    block = os.read(key.fd, 8192)
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    sizes[key.data] += len(block)
                    if sizes[key.data] > MAX_STREAM_BYTES:
                        raise ProviderError("Output del CLI oltre il limite: revisione interrotta.")
                    if key.data == "stdout":
                        output.extend(block)
            left = deadline - time.monotonic()
            if left <= 0:
                raise ProviderError("Timeout del CLI: revisione interrotta.")
            try:
                code = process.wait(timeout=left)
            except subprocess.TimeoutExpired:
                raise ProviderError("Timeout del CLI: revisione interrotta.") from None
            if code != 0:
                raise ProviderError("Il CLI ha rifiutato la richiesta; revisione incompleta.")
            return bytes(output)
    except ProviderError as error:
        raise _ProcessFailure(str(error), bytes(output)) from None
    finally:
        _kill_group(process)
        for pipe in (process.stdin, process.stdout, process.stderr):
            pipe.close()


def run_cli(provider, model, prompt, *, timeout=60, max_output_tokens=2000) -> ReviewResult:
    if provider not in SUPPORTED_CLI_PROVIDERS:
        raise ProviderError("CLI non supportato: isolamento completo di tool, estensioni e contesto non verificato. Usa la modalità API.")
    if os.name != "posix":
        raise ProviderError("L'adattatore CLI richiede macOS o Linux per isolare il gruppo di processi.")
    if not isinstance(model, str) or not model.strip() or model.startswith("-") or any(ord(c) < 32 for c in model):
        raise ProviderError("Seleziona esplicitamente un modello valido.")
    if not isinstance(prompt, str):
        raise ProviderError("Il testo della revisione deve essere una stringa.")
    encoded = prompt.encode("utf-8")
    if len(encoded) > MAX_PROMPT_BYTES:
        raise ProviderError("Testo della revisione oltre il limite del CLI.")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise ProviderError("Timeout non valido (massimo 3600 secondi).")
    if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 64000:
        raise ProviderError("Limite token non valido (da 1 a 64000).")
    executable = shutil.which(provider)
    if not executable:
        raise ProviderError("CLI non installato o non disponibile nel PATH.")
    # Preserve native login location; do not copy credentials or inherit model,
    # plugin, node-loader, shell-hook, session, or permission overrides.
    # Claude uses USER to locate the native macOS Keychain login.
    allowed = ("HOME", "USER", "PATH", "LANG", "LC_ALL", "TMPDIR", "XDG_CONFIG_HOME",
               "CLAUDE_CONFIG_DIR", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY",
               "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE")
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(max_output_tokens)
    env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    argv = [executable, "--print", "--model", model, "--safe-mode", "--tools", "",
            "--setting-sources", "", "--settings", '{"disableAllHooks":true}',
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--disable-slash-commands", "--no-session-persistence", "--no-chrome",
            "--max-turns", "1", "--output-format", "stream-json", "--verbose"]
    process_error = None
    with tempfile.TemporaryDirectory(prefix="vibe-shield-review-") as cwd:
        try:
            raw = _execute(argv, encoded, cwd, env, timeout)
        except _ProcessFailure as error:
            raw, process_error = error.output, str(error)
    return parse_stream(raw, process_error)
