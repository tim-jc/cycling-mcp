import os
from datetime import date, datetime
from typing import TypedDict
from zoneinfo import ZoneInfo

import mariadb
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

mcp = MCPServer("cycling-mcp")


class Activity(TypedDict):
    activity_id: int
    activity_name: str
    sport_type: str
    start_datetime_local: datetime
    distance_kilometres: float
    moving_time_seconds: int
    elevation_gain_metres: float


def parse_timezone_name(timezone_name: str) -> ZoneInfo:
    return ZoneInfo(timezone_name.split()[-1])


def fetch_activities(start_date: date, end_date: date) -> list[Activity]:
    with mariadb.connect(
        host=os.environ["CYCLING_MCP_DB_HOST"],
        port=int(os.environ["CYCLING_MCP_DB_PORT"]),
        user=os.environ["CYCLING_MCP_DB_USER"],
        password=os.environ["CYCLING_MCP_DB_PASSWORD"],
        database="cycling_platform_silver",
    ) as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """
                SELECT
                    activity_id,
                    activity_name,
                    sport_type,
                    start_datetime_local,
                    timezone_name,
                    distance_kilometres,
                    moving_time_seconds,
                    elevation_gain_metres
                FROM activities
                WHERE start_date_local BETWEEN ? AND ?
                ORDER BY start_datetime_local
                """,
                (start_date, end_date),
            )

            rows = cursor.fetchall()

    activities: list[Activity] = []

    for row in rows:
        activity: Activity = {
            "activity_id": row["activity_id"],
            "activity_name": row["activity_name"],
            "sport_type": row["sport_type"],
            "start_datetime_local": row["start_datetime_local"].replace(
                tzinfo=parse_timezone_name(row["timezone_name"])
            ),
            "distance_kilometres": row["distance_kilometres"],
            "moving_time_seconds": row["moving_time_seconds"],
            "elevation_gain_metres": row["elevation_gain_metres"],
        }
        activities.append(activity)

    return activities


@mcp.tool()
def get_activities(start_date: date, end_date: date) -> list[Activity]:
    """Return cycling activities within a specified local date range."""

    if start_date > end_date:
        raise ToolError("start_date must be on or before end_date")

    if (end_date - start_date).days > 90:
        raise ToolError("date range must not exceed 90 days")

    return fetch_activities(start_date, end_date)


if __name__ == "__main__":
    mcp.run()
