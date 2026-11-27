# Cycling MCP ToolError investigation

The 26 November 2026 investigation verified that anticipated tool errors retain
their messages over stdio. Inspector’s intermittent browser timeout remains an
unresolved, non-blocking development tooling defect. The web backend and browser
client were not isolated from each other, so the timeout’s cause remains unknown.

## Verified environment and results

The investigation used Python 3.13.15, MCP Python SDK 2.1.1, Inspector 2.16.0,
Node 26.13.1 and npm 11.20.0 on macOS.

- The Python MCP client completed 100 interleaved calls to a minimal standalone
  server and 500 calls to Cycling MCP with synthetic data, each over five fresh
  stdio sessions.
- Inspector CLI returned eight descriptive standalone errors and eight
  successful responses in fresh processes.
- The Cycling MCP checks covered reversed dates, an endpoint difference greater
  than 90 days, an unknown activity ID, and ranking quantities of 0 and 26.
  Successful calls continued after error responses on the same connection.

Keep `ToolError` for these anticipated validation failures. It produces an
MCP result with `isError: true` and a descriptive message. Ranking measure
and direction are validated by the public schema. Internal SQL allowlist
checks also guard direct calls to the ranking helper.

## Run the regression probe

From the repository root with the existing virtual environment installed:

```sh
.venv/bin/python scripts/probe_tool_errors.py
```

The probe starts five local stdio sessions and checks 500 interleaved calls.
It uses the registered application handlers, substitutes synthetic query
results and blocks MariaDB connections. It requires no database or credentials.

## Use Inspector CLI

Use the verified Inspector version for repeatable checks. These examples use
the probe’s fixture server, so both calls can run without database access:

```sh
npx @modelcontextprotocol/inspector@2.16.0 --cli --method tools/list \
  .venv/bin/python scripts/probe_tool_errors.py --serve-fixture

npx @modelcontextprotocol/inspector@2.16.0 --cli --method tools/call \
  --tool-name get_activities --tool-arg start_date=2026-01-02 \
  --tool-arg end_date=2026-01-01 --format json \
  .venv/bin/python scripts/probe_tool_errors.py --serve-fixture
```

Expect exit status 0 for discovery and 5 for the anticipated error. In the
JSON result, check `isError: true` and the descriptive text in `content`.
For local browser work, `scripts/dev_inspector.sh` uses the repository’s
virtual environment interpreter directly.
