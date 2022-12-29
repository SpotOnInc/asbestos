import contextlib

from snowfake_db.snowfake import SnowfakeConfig, SnowfakeConn, SnowfakeCursor

# Build a generic config that can be used by default
config = SnowfakeConfig()


@contextlib.contextmanager
def snowfake_cursor() -> SnowfakeCursor:
    """Stand-in for Snowflake's Python Connector."""
    yield SnowfakeCursor(config)


conn = SnowfakeConn(config=config)
