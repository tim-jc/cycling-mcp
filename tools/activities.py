import os
from datetime import date, datetime
from typing import TypedDict
from zoneinfo import ZoneInfo

import mariadb
from mcp.server.mcpserver.exceptions import ToolError


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


def row_to_activity(row: dict) -> Activity:
    return {
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


def get_connection():
    return mariadb.connect(
        host=os.environ["CYCLING_MCP_DB_HOST"],
        port=int(os.environ["CYCLING_MCP_DB_PORT"]),
        user=os.environ["CYCLING_MCP_DB_USER"],
        password=os.environ["CYCLING_MCP_DB_PASSWORD"],
        database="cycling_platform_silver",
    )


def fetch_activities(start_date: date, end_date: date) -> list[Activity]:
    with (
        get_connection() as connection,
        connection.cursor(dictionary=True) as cursor,
    ):
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

        return [row_to_activity(row) for row in rows]


def fetch_activity(activity_id: int) -> Activity | None:
    with (
        get_connection() as connection,
        connection.cursor(dictionary=True) as cursor,
    ):
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
            WHERE activity_id = ?
            """,
            (activity_id,),
        )

        row = cursor.fetchone()

    if row is None:
        return None

    return row_to_activity(row)


def order_activities(
    ranking_measure: str, ranking_direction: str, quantity: int
) -> list[Activity]:

    ranking_columns = {
        "distance": "distance_kilometres",
        "moving_time": "moving_time_seconds",
        "elevation_gain": "elevation_gain_metres",
    }

    ranking_directions = {
        "ascending": "ASC",
        "descending": "DESC",
    }

    if ranking_measure not in ranking_columns:
        raise ValueError(f"Unsupported ranking measure: {ranking_measure}")

    if ranking_direction not in ranking_directions:
        raise ValueError(f"Unsupported ranking direction: {ranking_direction}")

    if not 1 <= quantity <= 20:
        raise ValueError("quantity must be between 1 and 20")

    column = ranking_columns[ranking_measure]
    direction = ranking_directions[ranking_direction]

    with (
        get_connection() as connection,
        connection.cursor(dictionary=True) as cursor,
    ):
        cursor.execute(
            f"""
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
            ORDER BY {column} {direction}
            LIMIT ?
            """,
            (quantity,),
        )

        rows = cursor.fetchall()

    return [row_to_activity(row) for row in rows]


def register_activity_tools(mcp):
    @mcp.tool()
    def get_activities(start_date: date, end_date: date) -> list[Activity]:
        """Return cycling activities within a specified local date range."""

        if start_date > end_date:
            raise ToolError("start_date must be on or before end_date")

        if (end_date - start_date).days > 90:
            raise ToolError("date range must not exceed 90 days")

        return fetch_activities(start_date, end_date)

    @mcp.tool()
    def get_activity(activity_id: int) -> Activity:
        """Return a cycling activity identified by its activity ID."""

        activity = fetch_activity(activity_id)

        if activity is None:
            raise ToolError(f"activity_id {activity_id} was not found")

        return activity

    @mcp.tool()
    def rank_activities(
        ranking_measure: str, ranking_direction: str, quantity: int
    ) -> list[Activity]:
        """Rank cycling activities by a specified measure and direction, returning a specified quantity of activities."""

        # todo - check ranking measure supplied against allowed set and raise tool error if not in valid list

        # todo - define set of allowed ranking directions. If not ASC / DESC then add code to parse supplied
        # values and convert to ASC / DESC. Raise tool error if invalid value supplied.

        max_return = 25

        if quantity > max_return:
            raise ToolError(
                f"The maximum number of activities that can be returned is {max_return}"
            )

        return order_activities(ranking_measure, ranking_direction, quantity)
