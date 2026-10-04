# Development workflow

Use a short-lived branch and open a pull request. `CI gate` is the required aggregate
check: it fails when a required job fails or is cancelled, and accepts deliberate
service/database skips after the scope job succeeds. Main, manual and weekly runs
exercise all suites. PRs run expensive service and database suites only when their
implementation or shared CI configuration changes. Documentation-only PRs still
run offline checks, privacy checks, history secret scanning and dependency audits.

## Local checks

From the repository root:

```bash
python scripts/check_all.py --level offline
python scripts/check_all.py --level services
RUN_DB_INTEGRATION=1 python scripts/check_all.py --level integration
```

The default is `offline`, requiring only Python 3.11+. `services` also requires the
two agents' pinned Python requirements, wealth speech requirements, root development
requirements, and the browser dependencies (`pnpm install --frozen-lockfile` and
`pnpm exec playwright install chromium` in `business-analytics-agent`).
`integration` additionally requires risk-monitor requirements and a disposable
database configured with the `DB_*` environment variables used in `database.yml`.
Run it once for MySQL and once for PostgreSQL. These commands do not enable paid
model calls or contact customer systems.

## CI diagnosis and maintenance

- Open the failed job before retrying. Browser failures retain traces, screenshots
  and local server logs for seven days. Open a trace with `pnpm exec playwright show-trace`.
- Dependency audit reports are retained for seven days, including failed audits.
  Update affected requirements and validate both supported Python versions; do not
  ignore advisories just to obtain a passing gate. Optional Python provider requirements
  are included in the audit even when their integrations are not exercised.
- Gitleaks scans checked-out Git history with findings redacted. The custom privacy
  scanner additionally checks company-specific publication patterns in current files.
  Neither scanner establishes that previously published GitHub caches were cleared.
- Dependabot proposes monthly dependency and action updates. Review and test these
  PRs before merging. The workflow token has read-only repository permissions.
- Container jobs have bounded health retries; every job has a time limit. New runs
  cancel obsolete work for the same PR/ref. Each database job starts only its own engine.

## Agent browser scenario

```bash
cd business-analytics-agent
python -m pip install -r requirements.txt
python -m portfolio_demo.agent_server
```

Open `http://127.0.0.1:8765` and ask:
`What were revenue share and growth for BRANCH003 in 2025?`

The default model replays a tool call for a narrowly supported question format.
LangChain executes the actual graph and validates the tool arguments; the tool queries
SQLite and calculates metrics using the shared domain functions. FastAPI streams
status, tool evidence, an answer and a completion event to the browser. Numbers in
the evidence panel come from the tool, not from generated prose. Ambiguous years
request clarification, missing history stays undefined, and errors clear stale results.

This is an additional portfolio reconstruction sharing the analytics repository and
metric rules. The original supervisor/specialist agents remain separate integrations
with their own service tests. The replay mode demonstrates orchestration correctness,
not natural-language understanding or live-model accuracy.

Optional live mode uses `OPENAI_API_KEY` and `DEMO_MODEL` from the environment:

```bash
python -m portfolio_demo.agent_server --live
```

It sends the question and synthetic tool evidence to the configured OpenAI model;
provider charges may apply. The process binds only to loopback and rejects foreign
hosts and cross-origin browser requests. It is a local demo, with no user-account or
authorization system for hosting real financial records. CI never enables live mode.
