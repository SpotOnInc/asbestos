# asbestos
An easy way to mock Snowflake connections in Python!

## What is this?

`asbestos` is a library to allow easy mocking of Snowflake calls during local development or testing to save on costs and time. The docs have more information, but here's a quick example:

```python
from asbestos import asbestos_cursor, config as asbestos_config


def snowflake_cursor() -> SnowflakeCursor | AsbestosCursor:
    # Use a flag to decide whether it returns the test cursor
    # or the real thing
    if settings.ENABLE_ASBESTOS:
        return asbestos_cursor()
    return snowflake_connection().cursor(DictCursor)


asbestos_config.register(
    query="your sql goes %s",
    data=("here",),
    response={"It's a": "response!"}
)

with snowflake_cursor() as cursor:
    cursor.execute("your sql goes %s", ('here',))
    assert cursor.fetchall() == {"It's a": "response!"}
```

`asbestos` is not a 1:1 mocking of the full Snowflake API, but includes synchronous and async query mocking that handle most use cases. Check out [some fun things you can do with it here][usage]!

## Installation:

```shell
poetry add asbestos-snow
```

The installation name is slightly different from the usage name due to someone claiming the name with no releases on PyPI; with luck, we will be able to finish the name requisition process to be able to use `asbestos` soon. If you're interested, you can [see how well that's going here](https://github.com/pypi/support/issues/2621).

## Docs

[Check out the documentation here!][docs]

To work on the docs locally, ensure that your `python3` version is up-to-date ([pyenv](https://github.com/pyenv/pyenv) is a great way of managing this) and run `make docs`. This will create a dedicated documentation environment and serve the docs locally for testing. To remove the environment, run `make docs_clean`.

## Development

`asbestos` uses `pre-commit` to help us keep the repo clean. To get started, make sure [you have `poetry` installed](https://python-poetry.org/) and follow these steps:

* clone the respository:
  * `git clone git@github.com:SpotOnInc/asbestos.git` (preferred)
  * OR `git clone https://github.com/SpotOnInc/asbestos`
* `poetry install`
* `poetry shell`
* `pre-commit install`

After that, you're ready to go!

[usage]: https://spotoninc.github.io/asbestos/usage/
[docs]: https://spotoninc.github.io/asbestos/
