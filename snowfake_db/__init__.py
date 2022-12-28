import contextlib

from snowfake_db.snowfake import SnowfakeCursor, SnowfakeConfig


@contextlib.contextmanager
def snowfake_cursor() -> SnowfakeCursor:
    """Stand-in for Snowflake's Python Connector."""
    yield SnowfakeCursor()
