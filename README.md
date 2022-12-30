# snowfake_db
An easy way to mock Snowflake connections in Python!

## HEY!
**THIS IS NOT SNOWFLAKE.** If you want to connect to [SnowflakeDB](https://www.snowflake.com/en/) for real using Python, you will need to use the official library, [snowflake-connector-python](https://github.com/snowflakedb/snowflake-connector-python).

## What is this?

`snowfake_db` is a library to allow easy mocking of Snowflake calls during local development or testing to save on costs and time. The docs have more information, but here's a quick example:

```python
from snowfake_db import snowfake_cursor, config as snowfake_config

def snowflake_cursor() -> SnowflakeCursor | SnowfakeCursor:
    # Use a flag to decide whether it returns the test cursor
    # or the real thing
    if settings.ENABLE_SNOWFAKE:
        return snowfake_cursor()
    return snowflake_connection().cursor(DictCursor)


snowfake_config.register(
    query="your sql goes %s",
    data=("here",),
    response={"It's a": "response!"}
)

with snowflake_cursor() as cursor:
    cursor.execute("your sql goes %s", ('here',))
    assert cursor.fetchall() == {"It's a": "response!"}
```

`snowfake_db` is not a 1:1 mocking of the full Snowflake API, but includes synchronous and async query mocking that handle most use cases. Check out [some fun things you can do with it here][usage]!

## Installation:

```shell
poetry add snowfake-db  # watch out that you don't add an L!
```

## Docs

[Check out the documentation here!][docs]


[usage]: https://link-to-usage-page
[docs]: https://link-to-docs-root