# Demo video shot list

The MP4 records the running local app with English narration and burned-in captions. The on-screen samples are synthetic.

| Shot | Action shown | Verification cue |
|---|---|---|
| 01 | Open the case desk | Four bundled samples and synthetic-data banner |
| 02 | Load Meena and open harmless explanations | Low concern, initial variant and expected pay window |
| 03 | Load Ravi and select the typography finding | Red box around current INR 88,000 |
| 04 | Enable Peel layer | Prior INR 48,000 and current INR 88,000, with both page renders |
| 05 | Open the matrix and select the signature finding | Pay-cycle mismatch and a highlighted signature region |
| 06 | Request more documents | Point breakdown, applicant letter and decision audit receipt |
| 07 | Download dossier and verify chain | Real PDF download and integrity confirmation |
| 08 | Load the hidden instruction case | Embedded text appears as evidence |
| 09 | Load the degraded case | Cannot determine and reason |
| 10 | Open the benchmark | Recorded synthetic benchmark and robustness sweep |
| 11 | Return to case desk | Closing tag and author credit |

Re-record with the local app running, Playwright Chromium installed and Windows SAPI available.

```powershell
python scripts/record_demo.py
```

Upload `demo/Palimpsest-demo.mp4` to the submission's video platform and use the viewer link.
