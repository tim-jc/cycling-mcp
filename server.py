from datetime import date, datetime
from typing import TypedDict
from zoneinfo import ZoneInfo

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


def fetch_activities(start_date: date, end_date: date) -> list[Activity]:
    activity: Activity = {
        "activity_id": 123456789,
        "activity_name": "Morning Ride",
        "sport_type": "Ride",
        "start_datetime_local": datetime(
            2026,
            8,
            29,
            7,
            30,
            tzinfo=ZoneInfo("Europe/London"),
        ),
        "distance_kilometres": 42.3,
        "moving_time_seconds": 5400,
        "elevation_gain_metres": 420.0,
    }

    if start_date <= activity["start_datetime_local"].date() <= end_date:
        return [activity]

    return []


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
