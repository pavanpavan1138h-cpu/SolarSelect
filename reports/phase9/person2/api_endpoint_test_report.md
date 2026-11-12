# Final live endpoint verification

Fresh final run: 74 checks passed, zero failed (35 actual registry, 35 frozen, four unavailable-source). Full requests, actual responses, expected behavior/status, request IDs and durations are in [live_http.json](final_registry_integration/live_http.json). All ten endpoint families and Swagger/ReDoc/OpenAPI were exercised without contract changes.

| Source | Check | Request | Expected | Actual | Result | ms |
|---|---|---|---:|---:|---|---:|
| mlflow | health/live | GET /api/v1/health/live | 200 | 200 | PASS | 13.872 |
| mlflow | health/ready | GET /api/v1/health/ready | 200 | 200 | PASS | 2.234 |
| mlflow | model/info | GET /api/v1/model/info | 200 | 200 | PASS | 3.014 |
| mlflow | model/schema | GET /api/v1/model/schema | 200 | 200 | PASS | 8.567 |
| mlflow | panels | GET /api/v1/panels | 200 | 200 | PASS | 4.382 |
| mlflow | panels/PNL-TRINA-330W | GET /api/v1/panels/PNL-TRINA-330W | 200 | 200 | PASS | 2.862 |
| mlflow | limitations | GET /api/v1/limitations | 200 | 200 | PASS | 2.296 |
| mlflow | /docs | GET /docs | 200 | 200 | PASS | 1.347 |
| mlflow | /redoc | GET /redoc | 200 | 200 | PASS | 1.136 |
| mlflow | /openapi.json | GET /openapi.json | 200 | 200 | PASS | 33.693 |
| mlflow | Historical single 0 | POST /api/v1/predict | 200 | 200 | PASS | 50.192 |
| mlflow | Historical single 1 | POST /api/v1/predict | 200 | 200 | PASS | 58.879 |
| mlflow | Historical single 2 | POST /api/v1/predict | 200 | 200 | PASS | 51.308 |
| mlflow | Historical single 3 | POST /api/v1/predict | 200 | 200 | PASS | 50.631 |
| mlflow | Historical single 4 | POST /api/v1/predict | 200 | 200 | PASS | 48.23 |
| mlflow | Historical single 5 | POST /api/v1/predict | 200 | 200 | PASS | 46.365 |
| mlflow | Historical single 6 | POST /api/v1/predict | 200 | 200 | PASS | 47.727 |
| mlflow | Historical single 7 | POST /api/v1/predict | 200 | 200 | PASS | 47.905 |
| mlflow | Ordered batch | POST /api/v1/predict/batch | 200 | 200 | PASS | 364.227 |
| mlflow | Roof geometry | POST /api/v1/roof-fit | 200 | 200 | PASS | 12.273 |
| mlflow | Missing fields | POST /api/v1/predict | 422 | 422 | PASS | 3.055 |
| mlflow | Array/count input | POST /api/v1/predict | 422 | 422 | PASS | 2.515 |
| mlflow | Invalid capacity | POST /api/v1/predict | 422 | 422 | PASS | 3.323 |
| mlflow | Fractional integer | POST /api/v1/predict | 422 | 422 | PASS | 2.688 |
| mlflow | Unsupported site | POST /api/v1/predict | 422 | 422 | PASS | 2.437 |
| mlflow | Invalid timestamp | POST /api/v1/predict | 422 | 422 | PASS | 2.162 |
| mlflow | String input | POST /api/v1/predict | 422 | 422 | PASS | 1.84 |
| mlflow | Target leakage | POST /api/v1/predict | 422 | 422 | PASS | 2.054 |
| mlflow | Malformed JSON | POST /api/v1/predict | 422 | 422 | PASS | 1.739 |
| mlflow | NaN input | POST /api/v1/predict | 422 | 422 | PASS | 1.895 |
| mlflow | Infinity input | POST /api/v1/predict | 422 | 422 | PASS | 1.788 |
| mlflow | Oversized batch | POST /api/v1/predict/batch | 422 | 422 | PASS | 6.629 |
| mlflow | Prospective pending | POST /api/v1/predict | 409 | 409 | PASS | 2.511 |
| mlflow | Unknown panel | GET /api/v1/panels/UNKNOWN | 404 | 404 | PASS | 2.253 |
| mlflow | Explicit blend policy | POST /api/v1/predict | 409 | 409 | PASS | 10.825 |
| local | health/live | GET /api/v1/health/live | 200 | 200 | PASS | 33.125 |
| local | health/ready | GET /api/v1/health/ready | 200 | 200 | PASS | 2.981 |
| local | model/info | GET /api/v1/model/info | 200 | 200 | PASS | 2.765 |
| local | model/schema | GET /api/v1/model/schema | 200 | 200 | PASS | 56.756 |
| local | panels | GET /api/v1/panels | 200 | 200 | PASS | 4.168 |
| local | panels/PNL-TRINA-330W | GET /api/v1/panels/PNL-TRINA-330W | 200 | 200 | PASS | 3.067 |
| local | limitations | GET /api/v1/limitations | 200 | 200 | PASS | 2.637 |
| local | /docs | GET /docs | 200 | 200 | PASS | 1.321 |
| local | /redoc | GET /redoc | 200 | 200 | PASS | 1.099 |
| local | /openapi.json | GET /openapi.json | 200 | 200 | PASS | 32.841 |
| local | Historical single 0 | POST /api/v1/predict | 200 | 200 | PASS | 43.789 |
| local | Historical single 1 | POST /api/v1/predict | 200 | 200 | PASS | 37.562 |
| local | Historical single 2 | POST /api/v1/predict | 200 | 200 | PASS | 38.311 |
| local | Historical single 3 | POST /api/v1/predict | 200 | 200 | PASS | 38.432 |
| local | Historical single 4 | POST /api/v1/predict | 200 | 200 | PASS | 38.429 |
| local | Historical single 5 | POST /api/v1/predict | 200 | 200 | PASS | 38.286 |
| local | Historical single 6 | POST /api/v1/predict | 200 | 200 | PASS | 35.846 |
| local | Historical single 7 | POST /api/v1/predict | 200 | 200 | PASS | 37.947 |
| local | Ordered batch | POST /api/v1/predict/batch | 200 | 200 | PASS | 277.421 |
| local | Roof geometry | POST /api/v1/roof-fit | 200 | 200 | PASS | 12.823 |
| local | Missing fields | POST /api/v1/predict | 422 | 422 | PASS | 3.478 |
| local | Array/count input | POST /api/v1/predict | 422 | 422 | PASS | 2.003 |
| local | Invalid capacity | POST /api/v1/predict | 422 | 422 | PASS | 1.959 |
| local | Fractional integer | POST /api/v1/predict | 422 | 422 | PASS | 1.835 |
| local | Unsupported site | POST /api/v1/predict | 422 | 422 | PASS | 1.839 |
| local | Invalid timestamp | POST /api/v1/predict | 422 | 422 | PASS | 1.835 |
| local | String input | POST /api/v1/predict | 422 | 422 | PASS | 2.407 |
| local | Target leakage | POST /api/v1/predict | 422 | 422 | PASS | 2.131 |
| local | Malformed JSON | POST /api/v1/predict | 422 | 422 | PASS | 1.697 |
| local | NaN input | POST /api/v1/predict | 422 | 422 | PASS | 1.803 |
| local | Infinity input | POST /api/v1/predict | 422 | 422 | PASS | 1.8 |
| local | Oversized batch | POST /api/v1/predict/batch | 422 | 422 | PASS | 6.339 |
| local | Prospective pending | POST /api/v1/predict | 409 | 409 | PASS | 2.169 |
| local | Unknown panel | GET /api/v1/panels/UNKNOWN | 404 | 404 | PASS | 1.764 |
| local | Explicit blend policy | POST /api/v1/predict | 200 | 200 | PASS | 39.407 |
| unavailable | No silent fallback health/live | GET /api/v1/health/live | 200 | 200 | PASS | 3.259 |
| unavailable | No silent fallback health/ready | GET /api/v1/health/ready | 503 | 503 | PASS | 2.526 |
| unavailable | No silent fallback model/info | GET /api/v1/model/info | 503 | 503 | PASS | 2.746 |
| unavailable | Unavailable prediction | POST /api/v1/predict | 503 | 503 | PASS | 4.318 |

Postman collection: docs/backend/postman_collection.json, 37 requests, model_source variable. Postman/Newman itself was not executed; Python performed actual HTTP requests. [Authoritative completion summary](FINAL_PERSON2_SUBMISSION.md).
