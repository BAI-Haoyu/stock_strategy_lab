# Development record

Date: 13 November 2026. Times below use Europe/Paris (CET).

The assignment's two-week structure is used as a delivery plan, not as a claim of elapsed time or ten-person collaboration. The supplied brief was reviewed, and the public course notebook was retrieved. No prior repository or deployment account was supplied.

## Actual checkpoints

- 04:35: recorded start of the implementation session after requirements and source review. Chose portfolio analysis, strategy comparison and SQLite storage.
- 04:35–04:46: implemented modular calculations, data sources, UI and initial tests. Archived the course single-stock source. The user accidentally interrupted control and then asked to resume; saved work was retained.
- 04:46–05:03: completed dependency installation, input and currency checks, local server launch, automated UI tests and live Yahoo verification. Corrected the Yahoo cache path. A temporary network permission reset was resolved before claiming live data success.
- By 05:03: 29 tests passed. Three USD symbols each returned 501 aligned daily rows, ending 12 November 2026. The complete test transcript and numeric results are stored alongside this log.
- Documentation and visual review followed. Code generation, debugging and testing took less than one hour from the recorded implementation start, below the three-hour vibe coding limit. This timing is a session bound, not a measured time saving relative to manual work.

## Specification used to guide AI assistance

These are recorded design constraints, not a fabricated transcript of a separate Copilot conversation:

1. Extend the course baseline with exactly three integrated enhancements. Reject more than 20 symbols; require weights to sum to 100%; restrict portfolio valuation to verified USD instruments.
2. Use prior-close signals and next-open fills with adverse slippage and fees. Permit only one position per stock and retain open positions as marked-to-market positions.
3. Compare all strategies on the same dates and capital. Keep data, simulation, UI and storage in separate modules.
4. Test arithmetic with known values, future-data independence, invalid inputs, session isolation, and the save/restore user journey. Do not treat generated charts as evidence of financial correctness.

## Findings and decisions

- The original notebook uses same-close signal execution and permits overlapping trade records. The new engine deliberately differs in execution and capital accounting; the original code is retained for traceability.
- The standard package installer stalled at remote index requests. Public PyPI wheels were downloaded into the task workspace and installed into a local virtual environment. The tested versions are recorded in requirements-lock.txt.
- Yahoo's default user-cache directory was not writable in the restricted execution environment. The adapter now stores cache files inside the project's data directory. These files are excluded from packaging and Git.
- Later test runs encountered temporary-directory permissions inherited from an earlier tool session. Final tests used a fresh workspace temporary directory with pytest caching disabled. This changed the test environment, not the calculations.
- The app's synthetic prices are explicitly labelled; no unsuccessful live request is silently replaced with demo data.
- The observed historical interval favoured buy and hold for total return, with a larger drawdown. No parameter optimization, profitability claim or out-of-sample validation was performed.

## Release status

The code is implemented and locally verified. Public deployment, persistent authenticated storage, a ten-person user review and concurrency/load testing are outstanding. GitHub/Streamlit sign-in must be completed by the account owner. A localhost address is not a public submission link.
