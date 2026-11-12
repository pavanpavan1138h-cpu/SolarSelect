# Final Person 2 pytest results

Fresh final execution on 2026-11-12 in the authoritative feature worktree.

| Suite | Passed | Failed | Skipped | Errors | Seconds |
|---|---:|---:|---:|---:|---:|
| Dedicated API (includes 28 actual-registry cases) | 118 | 0 | 0 | 0 | 22.864 |
| Complete repository | 361 | 1 | 0 | 0 | 56.947 |

Executed python -m pytest -q tests -k test_api and python -m pytest -q tests/ with SOLARSELECT_REQUIRE_REGISTRY_TESTS=1. All 28 real champion cases ran. The other 90 API cases cover frozen mode, validation, geometry, errors and mocked failure paths.

The isolated registry test now passes after disposing its temporary tracking/registry SQLAlchemy engines before directory cleanup and restoring URI globals/environment; all original assertions remain. A prior targeted execution passed too.

One inherited failure remains: test_logged_visualization_artifacts expects the Phase 5 experiment in the older root DB. All ten genuine charts are present in the approved original archive, but the legacy test/store uses old root and macOS paths. Person 1 owns portable evaluation-store wiring. No assertion was weakened and no artifact/registration fabricated.

Raw final_api.log/xml and final_full.log/xml are retained locally under final_registry_integration and excluded from Git. Counts, timestamps and environment are in preservation_audit.json. Canonical Python 3.13.9 execution was unavailable; existing 3.12.14 was used without changing pins.

[Authoritative final submission](FINAL_PERSON2_SUBMISSION.md).
