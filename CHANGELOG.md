# Changelog

## Unreleased — documentation

- English README, public guides, issue templates, and marketplace descriptions.
- Default branch aligned with the current experimental beta; existing release tags remain unchanged.

## 0.6.0-beta.1 — experimental prerelease

- Installable Python CLI (package version 0.6.0b1): local scanners and advisory reviews with an explicit provider and model, with preview enabled by default.
- Multiple API providers or Claude CLI login; other CLIs are not yet supported.
- Claude response collection handles continuation blocks, retractions, and duplicates; errors and timeouts preserve partial text without approving the gate.
- Sensitive-value masking preserves parseable Python expressions, with a conservative fallback for ambiguous formats.
- Structured concise responses by default, an optional detailed mode, and a documented exploratory comparison.
- Synthetic benchmark suite and documented limitations; no promise of complete security or universal coverage.

## 0.5.1-beta.2 — prerelease

- Restricted support for GitHub prereleases from a verified local/remote tag pointing to approved content, without assets.
- Documented a real hook test in a separate Claude session on the beta.1 candidate.
- Distinguished beta download instructions from instructions for the default branch.
- Beta.1 CI passed; external human testing and a controlled token-usage comparison were still pending at this release.

## 0.5.1-beta.1 — candidate

- Fixed scanning of annotated tag metadata when pushing an explicit identifier.
- Added support for local tree/blob references, including Codex checkpoints; their contents are scanned, while submodules remain incomplete.
- Changes to application code within `.vibe-shield/` also invalidate approval.
- Prepared the MIT license, disclosure policy, issue templates, and cross-platform CI.
- Removed an unnecessary email address from current marketplace metadata without rewriting public history.

## 0.5.0 — beta, release preparation

### Reliability

- Approval is bound to the repository and its contents and remains valid for less than 30 minutes; approvals from 0.4.x cannot be reused.
- Partial, failed, or incomplete audits keep publication blocked; pre-deploy preserves the original expiration time when reusing an audit.
- Checks cover content intended for a commit and objects in Git history, with conservative handling of compound commands, different repositories, and unsupported configurations.
- A suite of 46 regression tests covers verified guard and CI template behavior.

### Auditing and usage

- Scanners run before AI analysis, specialists are engaged as needed, and related findings are independently verified in small groups.
- The model is inherited from the session rather than forcing the most expensive model.
- Token savings had not yet been demonstrated in a controlled comparison; no percentage was promised.

### Distribution preparation

- MIT license, beta instructions and limitations, security policy, contribution guide, and issue templates.
- Linux/macOS regression workflow and secret scanning, with actions pinned to commits and read-only permissions.

The private reporting channel was enabled and verified on 2026-09-11. At this preparation stage, the GitHub workflow run and installation by an external tester still needed verification before candidate promotion. This historical entry records prepared changes and does not establish that a release had been published at that point.
