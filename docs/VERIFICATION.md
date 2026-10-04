# Verification scope

## Local verification for the engineering revision

Python 3.13 was used locally. Tests below use synthetic data and no model credentials.

| Check | Executed result | What it establishes |
| --- | --- | --- |
| Standard-library project suites | 54 tests passed: risk 30, wealth 8, operations 14, mutex 2 | Deterministic business rules, DAO parameter binding, batch rollback, risk result aggregation, local HTTP contracts and lease behavior |
| Dependency-backed agent suites | 41 tests passed: wealth 20, operations 21 | Real FastAPI validation/SSE and LangChain orchestration with injected model/tool responses; cancellation, timeouts, request isolation, extraction and transport boundaries; mocked speech completion |
| Risk application adapters | 5 tests passed | Mapping, account scope, whitelist and Excel import contracts |
| Browser E2E | 5 tests passed in installed Chrome | Mobile branch selection, failure clearing/retry, empty-year state, streamed agent evidence and agent retry through the real local server |
| Extraction output contracts | 8/8 fixtures passed | Recorded synthetic outputs are accepted/rejected by the extraction schema as expected; **not model accuracy** |
| Lint / formatting | Passed | Whole-tree syntax/undefined-name lint; stronger lint and formatting on the explicit boundary modules in the quality script |
| Strict typing | Passed for 2 modules | Metric domain types and extracted entity schema; **not whole-tree strict typing** |
| Dependency consistency | `pip check` passed; Python 3.11 dry-run resolution succeeded | Installed dependencies agree; pinned service packages resolve for the Docker/CI Python version |
| Dependency audit | No known vulnerabilities in the audited installed environment | Point-in-time advisory check; optional E2B/MinIO providers were not installed or audited |
| Privacy / syntax / demos | Passed | Pattern scans, Python parsing and all four synthetic demos |

The 100 Python test methods are focused checks, not a coverage percentage. Three standard-library HTTP tests skip if loopback sockets are forbidden; the local verification above ran with sockets enabled and no skips.

## Reproduce

At the root, without dependencies:

```bash
python3 scripts/check_all.py
```

For each agent, use its own virtual environment from that project's directory:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
# Wealth only, for the optional speech contract tests:
# python -m pip install -r requirements-speech.txt
python -m unittest discover -s service_tests -v
# Wealth only:
# python evals/evaluate_contracts.py
```

The API tests exercise the actual supervisor → async specialist → tool path with a scripted model. They do not contact a model provider or establish routing quality on unseen questions. The 12 legacy synthetic wealth cases test deterministic tools; the 108-label catalog is a coverage design artifact.

Root quality checks:

```bash
python -m pip install -r requirements-dev.txt pydantic==2.11.3
python scripts/check_quality.py
```

Browser checks from `business-analytics-agent/` require Node 22+, pnpm and Python 3.11+:

```bash
python -m pip install -r requirements.txt
pnpm install --frozen-lockfile
pnpm exec playwright install chromium
pnpm test:e2e
```

Set `PLAYWRIGHT_CHANNEL=chrome` to use an installed Chrome. Frontend assets are plain HTML/CSS/JavaScript; there is no bundler or production compilation step.

Risk adapter checks require `requirements.txt` and `requirements-import.txt`, then `python -m unittest discover -s adapter_tests -v`.

## CI and limits

- `ci.yml`: PR/main/manual/weekly orchestration, scoped expensive checks, dependency audits, redacted history secret scanning and the aggregate `CI gate`.
- `portfolio.yml`: privacy/syntax, offline tests and demos on Python 3.11/3.13.
- `engineering.yml`: dependency-backed agents on both Python versions, focused quality checks, browser E2E, and agent Docker builds with health checks.
- `database.yml`: seven real-database integration methods and five adapter methods per MySQL 8.4/PostgreSQL 16 configuration.

Docker and live database services are verified in GitHub Actions; consult the run for the current commit. They were not rerun locally for the workflow revision. DAO capture tests check SQL/value separation and parameter order, not the business meaning of every inherited query.

Live model/data APIs, Redis, speech provider, E2B and object storage remain unverified. Speech tests use a fake socket. Dependency pins describe a tested resolution, not immutable hashes or a security guarantee. Privacy scans cannot prove absence of all identifying information or clear previously published Git history. No production latency, user count, financial impact or live accuracy is asserted.

The new browser agent has eight service tests covering SQL evidence, clarification, unavailable years, invalid model arguments, redacted provider failures, request validation, local access boundaries and request isolation. Its scripted model is a narrow replay fixture, not an evaluation of language understanding. See [development workflow](DEVELOPMENT.md) for local check levels and optional live mode.
