"""Exercise Cycling MCP tool errors over stdio with synthetic activity data."""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
RANKING = {"ranking_measure": "distance", "ranking_direction": "ascending"}
VALID_DATES = {"start_date": "2026-01-01", "end_date": "2026-01-01"}
ERROR_CASES = [
    (
        "get_activities",
        {"start_date": "2026-01-02", "end_date": "2026-01-01"},
        "start_date must be on or before end_date",
    ),
    (
        "get_activities",
        {"start_date": "2026-01-01", "end_date": "2026-04-02"},
        "date range must not exceed 90 days",
    ),
    ("get_activity", {"activity_id": 999}, "activity_id 999 was not found"),
    *[
        (
            "rank_activities",
            {**RANKING, "quantity": quantity},
            "quantity must be between 1 and 25",
        )
        for quantity in (0, 26)
    ],
]
SUCCESS_ARGUMENTS = {
    "get_activity": {"activity_id": 123},
    "get_activities": VALID_DATES,
    "rank_activities": {**RANKING, "quantity": 1},
}


def serve_fixture():
    sys.path.insert(0, str(ROOT))
    from server import mcp

    row = {
        "activity_id": 123,
        "activity_name": "Fixture ride",
        "sport_type": "Ride",
        "start_datetime_local": datetime(2026, 1, 1, tzinfo=UTC),
        "distance_kilometres": 1.0,
        "moving_time_seconds": 60,
        "elevation_gain_metres": 2.0,
    }
    with (
        patch(
            "mariadb.connect", side_effect=AssertionError("Database access is disabled")
        ),
        patch(
            "tools.activities.fetch_activity",
            side_effect=lambda i: row if i == 123 else None,
        ),
        patch("tools.activities.fetch_activities", return_value=[row]),
        patch("tools.activities.order_activities", return_value=[row]),
    ):
        mcp.run()


async def probe():
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).resolve()), "--serve-fixture"],
        cwd=ROOT,
    )
    count = 0
    slowest = 0.0
    for _ in range(5):
        async with (
            stdio_client(params) as (reader, writer),
            ClientSession(reader, writer, read_timeout_seconds=3) as session,
        ):
            await session.initialize()
            for name, arguments, message in ERROR_CASES * 10:
                started = perf_counter()
                error = await session.call_tool(name, arguments)
                slowest = max(slowest, perf_counter() - started)
                if not error.is_error or not any(
                    message in getattr(block, "text", "") for block in error.content
                ):
                    raise AssertionError(f"{name} did not return {message!r}: {error}")

                started = perf_counter()
                success = await session.call_tool(name, SUCCESS_ARGUMENTS[name])
                slowest = max(slowest, perf_counter() - started)
                payload = success.structured_content or {}
                rows = [payload] if name == "get_activity" else payload.get("result")
                if success.is_error or not rows or rows[0].get("activity_id") != 123:
                    raise AssertionError(
                        f"{name} did not return the fixture: {success}"
                    )
                count += 2
    print(
        f"Passed {count} calls across 5 stdio sessions. Slowest call: {slowest:.3f}s."
    )


if __name__ == "__main__":
    if sys.argv[1:] == ["--serve-fixture"]:
        serve_fixture()
    else:
        asyncio.run(probe())
