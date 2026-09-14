# 🛡️ Vibe Shield

**Security checks for AI-assisted development, with your choice of provider and model.**

Local secret scanning, AI reviews of selected files, and a Claude Code plugin with commit and publication checks. Standalone AI reviews are advisory: they do not authorize a release on their own.

**Experimental beta · 0.6.0-beta.1 · [MIT license](LICENSE)**

The software is free. Model usage may consume a subscription allowance or incur API charges. No tool can guarantee complete security.

[Install](#install-the-cli) · [Providers and limitations](docs/PROVIDERS.md) · [Benchmarks and token usage](docs/BENCHMARK.md) · [Report a vulnerability](SECURITY.md)

## Install the CLI

The standalone CLI requires Python 3.9+, Git, Bash and grep on macOS or Linux. In a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install "git+https://github.com/mdigital94/vibe-shield-plugin.git@v0.6.0-beta.1"
vibe-shield --version
vibe-shield scan /path/to/project
```

The Python package version is `0.6.0b1`. It is not published on PyPI; use the explicit Git reference above. Secret scanning stays local.

To use an existing Claude Code login:

```bash
vibe-shield review /path/to/project --mode cli --provider claude \
  --model YOUR_MODEL --file src/app.py
```

This previews the request without sending code. Add `--execute` to request an AI review. Responses are concise by default; use `--detail detailed` for an extended response.

API adapters support OpenAI, Anthropic, Gemini, Ollama and OpenAI-compatible endpoints. Subscription-based CLI execution currently supports Claude only. See [provider setup, credentials and limitations](docs/PROVIDERS.md).

## Install the Claude Code plugin

Use a full clone at the release tag for a reproducible installation:

```bash
git clone --branch v0.6.0-beta.1 https://github.com/mdigital94/vibe-shield-plugin.git vibe-shield
claude plugin marketplace add ./vibe-shield
claude plugin install vibe-shield@vibe-shield-marketplace
```

The tag identifies the released beta; the default branch may receive documentation or development updates. Do not use `--depth` when you need to scan the entire Git history. If the marketplace is already registered, check its source before changing it.

Restart Claude Code and run `/vibe-shield:security-help`, then `/vibe-shield:security-audit`. Before relying on automatic blocks, follow the [temporary-project test procedure](TESTING.md). Available skills do not prove that hooks are running. Hook execution in other hosts and on Windows has not been verified end to end.

This update makes the public documentation English. Plugin instructions and some CLI messages currently remain in Italian; ask the assistant for reports in your preferred language. This is not a fully localized runtime.

## What it checks

Three layers operate in sessions where the host loads and executes the hooks:

1. **While editing:** the write hook can flag credentials in a file. Remediation then requires the assistant to act.
2. **Before commits:** intercepted `git commit` commands check the content being committed. Detected secrets or sensitive files block the commit with remediation instructions.
3. **Before publication:** supported push and deployment commands require a complete, passing security audit that is less than 30 minutes old **and** matches the repository and content identity. Critical, high and medium findings must be resolved. Unsupported commands or options remain blocked even with a valid audit. GitHub prereleases have [additional constraints](TESTING.md).

## Plugin commands

| Command | Purpose |
| --- | --- |
| `/security-audit` | Run deterministic scanners first, review code and configuration, and involve specialists where useful. Medium or higher findings receive independent verification in related groups. Partial audits do not unlock publication. |
| `/pre-deploy` | Validate the full audit and check the actual publication contents, build, configuration and destination. |
| `/fix-security` | Apply suitable fixes and explain changes that need a decision. |
| `/secrets-scan` | Find and help remove exposed credentials, including in Git history. |
| `/setup-security` | Set up preventive controls such as ignore rules, environment handling, security headers and stack-specific checks. |
| `/security-help` | Explain findings, blocked actions and security terms. |
| `/second-opinion` | Optionally request an external model's opinion. Runs only when explicitly requested; see the limitations below. |
| `/post-deploy-check` | Perform passive checks on an authorized live site: headers, exposed files, source maps, cookies and error pages. |
| `/incident-response` | Guide containment, credential revocation, investigation and remediation after an incident. |

If a short command is unavailable, use its namespace, such as `/vibe-shield:security-audit`.

## Included specialists

| Agent | Scope |
| --- | --- |
| `secret-scanner` | Credentials, sensitive files and Git history |
| `code-auditor` | Injection, XSS, authorization, IDOR, SSRF, uploads and cryptographic weaknesses |
| `dependency-auditor` | Vulnerable dependencies, suspicious packages and typosquatting |
| `config-auditor` | CORS, headers, cookies, debug settings, database access rules, Docker and CI/CD |
| `finding-verifier` | Independently inspect evidence and confirm, reject or flag uncertain findings |

Agents inherit the session model. The plugin does not force a more expensive model. Explicit model requests are honored where supported by the host; model choice alone does not demonstrate audit quality.

## Token usage

The audit workflow collects the project inventory once, runs deterministic scanners before AI review, and passes concise results to the model. Specialists receive bounded tasks rather than being started for every audit. Related findings share a verifier. Pre-deploy can reuse a complete audit only while its content identity and 30-minute validity window still hold.

Savings from those workflow changes have not been established in a controlled comparison. A separate, exploratory six-case comparison of the standalone CLI's response formats observed **8.9% fewer reported total tokens** with concise output on one model. The [benchmark report](docs/BENCHMARK.md) documents the small sample, AI-assisted grading, replaced runs and all 17 calls. This is not a general savings or accuracy guarantee.

Unavailable scanners, unreachable advisory databases or exhausted budgets leave the audit incomplete. Reviewing only a diff does not authorize the whole project. Duration and token counts are recorded only when available from the host.

## Optional external opinions

The `/second-opinion` skill can guide the use of installed Gemini CLI, Codex CLI or Ollama tools on request. Cloud reviews require consent before code excerpts are sent. A locally configured Ollama endpoint can keep inference on the machine; check the endpoint before assuming it is local.

This older, assistant-guided skill is separate from the standalone CLI's isolated Claude adapter. It does not provide the same tool, MCP or attachment isolation guarantees. External opinions remain advisory and do not alter the publication gate. Redaction reduces exposure but cannot guarantee that every sensitive value or format is removed.

## Resolving a block

- **Commit blocked:** remove sensitive files from the staging area or move credentials to appropriate local configuration, then retry. Use `/secrets-scan` for guided remediation; revoke exposed credentials where needed.
- **Push or deployment blocked:** run `/pre-deploy`. Publication is allowed only after the required checks pass and while the audit remains valid. Failed extra checks invalidate the previous approval.
- **Explicit bypass:** `VIBE_SHIELD_SKIP=1` disables the local blocks for a command. It is a bypass, not a successful audit.

## Local audit files

The plugin writes `.vibe-shield/` inside the project. Exclude it from Git as part of setup.

- `report.md`: the latest full audit report.
- `status.json`: local audit status, coverage, timestamp, content identity and finding counts. It is not a cryptographic signature or tamper-resistant proof.
- `allowlist`: optional regular expressions, one per line, for recurring false positives in commit checks and guided scanning. Lines beginning with `#` are comments. The final publication scan is conservative and does not apply these exceptions.

## Coverage outside the host

Hooks cover only the tools and commands intercepted by the host. External terminals, aliases, wrapper scripts and other tools may fall outside that coverage. A skill appearing in Codex or another host does not demonstrate that Claude Code hooks execute there.

The `/setup-security` skill can also install a GitHub Actions security workflow and Dependabot configuration in the user's project. Review their coverage for the actual technology stack. These checks complement local controls, including for changes made by other contributors or through GitHub.

Dependencies can acquire new vulnerability advisories without any source change. The generated workflow includes weekly checks; repeat full audits when appropriate for the project's exposure and changes.

## Requirements and limitations

- The standalone CLI requires Python 3.9+. Plugin gate scripts require Python 3.8+, Bash, Git and grep on macOS/Linux. Stack-specific vulnerability scanners must be available to complete the relevant audit coverage.
- Pattern matching misses some secrets; AI reviews can miss vulnerabilities or produce false positives. Findings need evidence and verification.
- The dispatcher supports specific direct commands. Compound commands, ambiguous Git options and unsupported deployment destinations are blocked. Run staging, commit and publication separately.
- Automatic publication checks require a Git repository with complete history. Shallow clones, submodules and non-Git deployments need separate verification. All local references are scanned, including branches that are not being pushed.
- The audit snapshot covers tracked files, the staging area, Git references, plugin rules and local ignored content, including build output, with exclusions for generated internal reports and some dependency/cache directories. The publication secret scan covers history and non-ignored files. Pre-deploy must inspect the actual distributed output and relevant remote configuration.
- A valid local snapshot does not attest to later changes in cloud settings, remote services or advisory databases.
- Local blocks are not a security boundary against someone who controls the machine. Provider permissions and independent CI controls still matter.
- Automated regressions test covered behavior, not overall vulnerability detection accuracy. External user testing and broader model comparisons are still needed.

## Validation and contributing

The 0.6.0-beta.1 release passed **160 automated tests**, wheel build/install checks and CI on Linux/macOS with Python 3.9/3.12, including Git history secret scanning. Installation from the public Git tag was verified in temporary Python and Claude plugin environments. See the [release CI](https://github.com/mdigital94/vibe-shield-plugin/actions/runs/34879561284), [test procedure](TESTING.md) and [benchmark methodology](docs/BENCHMARK.md).

Earlier host testing verified that a downloaded plugin allowed a read-only Git command and blocked a synthetic-secret commit and a push without an audit in a temporary Claude session. This was a local test, not an independent external-user trial.

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md). Use [issues](https://github.com/mdigital94/vibe-shield-plugin/issues) for ordinary bugs and [private security reporting](SECURITY.md) for vulnerabilities. Do not upload credentials, complete session logs or private customer code.

## Repository layout

```text
vibe_shield/       standalone Python CLI and provider adapters
.claude-plugin/    plugin and marketplace manifests
skills/            nine assistant-guided commands
agents/            five specialist roles
hooks/             host hook configuration
scripts/           gate and secret-scanning scripts
benchmarks/        synthetic benchmark cases and runner
templates/         security CI and Dependabot templates
tests/             automated regressions
docs/              provider and benchmark documentation
```
