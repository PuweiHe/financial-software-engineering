"""Local agent demo: LangChain tools, SQLite evidence and streamed browser results."""

import argparse
import asyncio
from contextlib import asynccontextmanager
import json
import os
import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict, Field
from sse_starlette import EventSourceResponse
import uvicorn

from portfolio_demo.server import ASSETS, ROOT, MetricsRepository


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=500)


class ReportArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    year: int = Field(ge=1900, le=9999)
    branch_id: str | None = Field(default=None, pattern=r"^BRANCH[0-9]{3}$")


class ScriptedModel(GenericFakeChatModel):
    """Replay tool calls for supported demo questions without an external provider."""

    def bind_tools(self, tools, **kwargs):
        return self


def replay_model(question):
    years = re.findall(r"\b(?:19|20)[0-9]{2}\b", question)
    branches = re.findall(r"\bBRANCH[0-9]{3}\b", question.upper())
    if (
        len(set(years)) != 1
        or len(set(branches)) > 1
        or not re.search(r"revenue|growth|share|收入|同比|贡献", question, re.IGNORECASE)
    ):
        return ScriptedModel(
            disable_streaming=True,
            messages=iter(
                [
                    AIMessage(
                        content="Ask about revenue, share or growth for one year, optionally one BRANCH ID."
                    )
                ]
            ),
        )
    arguments = {"year": int(years[0]), "branch_id": branches[0] if branches else None}
    return ScriptedModel(
        disable_streaming=True,
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[{"name": "branch_report", "args": arguments, "id": "report"}],
                ),
                AIMessage(
                    content="Review the returned SQLite evidence; missing history remains undefined."
                ),
            ]
        ),
    )


def make_app(repository=None, model_factory=None, mode="scripted"):
    owns_repository = repository is None
    if owns_repository:
        repository = MetricsRepository(json.loads((ROOT / "examples/branches.json").read_text()))
    if model_factory is None:
        if mode == "live":
            # The provider is opt-in and receives only questions and synthetic evidence.
            if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("DEMO_MODEL"):
                raise ValueError("Live mode requires OPENAI_API_KEY and DEMO_MODEL")

            def model_factory(question):
                return ChatOpenAI(
                    model=os.environ["DEMO_MODEL"], temperature=0, timeout=15, max_retries=1
                )
        else:
            model_factory = replay_model

    @asynccontextmanager
    async def lifespan(app):
        yield
        if owns_repository:
            repository.close()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    @app.get("/healthz")
    async def health():
        return {"status": "ok", "synthetic": True}

    @app.get("/api/capabilities")
    async def capabilities():
        return {"agent": True, "mode": mode}

    @app.get("/api/years")
    async def years():
        return {"years": repository.years(), "synthetic": True}

    @app.get("/api/metrics")
    async def metrics(year: int, branch_id: str | None = None):

        if year not in repository.years():
            raise HTTPException(404, "Year is unavailable")
        try:
            return repository.report(year, branch_id)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/api/agent/stream")
    async def ask(body: Question, request: Request):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            raise HTTPException(403, "Cross-origin requests are not allowed")

        async def events():
            # Evidence belongs to this request; model prose never supplies report numbers.
            evidence = []

            @tool(args_schema=ReportArguments)
            async def branch_report(year: int, branch_id: str | None = None) -> str:
                """Read revenue, share and prior-year growth for one year from synthetic SQLite."""
                if year not in repository.years():
                    return json.dumps({"error": "Year is unavailable"})
                try:
                    report = await asyncio.to_thread(repository.report, year, branch_id)
                except LookupError:
                    return json.dumps({"error": "Branch is unavailable"})
                evidence.append(report)
                return json.dumps(report, allow_nan=False)

            def event(name, data):
                return {"event": name, "data": json.dumps(data, allow_nan=False)}

            try:
                async with asyncio.timeout(30):
                    model = model_factory(body.question)
                    graph = create_agent(
                        model=model,
                        tools=[branch_report],
                        middleware=[ToolCallLimitMiddleware(run_limit=2, exit_behavior="error")],
                        system_prompt=(
                            "Answer branch revenue, share and growth questions using branch_report. "
                            "Ask for clarification if the year is missing or ambiguous. "
                            "Use only returned evidence. Missing history is not zero growth. "
                            "Do not invent values or claim access to real customer data."
                        ),
                    )
                    yield event("status", {"message": "Selecting a tool", "mode": mode})
                    async for item in graph.astream_events(
                        {"messages": [{"role": "user", "content": body.question}]},
                        config={"recursion_limit": 10},
                        version="v2",
                    ):
                        if item["event"] == "on_tool_start":
                            yield event("status", {"message": "Reading synthetic SQLite records"})
                        elif item["event"] == "on_tool_end":
                            if evidence:
                                yield event("report", evidence.pop(0))
                            else:
                                yield event(
                                    "status", {"message": "No report available for this request"}
                                )
                        elif item["event"] == "on_chat_model_end":
                            message = item["data"].get("output")
                            content = getattr(message, "content", "")
                            if isinstance(content, str) and content:
                                yield event("answer", {"text": content})
                    yield event("done", {"synthetic": True})
            except asyncio.CancelledError:
                raise
            except TimeoutError:
                yield event("error", {"message": "Request timed out. Please retry."})
            except Exception:
                yield event("error", {"message": "The agent could not complete the request."})

        return EventSourceResponse(events(), send_timeout=10)

    @app.get("/")
    async def index():
        return FileResponse(ASSETS / "index.html")

    @app.get("/app.js")
    async def javascript():
        return FileResponse(ASSETS / "app.js", media_type="text/javascript")

    @app.get("/style.css")
    async def stylesheet():
        return FileResponse(ASSETS / "style.css", media_type="text/css")

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--live", action="store_true", help="Use an explicitly configured model")
    args = parser.parse_args()
    uvicorn.run(
        make_app(mode="live" if args.live else "scripted"), host="127.0.0.1", port=args.port
    )
