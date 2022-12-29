# Usage

Using `snowfake_db` is as straightforward as we can make it. The general flow looks like this:

- insert snowfake cursor in whatever way works best for you
- inform `snowfake_db` about your queries and what the expected responses are
- use it as normal!

If you use the recommended setup of the `snowfake_cursor()` function, then there are two pieces to juggle: the cursor function and the `config`.

## `snowfake_db`'s Config

The `config` object keeps track of all the queries that you've saved and a small handful of additional data. The primary method that you'll be using is called `.register()`, and it looks like this:

```python
from snowfake_db import config, snowfake_cursor

# This tells snowfake that you're going to pass a base SQL string, and
# when it sees that specific string, it should respond with the passed-in
# value.
config.register(query="select * from mytable", response={"HELLO": "WORLD"})

with snowfake_cursor() as cursor:
    cursor.execute("select * from mytable")
    assert cursor.fetchone() == {"HELLO": "WORLD"}
```

You can register as many queries as you want, and they can be as complex as you want (since they're just strings). You can also register queries that look for specific pieces of data! Since `snowflake` allows you to pass in SQL and values to substitute, `snowfake_db` accepts the same.

```python
from snowfake_db import config, snowfake_cursor

config.register(
    query="my very complicated query",
    data=(1, 2, 3),
    response={"HELLO": "WORLD"}
)

with snowfake_cursor() as cursor:
    cursor.execute("my very complicated query", (1, 2, 3))
    assert cursor.fetchone() == {"HELLO": "WORLD"}
```

If you have a query that is just the base SQL, it will accept any passed-in extra data:

```python
config.register(
    query="my query!",
    response={"HELLO": "WORLD"}
)

with snowfake_cursor() as cursor:
    cursor.execute("my query!", (1, 2, 3))
    assert cursor.fetchone() == {"HELLO": "WORLD"}
```

But if you register a query that is more complex than what you pass in, it will not match and will return Snowflake's default "we didn't find anything" response.

```python
config.register(
    query="my very complicated query",
    data=(1, 2, 3),
    response={"HELLO": "WORLD"}
)

with snowfake_cursor() as cursor:
    cursor.execute("my very complicated query")
    assert cursor.fetchone() == {}
```

The same goes for queries that are registered with data but different data is passed in; only specific matches will trigger.

## Single-use Queries

For testing purposes, sometimes it's helpful to have a query that can only be run once before vanishing into the ether. You can do that by using `config.register_ephemeral()`:

```python
config.register_ephemeral(
    query="Shhh, I'll only be available once!",
    response={"HELLO": "WORLD"}
)

with snowfake_cursor() as cursor:
    cursor.execute("Shhh, I'll only be available once!")
    # first time it's there...
    assert cursor.fetchone() == {"HELLO": "WORLD"}
    # second time it's not!
    assert cursor.fetchone() == {}
```

## Resetting the Query List

You can remove all the queries loaded by calling `config.clear_queries()`.

## The Cursor

The cursor object has all three fetch methods implemented and can be utilized as expected:

```python
config.register(
    query="Hello!",
    response=[
        {"a": 1},
        {"b": 2},
        {"c": 3},
        {"d": 4},
        {"e": 5},
    ],
)

with snowfake_cursor() as cursor:
    cursor.execute("Hello!")
    assert cursor.fetchone() == {"a": 1}
    assert cursor.fetchall() == [
        {"a": 1},
        {"b": 2},
        {"c": 3},
        {"d": 4},
        {"e": 5},
    ]
    cursor.arraysize = 2
    assert cursor.fetchmany() == [{"a": 1}, {"b": 2}]
    assert cursor.fetchmany() == [{"c": 3}, {"d": 4}]
    assert cursor.fetchmany() == [{"e": 5}]
```