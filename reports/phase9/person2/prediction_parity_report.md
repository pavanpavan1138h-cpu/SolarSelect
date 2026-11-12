# Final actual-model prediction parity

Fresh final live verification: genuine first eight held-out peer test.csv records, SiteKey 15 on 2022-03-01, 02, 04, 05, 06, 07, 08, 09. Dataset SHA-256: 64a404afcd3ad819cf6d3d69611c87ff3ab5880d2809a33900e00946f7b8b018.

Actual Peer Cohort champion v1 was loaded after alias/version/run/hash/signature/skops checks. Independently loaded frozen, actual provider, PredictionService, HTTP singles and HTTP batch match with atol 1e-8, rtol 0. Maximum difference in this final run: 8.8817841970012523e-16. All 100 fitted trees and estimator parameters match exactly. No synthetic evaluation records, clipping, rounding or changed expected values.

| Row | Independent frozen | Actual registry | Registry HTTP single | Registry HTTP batch |
|---:|---:|---:|---:|---:|
| 1 | 3.4601096349288265 | 3.4601096349288256 | 3.4601096349288265 | 3.4601096349288265 |
| 2 | 3.1362662943773607 | 3.1362662943773603 | 3.1362662943773603 | 3.1362662943773616 |
| 3 | 3.3314843692313416 | 3.3314843692313416 | 3.3314843692313421 | 3.3314843692313416 |
| 4 | 3.3500506728703909 | 3.3500506728703914 | 3.3500506728703914 | 3.3500506728703914 |
| 5 | 3.7071767714352637 | 3.7071767714352637 | 3.7071767714352633 | 3.7071767714352633 |
| 6 | 3.7219621916544123 | 3.7219621916544128 | 3.7219621916544123 | 3.7219621916544123 |
| 7 | 3.4802032218622032 | 3.4802032218622032 | 3.4802032218622037 | 3.4802032218622028 |
| 8 | 3.7443059959304126 | 3.7443059959304126 | 3.7443059959304126 | 3.7443059959304121 |

[Full fresh arrays/HTTP responses/source IDs](final_registry_integration/live_http.json). [Earlier structural model verification](final_registry_integration/actual_model_parity.json). This establishes equivalence, not new accuracy benchmarking. [Current summary](FINAL_PERSON2_SUBMISSION.md).
