# Contributing to Vibe Shield

This experimental beta welcomes minimal reproductions, fixes to the guards, clearer documentation, and evidence about token usage. Before proposing a large feature, open an issue describing the concrete problem and expected outcome.

For vulnerabilities, follow [SECURITY.md](SECURITY.md). For ordinary issues, include the plugin and host versions, operating system, reproduction steps, and expected and observed results. Use temporary repositories and synthetic credentials; remove personal paths, private logs, and customer data.

## Changes and verification

1. Keep each change focused on the problem it addresses and update the related documentation.
2. For a functional defect, add a test that reproduces the incorrect behavior and verifies the fix. Tests must not publish anything or access real credentials.
3. Run `python3 -m unittest discover -s tests` from the repository root. Bash, Git, and Python 3.9+ are required for the full suite.
4. If you change hooks or installation, also follow [TESTING.md](TESTING.md). Distinguish direct script tests from automatic execution in the host.
5. In your pull request, describe the problem, the change, the checks you ran, and remaining limitations. Do not claim checks you did not run.

The Python runtime uses the standard library. The plugin workflow checks regressions and secrets; the template in `templates/` is intended for users' projects and must be adapted to their dependencies. AI results depend on the model and are not validated by the guard test suite alone.

Contributions are distributed under the repository's [MIT license](LICENSE).
