import contextlib

from asbestos.asbestos import AsbestosConfig, AsbestosConn, AsbestosCursor

# Build a generic config that can be used by default
config = AsbestosConfig()


@contextlib.contextmanager
def asbestos_cursor() -> AsbestosCursor:
    """Stand-in for Snowflake's Python Connector."""
    yield AsbestosCursor(config)


conn = AsbestosConn(config=config)
