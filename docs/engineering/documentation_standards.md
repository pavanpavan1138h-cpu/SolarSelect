# Documentation Standards — SolarSelect

This document defines the mandatory documentation standards that every future task, prompt, script, notebook, and pull request must follow in SolarSelect.

---

## 1. The 13-Point Documentation Standard

For every new prompt, feature, or phase implementation, the primary documentation (README or completion report) must explicitly address the following 13 sections:

1. **Objective and Scope:** Clear statement of task boundaries, goals, and what is explicitly out of scope.
2. **Methodology:** Physical principles, mathematical formulations, and algorithmic approaches followed.
3. **Data and Sources:** Traceable record of all data files accessed, loaded, or generated, with licensing notes.
4. **Technical Implementation:** Detailed narrative of code architecture, key functions, and modular design.
5. **Configuration and Parameters:** Exact hyperparameters, random seeds, threshold values, and hardware limits.
6. **Results and Outputs:** Full disclosure of empirical metrics, confusion matrices, error tables, and runtimes.
7. **Interpretation:** Scientific and engineering meaning of results (e.g. why an error occurred, physical plausibility).
8. **Decisions and Rationale:** Architectural choices made, alternatives evaluated, and reasons for selection.
9. **Assumptions:** Explicit list of assumptions made, distinguishing them from verified empirical facts.
10. **Limitations and Risks:** Failure modes, known edge cases, data gaps, and operational vulnerabilities.
11. **Reproducibility Instructions:** Exact CLI commands to reproduce the code, tests, and outputs.
12. **Files Created and Modified:** Exact inventory of all added, modified, or deleted files.
13. **Execution Status:** Formal status declaration (COMPLETED, COMPLETED WITH LIMITATIONS, IN PROGRESS, PENDING, or BLOCKED BY APPROVAL).

---

## 2. Code, Notebook, and Visual Standards

- **Meaningful Markdown:** Every Jupyter notebook must include narrative Markdown cells explaining the intent and physics before major code blocks. Code must never appear without context.
- **Function Docstrings:** Every Python function and class must include a PEP 257 compliant docstring detailing arguments, return types, physical units, and exceptions.
- **Visualizations:** Every figure generated must have:
  * An informative title including figure identifier and topic.
  * Clear axis labels with explicit units (e.g. `kWh/kWp/day`, `°C`, `mm`).
  * Legends and color keys.
  * High resolution (minimum 300 DPI) saved to `figures/`.
- **Metric Integrity:** Every reported metric must explicitly identify the dataset split on which it was calculated (e.g. "Train", "Validation", or "Held-Out Test") and its physical units.
- **Traceable Citations:** Any external reference must record the author, publication title, year, URL, and access date.
- **Audit Logging:** Every work session must append an entry to the root `log.txt` chronologically before closing.

