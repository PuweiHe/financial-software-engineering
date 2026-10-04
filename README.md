# Financial Software Engineering Portfolio

[![CI](https://github.com/PuweiHe/financial-software-engineering/actions/workflows/ci.yml/badge.svg)](https://github.com/PuweiHe/financial-software-engineering/actions/workflows/ci.yml)

This portfolio shows how I turn financial business questions into software: a runnable browser-to-API-to-SQL analytics path, domain agents that route research and operating-metric requests, and a configurable investment monitor with database and concurrency checks. The examples are generalized and use synthetic data so reviewers can inspect the implementation without customer systems.

**Start with working code:** [run the branch analytics demo](business-analytics-agent/README.md#try-the-full-stack-business-scenario) to trace one request through the UI, HTTP API, SQL, and business rules. Then use the [code review guide](docs/REVIEW_GUIDE.md) to inspect agent routing and risk-monitor persistence. The demo runs without credentials; the retained LLM agents need separately configured model and data services.

**Try the agent path:** [run the conversational browser demo](docs/DEVELOPMENT.md#agent-browser-scenario): question → LangChain tool call → validated arguments → SQLite evidence → SSE → browser. The default scripted model needs no credentials; optional live mode uses your configured model.

## Start with a working product path

**Business scenario:** an operations manager asks which branches contributed to annual revenue and how each branch changed from the prior year. The [Business Analytics Agent](business-analytics-agent/) contains the domain agent and API adapters. Its new [browser demo](business-analytics-agent/portfolio_demo/) gives that question a complete local path: browser controls → HTTP API → parameterized SQLite query → deterministic metric calculation → visible results. The demo uses synthetic branch records and does not invoke an LLM.

```bash
cd business-analytics-agent
python3 -m portfolio_demo.server
# Open http://127.0.0.1:8765/
```

Choose 2025 and `BRANCH003`: the sample branch contributes 20% of annual revenue, while its growth reads **No baseline** because no 2024 record exists. The distinction prevents missing history from becoming a misleading zero.

## From business request to code

| Workflow | Business result represented in this repository | Inspectable engineering evidence |
| --- | --- | --- |
| [Business Analytics Agent](business-analytics-agent/) | Branch revenue, share, and year-over-year growth remain consistent across periods; an absent baseline stays undefined. | [Four tool domains](business-analytics-agent/agent/mutil_agent.py), [HTTP/SQL browser demo](business-analytics-agent/portfolio_demo/), [metric and API tests](business-analytics-agent/tests/test_portfolio_demo.py). |
| [Wealth Research Agent](wealth-agent/) | Built for internal research at HuiDi Investment, Kuangke's wholly owned private fund subsidiary ([over RMB 6B AUM](https://hdinvesting.cn/)); the workflow retains multiple fund matches and unavailable return history instead of presenting an unsupported comparison. | [Entity resolution and bounded lookup](wealth-agent/agent/entity_recognizer.py), [three specialist tool groups](wealth-agent/agent/mutil_agent.py), [synthetic cases](wealth-agent/evals/synthetic_cases.json), FastAPI/SSE. |
| [Investment Risk Monitor](investment-risk-monitor-unified/) | Institutional risk analysts can review dated checks, historical replay, and explicit missing-data or alert states. | [Configuration-to-result workflow](investment-risk-monitor-unified/docs/CONFIGURATION_WORKFLOW.md), [MySQL/PostgreSQL integration tests](investment-risk-monitor-unified/integration_tests/test_database.py), transactional imports and distributed leases. |
| [Database Job Mutex](database-job-mutex/) | Concurrent instances do not acquire the same scheduled-job lease; a stale owner cannot release its successor's lease. | [Owner-token lease](database-job-mutex/distributed_mutex_job.py), [stale-release tests](database-job-mutex/tests/test_lease.py). |

**For SDE/SWE review:** run the browser demo, then inspect the risk monitor's database tests and the mutex's concurrency case. **For agent engineering review:** inspect the two domain agent architectures after the runnable examples; their live model and customer-data adapters require external services.

## Engineering worth inspecting

- **Agent reliability:** real async supervisor/specialist execution, validated entity extraction, request-local cards, explicit SSE errors and bounded calls. [Service tests](wealth-agent/service_tests/) use the actual orchestration graph with scripted model responses.
- **Database correctness:** bound values across the risk DAOs, transactional batch writes and visible multi-dimension failures. [Regression tests](investment-risk-monitor-unified/tests/) exercise adversarial filters and rollback.
- **Full-stack behavior:** typed metric rules, safe missing baselines, failure/retry states and [three browser E2E cases](business-analytics-agent/e2e/).
- **Reviewable evidence:** 100 focused Python test methods, five browser tests and eight extraction-contract fixtures passed locally. These are not live-model accuracy or production-performance measurements. [Exact scope and commands](docs/VERIFICATION.md).

The [engineering review](docs/ENGINEERING_REVIEW.md) contains the architecture, implementation decisions, remaining debt and interview discussion points. The [initial audit](docs/ENGINEERING_AUDIT.md) records the defects that motivated this revision.

## Stack by responsibility

| Layer | Implementation |
| --- | --- |
| Browser | HTML, CSS and JavaScript; responsive synthetic analytics UI |
| APIs | Python, FastAPI, Pydantic and Server-Sent Events; standard-library local demo server |
| Agents | LangChain/LangGraph, OpenAI-compatible model adapters, domain tools |
| Data | SQLite demo; MySQL/PostgreSQL risk persistence; optional Redis history |
| Verification | unittest, Playwright, Ruff, focused mypy; GitHub Actions |
| Packaging | Resolved Python dependency pins; nonroot agent Docker images |

## My role and the public reconstruction

My internship work included clarifying financial-institution requirements, implementing backend and frontend functionality, writing SQL for data-driven features, and developing domain-agent capabilities. The table above connects those areas to inspectable examples. [Contribution and scope notes](docs/CONTRIBUTIONS.md) distinguish this stated role from functionality added for the public portfolio; they do not attribute every retained line of a team codebase to one person. Client identities and deployment details are intentionally absent from this public copy.

The public repository adds synthetic fixtures, local demos, tests, and privacy changes so a reviewer can run meaningful paths. The business-analytics browser UI is a new portfolio reconstruction; frontend source from the original operations project was not present in the supplied files.

## Reproduce the checks

```bash
git clone https://github.com/PuweiHe/financial-software-engineering.git
cd financial-software-engineering
python3 scripts/check_all.py
```

The offline runner uses Python 3.11+ with no paid model, credentials, or database server. It runs privacy/syntax checks, unit tests, and four synthetic demos in separate project processes. The browser demo needs only Python's standard library. The separate database workflow runs the risk-monitor integration suite on MySQL 8.4 and PostgreSQL 16. See [verification scope](docs/VERIFICATION.md) for exactly what each check proves.

The repository-wide publishable-tree check also rejects common credential formats, personal paths, nonlocal IP addresses, and hardcoded numeric user IDs in Python adapter fields. It reports file paths and categories without printing matched values.

## Business decisions visible in code

| Requirement | Engineering choice | Evidence |
| --- | --- | --- |
| A branch's missing prior year must not read as zero growth. | Preserve an undefined growth value through SQL, API, and browser presentation. | [Metric implementation](business-analytics-agent/metrics.py), [HTTP checks](business-analytics-agent/tests/test_portfolio_demo.py) |
| An absent risk position must not read as a safe zero exposure. | Emit a data-quality result with a null indicator and an explicit status. | [Ratio evaluator](investment-risk-monitor-unified/core/holding_ratio.py), [database check](investment-risk-monitor-unified/integration_tests/test_database.py) |
| A batch must report failed rules even after it finishes iterating. | Aggregate execution status at the runner boundary. | [Runner regression test](investment-risk-monitor-unified/tests/test_runner_contract.py) |
| A stale worker must not release a successor's lease. | Require the owner token for release. | [Lease implementation](investment-risk-monitor-unified/utils/distributed_lock.py), [concurrency test](investment-risk-monitor-unified/integration_tests/test_database.py) |
| A fund name can be ambiguous or lack one-year history. | Separate entity lookup and specialist tools; retain ambiguity and missing values. | [Fund cases](wealth-agent/evals/synthetic_cases.json), [tool tests](wealth-agent/tests/test_demo.py) |

Read the [business case studies](docs/BUSINESS_CASES.md) and [architecture decisions](docs/ARCHITECTURE.md) for context. All public data is synthetic. No customer records, credentials, production results, or measured business impact are claimed.
