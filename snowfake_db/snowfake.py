from typing import Any, Optional

from snowfake_db.exceptions import SnowfakeMissingConfig, SnowfakeDuplicateQuery

EXAMPLE_QUERY = "hello"
EXAMPLE_RESPONSE = "world"

# Monkeypatch this from anywhere to make Snowfake return whatever you need.
# Example usage:
# >>> import snowfake_db.snowfake
# >>> from snowfake_db.snowfake import snowfake_cursor
# >>> snowfake_db.snowfake.OVERRIDE_RESPONSE = "HAXORED"
# >>> with snowfake_cursor() as cursor:
# ...   cursor.execute('hello', ('datadatadata',))
# ...   cursor.fetchone()
# ...
# 'HAXORED'
#
# Manually reset to None when you're done and it'll use the map as expected.
OVERRIDE_RESPONSE = None


class SnowfakeResponse:
    """
    Internal representation of queries, data, and responses.

    A SnowfakeResponse has four primary attributes:

    query: str -> the raw SQL query that you would pass to Snowflake.
    data: Optional[tuple[Any]] -> if you use %s substitution, this is your substitution
        data.
    response: dict[Any] -> the data that Snowflake would normally respond with.
    ephemeral: bool -> a flag that denotes whether this is a single-use query.
    """
    def __init__(
        self, query: str, response: dict[Any], ephemeral: bool = False, data: Optional[tuple[Any]] = None
    ):
        self.query: str = query
        self.data: Optional[tuple[Any]] = data
        self.response: dict[Any] = response
        self.ephemeral: bool = ephemeral

    def __str__(self) -> str:
        query = f"{self.query[:30]}..." if len(self.query) > 30 else self.query
        if self.data:
            data = str(self.data)
            data = f"{data[:30]}..." if len(data) > 30 else data
        else:
            data = None

        response = str(self.response)
        response = f"{response[:30]}..." if len(response) > 30 else response

        if self.ephemeral:
            value = "EphemeralSnowfakeResponse: "
        else:
            value = "SnowfakeResponse: "

        value += f" {query}"
        if self.data:
            value += f"+ {data} "
        value += f"-> {response}"

        return value


class SnowfakeConfig:
    """
    The cursor in Snowfake takes a single argument of an instance of `SnowfakeConfig`.
    When using the built-in `snowfake_cursor()`, it automatically uses a global
    config built just for this purpose.

    !!! warning "Hey!"

        If you're using the default `snowfake_cursor()`, you do not need to instantiate
        your own instance of this class. Just import the existing version from
        `snowflake_db.config`.
    """

    def __init__(self):
        self.query_map: list[SnowfakeResponse] = []
        self.data = {}
        self.default_response: SnowfakeResponse = SnowfakeResponse(query="", response={})

    def lookup_query(self, query, data) -> SnowfakeResponse:
        # We'll separate this into two stages. First, we find all the responses
        # that _could_ be a match, then we'll filter through those to find the
        # most appropriate match.

        possible_matches = [resp for resp in self.query_map if resp.query == query]

        if not possible_matches:
            return self.default_response

        if len(possible_matches) == 1:
            return possible_matches[0]

        # If we make it down here, then there are queries that have specific responses
        # and we need to account for that.
        for option in possible_matches:
            if option.data == data:
                return option

        # Now that we know the specific data we're looking for isn't here, do we have
        # one that's just the bare query?
        for option in possible_matches:
            if option.data is None:
                return option

        # if we fall down here, we don't have anything that matches.
        return self.default_response

    def remove_ephemeral_response(self, resp: SnowfakeResponse) -> None:
        # Ephemeral queries are only good for one call. Remove it from the list so that
        # it can't show up again.
        if resp == self.default_response:
            # can't nuke the default because it's technically not in the list
            return

        if resp.ephemeral:
            self.query_map.pop(self.query_map.index(resp))

    def check_for_duplicates(self, query: str, data: tuple, ephemeral: bool) -> None:
        for option in self.query_map:
            if option.query == query and option.data == data:
                # We have a duplicate. Now we just need to figure out what error to show.
                if option.ephemeral != ephemeral:
                    # we have the same query, but they were created two different ways.
                    raise SnowfakeDuplicateQuery(
                        "You can't have an ephemeral and non-ephemeral version of the"
                        " same query active at the same time."
                    )
                raise SnowfakeDuplicateQuery("You've already registered this query!")

    def register(self, query: str, response: dict, data: tuple = None) -> None:
        """
        Snowfake will watch for any call that includes the query passed in
        and return the response you save. If data is provided with the query,
        the response will only be returned if the query and data match exactly.
        A query with no data will match any data passed in, though.

        Example:

        ```python
        >>> config.register(query="A", response="B")
        >>> cursor.execute("A")
        >>> cursor.fetchone()
        "B"  # This matches, so we get what we expect
        ```

        Because our registered response doesn't have data attached to it, it
        will match all queries that are more specific.

        ```python
        >>> cursor.execute("A", ("AAA",))
        >>> cursor.fetchone()
        "B"
        ```

        However, if our registered response is more specific than the query, it will
        not match.

        ```python
        >>> config.clear_queries()
        >>> config.register(query="A", data="D", response="B")
        >>> cursor.execute("A", ("D",))
        >>> cursor.fetchone()
        "B"  # this matches the saved query exactly, so we get the expected response
        >>> cursor.execute("A")
        >>> cursor.fetchone()
        {}  # default response
        >>> cursor.execute("A", ("E",))  # extra data doesn't match!
        >>> cursor.fetchone()
        {}  # default response
        ```
        """
        self.check_for_duplicates(query=query, data=data, ephemeral=False)
        self.query_map.append(
            SnowfakeResponse(query=query, data=data, response=response, ephemeral=False)
        )

    def register_ephemeral(self, query: str, response: dict, data: tuple = None) -> None:
        """
        Works the same way as `SnowfakeConfig.register()` with the only difference being
        that after this query is called, it is removed from the list. This can be used
        for tests or other situations where you need a call to succeed only once.
        """
        self.check_for_duplicates(query=query, data=data, ephemeral=True)
        self.query_map.append(
            SnowfakeResponse(query=query, data=data, response=response, ephemeral=True)
        )

    def clear_queries(self):
        """Remove all the registered queries and responses."""
        self.query_map = []


class SnowfakeCursor:
    """
    Analogue for Snowflake's cursor object.

    If you're wanting to use this as a manually-constructed object, you will need
    to create an instance of SnowfakeConfig first, then pass it into your cursor. The
    easiest way to handle this is to treat it like the instantiation that is used in
    Snowfake:

    ```python
    import contextlib

    from snowfake_db.snowfake import SnowfakeCursor, SnowfakeConfig


    myconfig = SnowfakeConfig()

    # set up myconfig here
    ...

    @contextlib.contextmanager
    def my_custom_cursor() -> SnowfakeCursor:
        yield SnowfakeCursor(config=myconfig)
    ```
    """

    def __init__(self, config: SnowfakeConfig = None) -> None:
        self.query = None
        self.data = None
        if not config:
            raise SnowfakeMissingConfig(
                "If you're making a custom cursor, you will need to"
                " create a configuration and pass it in here."
            )
        self.config = config

    def execute(self, query: str, inserted_data: tuple = None) -> None:
        self.query = query
        self.data = inserted_data

    def _get(self) -> dict | list[dict]:
        return (
            OVERRIDE_RESPONSE
            if OVERRIDE_RESPONSE
            else self.config.remove_ephemeral_response(
                self.config.lookup_query(self.query, self.data)
            )
        )

    def fetchone(self) -> dict | list[dict]:
        return self._get()

    def fetchall(self) -> dict | list[dict]:
        return self._get()
