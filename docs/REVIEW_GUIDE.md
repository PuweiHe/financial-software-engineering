# Five-minute code review guide

This guide points to code that a reviewer can inspect quickly. The data and runnable examples are synthetic. The browser demo is a portfolio reconstruction; the retained agent services need separately configured model and financial-data APIs.

## 1. Follow one full-stack request

**Business request:** compare branches' annual revenue and share, then show year-over-year growth for a selected branch.

1. [Browser controls and states](../business-analytics-agent/portfolio_demo/app.js) request available years, send the selected year and branch to `/api/metrics`, and render loading, error, missing-baseline, and successful results.
2. [HTTP handler](../business-analytics-agent/portfolio_demo/server.py) validates the query and returns JSON with explicit 400/404 responses. Its SQLite repository uses a unique branch/year key and bound query values.
3. [Metric calculation](../business-analytics-agent/metrics.py) computes the total, revenue share, and growth. The missing 2024 observation for `BRANCH003` remains undefined rather than becoming zero growth.
4. [HTTP and repository tests](../business-analytics-agent/tests/test_portfolio_demo.py) cover that case, invalid queries, duplicate observations, and an attempted SQL-injection string.

Run it from `business-analytics-agent/` with `python3 -m portfolio_demo.server`, then open `http://127.0.0.1:8765/`. Choose 2025 and `BRANCH003`; the synthetic result is a 20% share and **No baseline** growth. This path runs locally without a model or credentials.

## 2. Run the conversational path

Start `python -m portfolio_demo.agent_server` after installing the business agent requirements.
Ask `What were revenue share and growth for BRANCH003 in 2025?`.

Follow [the FastAPI application](../business-analytics-agent/portfolio_demo/agent_server.py):
`Question` validates input; `ReportArguments` constrains the model's tool arguments;
`branch_report` reads SQLite through the shared repository; the graph emits SSE events;
the [browser](../business-analytics-agent/portfolio_demo/app.js) renders evidence and clears it on failure.
The sample returns 20% share and no growth baseline. Ask about both 2024 and 2025 to see clarification.

The default scripted model is a narrow replay fixture. It establishes execution behavior,
not language understanding. The original supervisor graph remains separately tested.
[Eight service tests](../business-analytics-agent/service_tests/test_demo_agent.py) cover
validation, ambiguity, missing data, provider errors and request boundaries.

## 3. Inspect the agent service boundaries

**Business request:** research a fund whose name may match more than one product, or compare products when one lacks a return history.

1. [Wealth API routes](../wealth-agent/web/agent_api.py) expose normal and streaming conversation endpoints and scope the token context to each request.
2. [Entity recognition and lookup](../wealth-agent/agent/entity_recognizer.py) separate name extraction from bounded concurrent entity queries and return multiple candidates when a name is ambiguous.
3. [Supervisor and specialist agents](../wealth-agent/agent/mutil_agent.py) route fund, manager, and company requests to separate tool sets, apply tool-call limits, and stream model/tool events.
4. [Fund comparison tool](../wealth-agent/tools/compare_fund_tool.py) delegates structured lookups to configured data adapters. [Synthetic cases](../wealth-agent/evals/synthetic_cases.json) and [offline tests](../wealth-agent/tests/test_demo.py) exercise deterministic ambiguity and missing-history behavior.

The synthetic cases do **not** measure LLM routing accuracy or prove that external financial-data adapters work. The [wealth agent README](../wealth-agent/README.md) lists the configuration needed for a live integration.

The separate [operations agent](../business-analytics-agent/agent/mutil_agent.py) routes branch lookup, operating metrics, calculation, and report-request tools. Its local browser demo demonstrates the business calculation and full-stack data path; it does not invoke this agent.

## 4. Check persistence and concurrency

The [risk monitor workflow](../investment-risk-monitor-unified/docs/CONFIGURATION_WORKFLOW.md) shows how a configured rule becomes a dated result. [Database integration tests](../investment-risk-monitor-unified/integration_tests/test_database.py) cover adapted import, result, and lease paths on MySQL and PostgreSQL. The [standalone lease example](../database-job-mutex/README.md) isolates the stale-owner release problem.

Run `python3 scripts/check_all.py` at the repository root for offline checks. Read [verification scope](VERIFICATION.md) for what those checks establish and [contribution scope](CONTRIBUTIONS.md) for the distinction between internship work and public reconstructions.

## 5. Inspect the reliability changes

[Dependency-backed service tests](../wealth-agent/service_tests/) exercise real FastAPI routes and real LangChain graphs with scripted responses. Start with `test_graph.py`, then the timeout, cancellation and same-ID isolation cases. [Browser E2E tests](../business-analytics-agent/e2e/) verify failure recovery through the visible UI. [DAO tests](../investment-risk-monitor-unified/tests/test_dao_parameters.py) check SQL/value separation, while [batch tests](../investment-risk-monitor-unified/tests/test_query_adapter.py) check transactional rollback.

[Engineering decisions and interview notes](ENGINEERING_REVIEW.md) explain why these changes were made and which production claims the tests cannot support.
