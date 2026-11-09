# Capability matrix

| Capability | State | Scope |
|---|---|---|
| Multi-file case, original SHA-256, purge | Implemented | PDF, PNG, JPEG within bounded local inputs. Public mode uses bundled cases. |
| Embedded PDF text and Tesseract | Implemented | Coordinates on supported page renders. Values are unverified. |
| Document classification and field extraction | Partial | English labeled templates and keyword scoring. Free-form layouts and unlabeled rows can fail. |
| Field relationships and cross-document matching | Partial | Payroll, date order, age, formats, and identity rules. Initials and common variations supported. |
| Font, baseline and sharpness | Partial | Neighboring money fields with PDF typography and raster proxies. |
| ELA and copy-move | Partial | JPEG recompression heatmap and ORB translation heuristics on raster uploads. No positive-case hit rate in the initial benchmark. |
| Signature reuse | Partial | Labeled PDF signatures compared with SSIM. Shared stamps are a benign explanation. |
| Retained PDF history | Implemented | Up to four earlier validated revisions, page text diff and side-by-side renders. |
| Hidden instruction | Partial | PDF visibility and English pattern rules. Extracted text never controls the workflow. |
| Innocent explanations and human review | Implemented | Evidence-specific alternatives, next steps, point breakdown, letter and audit entry. |
| Dossier and chain verification | Implemented | On-screen case and PDF with source hashes, evidence and reviewer action. |
| Blind corpus and calibrated scores | Planned | Initial results are synthetic and self-generated. |
| External language-model rephrasing | Planned | Current narrative is deterministic and evidence-linked. |
| Issuer or identity authentication, biometric comparison | Unsupported | Require independent verification. |
| Flattened PDF history and automatic verdicts | Unsupported | No recoverable revision bytes and no system decision. |
