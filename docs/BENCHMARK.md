# Beta 0.6 evaluation

These results concern small synthetic projects and do not certify application security. The suite contains 30 cases: 12 vulnerable/fixed pairs, 2 scanner cases, and 4 attempts to manipulate the reviewer. Expected answers stay outside the files sent to the model.

## Observations

The first run with Claude CLI and `fable` (returned as `claude-fable-5-1`) produced 27 reports from 28 reviews; one case was refused twice. Successful reports declared 286,035 tokens, including input, output, cache reads, and cache writes. Usage from failed attempts is unavailable, so actual total usage is incomplete. Tokens do not measure monetary cost or the percentage of a subscription quota.

An AI-assisted assessment, not an independent human review, identified 14 original reports that began mid-sentence. In two other cases, masking hid part of the evidence. We do not publish precision or recall for that run: attributing those omissions to the model would be misleading.

Stream collection was fixed. Three cases were rerun without increasing the output limit: all produced complete reports, including one assembled from two blocks. The revised masking preserves relevant Python expressions while hiding sensitive literal values. It does not preserve every language in the same way; ambiguous formats are handled conservatively.

## Exploratory comparison of concise responses

The sample was selected before execution: c01/c02 (SQL), c13/c14 (HTML), c21 (password logging), and c29 (logging and an unauthorized read instruction). Each case was scheduled once per condition, detailed and concise, alternating their order. Source, masking, model, Claude access, output limit of 2000 per response, and 180-second timeout were held constant. The initial plan allowed up to 12 calls, with no automatic retries; additional diagnostic reruns are disclosed below.

Reports are assessed against each case's rubric, distinguishing demonstrated findings, hypotheses, and optional hardening. A single repetition does not estimate variability or establish statistical significance, equivalent quality, or generalizable savings. Cache behavior can vary between requests. The results are an exploratory measurement of the final cohort below.

### Final sample results

| Measure (6 cases per format) | Detailed | Concise |
| --- | ---: | ---: |
| Output tokens | 8250 | 5243 |
| Uncached input tokens | 12 | 12 |
| Cache read tokens | 3654 | 3654 |
| Cache write tokens | 20999 | 21089 |
| Sum of token categories | 32915 | 29998 |
| Combined call duration, seconds | 149.778 | 106.131 |

Observed difference: 36.4% fewer output tokens and 8.9% fewer tokens across the summed categories. This is not a savings guarantee: there was one repetition, latency and cache behavior vary, and no statistical inference was performed.

During verification, four logging responses were excluded from assessment and rerun because report masking removed evidence. The concise c29 condition needed a second rerun for a different quotation-mark ambiguity. The final cohort uses the eight initial reports for the first four cases and the latest four usable reports for the two logging cases. Generation settings stayed the same; local processing of returned text changed. Original results were retained, not silently replaced.

The complete experiment required **17 calls and 88,923 reported tokens**, including discarded responses. The twelve responses in the final cohort are only the basis for comparison; they do not represent all usage incurred.

The AI-assisted assessment of the final cohort recognized the same four expected issues in both formats and produced consistent judgments on the two fixed cases. This was not a blinded human review: it does not establish absence of false positives, general equivalence, or coverage beyond these examples.

## Reproduction

Methods and commands are in [benchmarks/README.md](../benchmarks/README.md). Use a checkout of the published `v0.6.0-beta.1` tag; the default branch can receive subsequent documentation or development updates. The `--detail concise` and `--detail detailed` options select the conditions; use separate result directories. Human annotations and independent verification remain necessary before treating precision/recall as evidence of quality.

The automated suite also checks secrets, gates, provider failures, process limits, file integrity, and continuation parsing. Passing tests establish those behaviors, not recognition of every vulnerability.
