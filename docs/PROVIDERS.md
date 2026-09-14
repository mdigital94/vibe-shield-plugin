# Standalone CLI: providers and models

Status: beta **0.6.0b1**, available from GitHub tag `v0.6.0-beta.1`. Not published on PyPI. The CLI provides advisory reviews; the Claude Code plugin retains its own audits and hooks.

## Install from a source checkout

Requires Python 3.9+, Git, Bash, and grep on macOS/Linux. Check out `v0.6.0-beta.1` to use the published beta; the default branch can receive subsequent documentation or development updates. A virtual environment is recommended:

```bash
git clone --branch v0.6.0-beta.1 https://github.com/mdigital94/vibe-shield-plugin.git
cd vibe-shield-plugin
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install .
vibe-shield providers
```

You can also run `python3 -m vibe_shield` from the checkout root. The package includes the plugin's scripts and patterns: Claude is not required to use the scanner or API adapters.

## Checks without AI

```bash
vibe-shield scan /path/to/project
vibe-shield scan /path/to/project --history
vibe-shield check /path/to/project
```

`scan` exits with 0 for no matches, 2 for findings, or 3 for an incomplete scan. `check` exits with 0 only for a valid, complete gate pass; otherwise it returns 2. A clean scan does not certify an application or create a pass.

## Choose access method, provider, and model

| Mode | Provider | Access | Status |
| --- | --- | --- | --- |
| API | `openai` | `OPENAI_API_KEY` | Chat Completions adapter |
| API | `anthropic` | `ANTHROPIC_API_KEY` | Messages adapter |
| API | `gemini` | `GEMINI_API_KEY` | generateContent adapter |
| API | `ollama` | Configured API runtime | Chat adapter; defaults to loopback |
| API | `openai-compatible` | `VIBE_SHIELD_API_KEY` and `--endpoint` | Chat Completions protocol |
| CLI | `claude` | Access already configured in the CLI | Requires a version supporting `--safe-mode` and isolation options |
| CLI | Codex, Gemini, Ollama | — | Adapters unavailable: full isolation has not been verified |

API and CLI access are separate choices. A chat subscription does not automatically include API credits. The Claude CLI uses its configured access, which may be a subscription or an API key. Vibe Shield does not copy credentials. Set keys in the environment through your secrets manager; do not put them in project files or command arguments.

`--model` is required and is passed to the provider without fallback or substitution. Supply a text model identifier compatible with the selected API and available to your account; the tool does not maintain a universal model catalog. Protocol compatibility does not mean every service and model has been tested. `--endpoint` is supported only for Ollama and OpenAI-compatible services: use an HTTPS base URL, or HTTP on loopback. API requests reject credentials in URLs and redirects, and do not inherit proxy settings.

The missing CLI adapters are not considered impossible: their file access and tool execution need to be verified first. Read-only mode alone does not necessarily restrict reads to the selected files. Use the available API adapter for those providers.

## Preview before explicitly sending

```bash
vibe-shield review /path/to/project --mode api --provider openai \
  --model YOUR_MODEL --file src/app.py --file src/auth.py
```

Without `--execute`, this only displays the file manifest: no network access, no CLI invocation, and no gate changes. Select project-relative files, not directories. Add `--execute` to the same command to make the request: this authorizes sending the content and any costs associated with the selected access method.

Using an already configured CLI:

```bash
vibe-shield review /path/to/project --mode cli --provider claude \
  --model YOUR_MODEL --file src/app.py --execute
```

Using a local Ollama runtime with an available model:

```bash
vibe-shield review /path/to/project --mode api --provider ollama \
  --model YOUR_MODEL --file src/app.py --execute
```

For a compatible endpoint, use `--provider openai-compatible --endpoint https://service.example/v1`. The tool appends `/chat/completions`; Ollama appends `/api/chat`. Selecting a remote Ollama endpoint sends code off your computer.

## Data, limits, and outcomes

- Only explicitly selected files enter the prompt: up to 32 files and 64 KiB combined by default. `--max-input-bytes` supports up to 256 KiB. Content is not silently truncated.
- Sensitive filenames, credential directories, binary files, and symlinks are rejected. Known secret formats, credential assignments, and API keys from the environment are masked; this does not guarantee detection of every private value. Review what you authorize for transmission.
- API requests include no tools. The Claude CLI runs in a temporary directory with tools, skills, MCP, and customizations disabled. The CLI continues to manage login. Model-suggested changes are not applied.
- `--timeout` limits socket inactivity for APIs and total process time for the CLI; the default is 60 seconds. `--max-output-tokens` requests a provider output limit (default: 2000). For the CLI, this is a per-response limit, not a total cap: Claude's internal continuations can exceed it. The adapter adds no retries or fallbacks; the CLI's internal behavior still applies.
- `review` is **advisory and limited to selected files**, not a full-stack audit. Execution invalidates the previous pass and never writes PASS, even when the model reports no issues. If selected files change during the request, the result is incomplete.
- JSON reports include the provider, requested and returned model when known, file hashes, measured duration, available usage counters, and masked text. Model output is treated as untrusted data. Exit 0 means the review completed, **not permission to publish**; errors and limits produce exit 3.
- Claude CLI output is read as `stream-json`: completed text blocks are assembled in received order, using block identifiers to handle duplicates, retractions, and replacements. The final `result` field is not appended again. Thinking, synthetic messages, and child-agent output are excluded. `response_segments` counts retained blocks; `response_complete` indicates verified response termination, not audit completeness.
- After a timeout, error, or malformed stream, already verified blocks remain in the report, masked, with status `incomplete` and exit 3. A block still being generated or a truncated JSON line is not reconstructed by guesswork. Without a final result, usage counters are unknown. The raw stream is not saved.
- Missing token counts are null, not zero. OpenAI/Gemini include cached tokens in input counts; Anthropic reports them separately. Do not indiscriminately add input and cache counts. The tool does not estimate monetary costs, subscription quota usage, or savings between models.

## Verification and remaining work

Automated tests cover simulated transports and processes, file selection, errors, and regressions; the package has been checked outside the source checkout. The first authorized live test used Claude CLI with an existing subscription and the `fable` alias, returned as `claude-fable-5-1`. On macOS, the adapter also preserves `USER`, which the CLI needs to retrieve its login from Keychain. Other providers and models still require live testing, and isolated adapters for other CLIs remain to be built.

A full audit command and blocking integrations for other hosts require additional coverage orchestration: a single AI review does not replace dependency scanning, independent verification, or publication checks.

## Response detail and usage

`--detail concise` is the default: findings with evidence, location, and remediation, plus essential limitations. `--detail detailed` retains the extended format. Brevity is a request to the model, not a hard limit: findings are not cut off to meet a length target. In concise mode, the model receives paths and text; hashes remain in the local report. See the [exploratory comparison](BENCHMARK.md).

Source and report masking are separate. In reports, inline code and fenced code blocks are processed separately from prose: sensitive values remain masked without automatically removing the rest of a finding. `review_redacted` indicates text changes; a report with no available review text is marked incomplete. This availability check does not assess the answer's correctness. Masking remains heuristic and does not guarantee detection of every secret.
