# Vibe Shield — Tester guide

Vibe Shield 0.6.0-beta.1 is experimental. It provides a standalone CLI and a Claude Code plugin to assist with security checks before publication: secret scanning, AI-assisted audits with adversarial verification, guards for intercepted risky commit and deployment commands, and guided fixes. Reports aim to be understandable to people without a security background. The plugin contains nine skills, five specialized agents, and PreToolUse/PostToolUse hooks backed by Bash and Python scripts.

## Requirements

- A recent Claude Code CLI on macOS or Linux for plugin tests (`claude --version`; tested with 2.1.198).
- Bash, Git, grep, and Python 3.9+ for the standalone CLI and full test suite. The plugin's guard scripts require Python 3.8+. Stack scanners (such as npm audit or pip-audit) and access to their databases are required to complete the corresponding audit; missing checks must leave the gate incomplete.

## Plugin installation

Use the download or clone instructions in the [README](README.md), then:

1. In a Claude Code session:
   ```
   /plugin marketplace add /path/to/vibe-shield-plugin
   /plugin install vibe-shield@vibe-shield-marketplace
   /reload-plugins
   ```
2. Verify that `/vibe-shield:security-help` responds.

To uninstall: `/plugin uninstall vibe-shield` and `/plugin marketplace remove vibe-shield-marketplace`.

## Suggested test path

In a test project, or a copy of a real project:

1. Run `/vibe-shield:setup-security` for preventive hardening.
2. Ask Claude to write a fake key in a recognized format to a file (for example, `sk_live_...` with 24+ characters). The hook should immediately warn you.
3. Ask Claude to commit that file. The commit should be BLOCKED, including when `git add X && git commit` is issued as a single command.
4. Ask Claude to push. It should be blocked until `/vibe-shield:pre-deploy` passes.
5. Run `/vibe-shield:security-audit` on a project with known vulnerabilities (concatenated SQL, inappropriate wildcard CORS, missing RLS where required, etc.). Assess the report's quality and false positives.
6. If you own a live website, run `/vibe-shield:post-deploy-check https://your-site.example` with its actual URL.

## Adversarial testing

If you have security experience, test the protections themselves:

- Secret formats missed by the patterns in `scripts/patterns-exact.grep`.
- Commit or publication paths that bypass the hooks: compound commands, aliases, wrapper scripts, and tools other than Bash.
- Disruptive false positives. `.vibe-shield/allowlist` accepts one extended regular expression per line.
- Prompt injection: can a malicious project file persuade the agents to ignore or fabricate a finding?
- Audit quality: inflated or missed findings, incorrect severity, and the effectiveness of adversarial verification.
- Script robustness in `scripts/`: JSON parsing, exploitable fail-open behavior, and Git edge cases.

The hooks cover only intercepted operations within Claude Code. The CI template (`templates/security-ci.yml`) provides additional checks outside that path. The documented `VIBE_SHIELD_SKIP=1` bypass is an intentional design choice.

## Feedback

For each problem, describe what you did, what you expected, and what happened. Include only relevant, sanitized output. Follow [SECURITY.md](SECURITY.md) for private vulnerability reports.

## Automated regression tests

From the repository root:

```bash
python3 -m unittest discover -s tests
```

Tests use temporary repositories and synthetic credentials; never publish real secrets to test the tool. Check at least: a secret staged but removed from the working tree, an already committed secret, chained commit and push commands, `git -C` targeting another repository, changes after approval, approval expiration even on the same HEAD, and failures that invalidate an earlier approval. These guard tests do not replace real testing in the host.

## Skill workflows and usage

1. An audit limited to one folder must produce a partial report and leave the gate incomplete.
2. A missing scanner, network/database error, or interrupted verification must prevent approval even when there are no findings.
3. Pre-deploy must reuse only a valid, complete audit of the same content. A failed additional check must leave the gate blocked.
4. Fix-security must require renewed verification and complete coverage; setting finding counts to zero is insufficient to grant approval.
5. Compare old and new audits using the same fixture, model, and host configuration in separate sessions. Record input/output/cache tokens where available, duration, delegation count, coverage, confirmed findings, and missed known vulnerabilities. Separate the first audit from pre-deploy reuse. Repeat across multiple stacks before concluding that savings preserve quality.
6. If the host does not expose tokens or timings, record “unavailable.” Do not infer a percentage saving from the number of agents alone.

Agents must inherit the session model and honor explicit overrides. Verify this in the host as well. The presence of skills in a host other than Claude Code does not prove that it executes the hooks.

### Scanner behavior and coverage

`scan-secrets.sh .` returns 0 for no matches, 2 for findings, and 3 for incomplete scans or errors. `scan-secrets.sh --history --all` checks available history and reports a shallow clone as incomplete. Secret values are not printed. Identical historical blobs are scanned once per content value; names and allowlist rules are still evaluated separately.

CI template tests verify routing and thresholds with simulated commands. They do not replace a GitHub workflow run or access to scanner databases.

### GitHub prereleases

The gate supports only `gh release create TAG --verify-tag --prerelease --repo https://github.com/OWNER/REPO --notes "Short notes"`, with an optional `--title "Title"`. The explicit repository must match origin; the local tag must identify HEAD and exactly match the remote tag. Modified tracked files, assets, alternative targets, generated notes or notes supplied through a file option, metadata containing possible secrets, and unrecognized options block publication. A valid complete audit and pre-deploy check remain mandatory.

Tests cover the valid path and rejection of missing audits, mismatched tags, changed content, risky metadata, and unsupported options. Remote tag verification is simulated in automated tests; actual publication queries origin.

## Standalone CLI beta 0.6

The final local suite for 0.6.0-beta.1 contains 160 tests. The wheel was installed in an isolated environment outside the checkout, with checks for the version, provider listing, scanner, and preview. The 0.6 plugin was installed in a temporary Claude configuration. Model evaluations and their limitations are documented in [docs/BENCHMARK.md](docs/BENCHMARK.md). CI also builds and installs the wheel on Linux/macOS with Python 3.9/3.12.
