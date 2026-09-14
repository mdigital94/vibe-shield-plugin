# Security reporting

## Scope and supported versions

Vibe Shield is an experimental beta that assists with development security checks. Fixes target the latest beta; older versions are not maintained. Version 0.5.0 invalidates approvals from 0.4.x and requires a new audit.

Relevant reports include vulnerabilities in the scripts, data exposure, and reproducible ways to obtain an invalid approval within the documented workflows. The plugin is not a security boundary against someone who can modify its files or disable its hooks. See the README for coverage limitations.

## Private disclosure

Use [Report a vulnerability](https://github.com/mdigital94/vibe-shield-plugin/security/advisories/new) to send a private report to the maintainers. This GitHub channel was enabled and verified on 2026-09-11. Do not open public issues containing exploitable details, secrets, complete logs, or customer data.

If the channel becomes unavailable, open only a generic issue asking for a private contact method; do not include vulnerability details.

In your private report, include the plugin and host versions, operating system, expected and observed behavior, and a minimal reproduction using synthetic data. Describe the impact and required conditions. Test only systems you own or are authorized to assess.

If you have exposed a real credential, revoke it with its provider before reporting it. Do not send its value. No response times or rewards are promised; coordinate public disclosure of the details after assessment and remediation.
