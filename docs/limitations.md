# Limitations

- Classification and field extraction assume English and explicit labels. OCR confidence describes recognition quality. An extracted value can still be wrong.
- Different issuers use different payroll formats and payment calendars. The prototype compares a single labeled credit inside a configurable-in-code sample window of three days before to ten days after the pay date. Split payments require manual verification.
- A shared template, approved stamp, different export software, blur or JPEG compression can produce visual similarity or disagreement. ELA and ORB contribute only one point each. Typeface checks compare money fields and skip sparse layouts.
- PDF recovery needs an intact previous revision. Flattened, repaired or fully rewritten PDFs can erase the earlier bytes. The comparison focuses on retained text and matching pages. Page additions, reordering and raster-only edits need manual review.
- Hidden text and reviewer-directed language are detected with bounded visibility and phrase rules. Obfuscated, multilingual or image-only instructions can evade the detector. The deterministic review workflow gives document text no execution path.
- The benchmark is synthetic, self-generated and drawn from a small template family. A consistent rewritten payroll case was missed. One rotated genuine scan triggered a false alarm in the initial sweep. Consult the measured outputs for the current run.
- Heuristic method confidence and concern weights are uncalibrated. Findings can be correlated. The total is a visible triage aid for a human.
- The prototype does not validate real identity, authenticate issuers or infer signature authorship. It cannot distinguish intentional edits from legitimate corrections.
- Public deployment requires demo-only mode. SQLite on free hosts is typically ephemeral. The chain is an integrity consistency check, with no independent timestamp or externally signed head.
- Native PDF and OCR parsing has a subprocess time boundary. Production deployment would require stronger isolation, account controls and retention policies.

[Security model](architecture.md#security-model) · [Benchmark output](../data/benchmark/results/benchmark.md) · [Robustness output](../data/benchmark/results/robustness.md)
