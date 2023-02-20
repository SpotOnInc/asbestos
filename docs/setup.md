# Setup

Snowflake offers a few different ways to utilize the library depending on the functionality that you need, so `asbestos` offers three ways to utilize it.

- prebuilt cursor context manager
- prebuilt conn object
- manual cursor creation

The first two are equal in terms of usability and are intended as drop-in solutions. If you need something more specific, check out the manual creation!

## Prebuilt Cursor Context Manager

The way that we most commonly use Snowflake at SpotOn is by taking advantage of the fact that Snowflake doesn't check credentials until the first call after instantiating the connector and utilizing a helper function to grab the cursor whenever it's needed. Here's a simplified view of what that looks like in practice:

```python
from asbestos import asbestos_cursor
from snowflake import connector as snowflake_connector
from snowflake.connector.connection import SnowflakeConnection
from snowflake.connector.cursor import DictCursor, SnowflakeCursor


def snowflake_connection() -> SnowflakeConnection:
    # this can be instantiated with null data and it won't explode
    # until the cursor is created and called.
    return snowflake_connector.connect(
        user=settings.SNOWFLAKE_USER,
        password=settings.SNOWFLAKE_PASSWORD,
        account=settings.SNOWFLAKE_ACCOUNT,
        warehouse=settings.SNOWFLAKE_WAREHOUSE,
        database=settings.SNOWFLAKE_DB,
        schema=settings.SNOWFLAKE_SCHEMA,
    )


def snowflake_cursor() -> SnowflakeCursor | AsbestosCursor:
    # if ENABLE_ASBESTOS is set to True, the real cursor will never
    # trigger and the connector will never realize that it has bad
    # data, so we don't have to worry about credentials when testing.
    if settings.ENABLE_ASBESTOS:
        return asbestos_cursor()
    return snowflake_connection().cursor(DictCursor)


def injected_snowflake_cursor(
        cursor: Optional[AsbestosCursor] = None
) -> SnowflakeCursor:
    # If you prefer dependency injection, you can also build it like this!
    return cursor if cursor else snowflake_connection().cursor(DictCursor)
```

In normal usage, this allows us to write queries backed by Snowflakes auto-rollback handling that essentially follow this format:

```python
with snowflake_cursor() as cursor:
    cursor.execute("select * from table")
    result = cursor.fetchall()
```

If you flip the flag for ENABLE_ASBESTOS (or whatever you want to call the flag in your system), it simply returns the mockable cursor instead, which lets you quickly swap between local development, production, and tests. `asbestos` is set up to make this type of usage as easy as possible.

## Prebuilt Conn Object

Sometimes, especially when working with async queries, you need access to the connection object that spawned the cursor. `asbestos` has a connector that it makes available for just this purpose and can be imported as `from asbestos import conn`.

When using the prebuilt `conn` object, everything you need to work with the connection is located on that object, including the `cursor` and the `config`, which is a special object we'll touch on in a bit. Here's an example using lightly edited [async code from the Snowflake documentation](https://docs.snowflake.com/en/user-guide/python-connector-example.html#checking-the-status-of-a-query):

```python
from asbestos import conn

count_query = "select count(*) from table(generator(timeLimit => 25))"
count_query_response = {"COUNT": 42}

# tell asbestos to look for this particular query
conn.config.register(query=count_query, response=count_query_response)

cur = conn.cursor()
cur.execute_async("select count(*) from table(generator(timeLimit => 25))")
# Wait for the query to finish running.
query_id = cur.sfqid
while conn.is_still_running(conn.get_query_status(query_id)):
    pass

cur.get_results_from_sfqid(query_id)
assert cur.fetchall() == {"COUNT": 42}
```

## Manual Cursor Creation

!!! warning "Hold on!"

    Creating the `asbestos` connections and cursor is possible, but you're probably going to have a worse time. We recommend using one of the two prebuilt options above if you can.

While this method isn't recommended, it is possible. You have two methods here of creating your own cursor with varying amounts of usability. 

### Manual Setup with AsbestosConn

The `AsbestosConn` object is pre-configured to build all the necessary parts automatically when you instantiate it, so the only thing you need to do is import it and instantiate it; then you're good to go!

```python
from asbestos import AsbestosConn

myconn = AsbestosConn()
```

### Manual Setup with AsbestosCursor

The cursor object is a bit more temperamental and requires the additional setup of a standalone `AsbestosConfig` object as well, since the `AsbestosConfig` object controls the cursor. Here's how to set it up:

```python
import contextlib

from asbestos import AsbestosConfig, AsbestosCursor

myconfig = AsbestosConfig()


@contextlib.contextmanager
def asbestos_cursor() -> AsbestosCursor:
    yield AsbestosCursor(myconfig)


# Usage:
with asbestos_cursor() as cursor:
    cursor.execute(...)
    ...
```

It's highly recommended to use one of the other setups if they work for you, as this one just has more moving pieces.
