# Financial software engineering: experience and evidence

My work connects business requirements with implementation: clarify the entity, period
and expected result; define the API and data contract; implement services and SQL;
surface the result in the interface; investigate failures across those boundaries.
My focus is backend-oriented full-stack development and domain agents.

## Operating analytics

**Goal:** help business users inspect branch performance with consistent revenue,
share and comparison-period definitions.

**Work:** translated stakeholder requirements into SQL-backed services and frontend
data-card workflows, with FastAPI/SSE interfaces and four agent tool domains:
branch lookup, operating metrics, calculations and report requests.

**Outcome represented in code:** structured requests reach domain tools and return
results that can be displayed by the client. The public reconstruction additionally
demonstrates SQLite-backed calculations, missing-baseline handling and streamed evidence.
See the [browser agent](../business-analytics-agent/portfolio_demo/agent_server.py),
[original orchestration](../business-analytics-agent/agent/mutil_agent.py) and
[business rules](../business-analytics-agent/metrics.py).

## Internal fund research

**Goal:** support the company's internal quantitative private-fund research workflow.
The repository owner's stated business context is HuiDi Investment, Kuangke's wholly
owned subsidiary. Fund size describes the organization, not assets managed by this software.

**Work:** developed agent service capabilities across three specialist groups—funds,
managers and companies—with entity resolution separated from downstream data retrieval.

**Outcome represented in code:** domain-specific tools, bounded lookup and explicit
handling of ambiguity and unavailable history. [Entity resolution](../wealth-agent/agent/entity_recognizer.py)
and [service tests](../wealth-agent/service_tests/) show the implementation and its limits.
Synthetic cases do not establish live-model accuracy or investment performance.

## Institutional investment monitoring

**Goal:** translate institution-specific investment guidelines into repeatable checks
over dated positions, with results available for review and historical replay.

**Work:** implemented configurable monitoring workflows connecting holdings queries,
rule execution and persisted results, with database-backed scheduled-job coordination.

**Outcome represented in code:** distinct breach, missing-data and execution-failure
states; historical execution paths; ownership-aware leases. Inspect the
[configuration workflow](../investment-risk-monitor-unified/docs/CONFIGURATION_WORKFLOW.md)
and [database integration tests](../investment-risk-monitor-unified/integration_tests/test_database.py).

## Public engineering extension

After the internship, I extended the sanitized repository with reproducible browser
demos, API and tool-boundary tests, SQL parameterization and CI. The documented baseline
contains 100 Python test methods, five browser scenarios and eight extraction-contract
fixtures. Database integration methods run separately on MySQL and PostgreSQL.
These are verification counts, not production adoption or performance improvements.

The browser reconstruction and later reliability fixes demonstrate current engineering
skills; they are distinguished from internship deliverables. See [contribution scope](CONTRIBUTIONS.md)
and [verification commands](VERIFICATION.md). Personal ownership statements describe the
repository owner's confirmed responsibilities, not sole authorship of the team codebase.
