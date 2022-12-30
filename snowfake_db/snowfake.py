import random
from typing import Any, Optional

from snowfake_db.exceptions import SnowfakeDuplicateQuery, SnowfakeMissingConfig

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
    data: Optional[tuple[Any]] -> if you use substitution, this is your substitution
        data.
    response: dict[Any] -> the data that Snowflake would normally respond with.
    ephemeral: bool -> a flag that denotes whether this is a single-use query.
    """

    def __init__(
        self,
        query: str,
        response: dict[Any],
        ephemeral: bool = False,
        data: Optional[tuple[Any]] = None,
    ) -> None:
        self.query: str = query
        self.data: Optional[tuple[Any]] = data
        self.response: dict[Any] | list[dict[Any]] = response
        self.ephemeral: bool = ephemeral
        self.sfqid: int = 0
        self.set_sfqid()

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

    def set_sfqid(self) -> None:
        self.sfqid = random.randrange(10000, 60000)


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

    def __init__(self) -> None:
        self.query_map: list[SnowfakeResponse] = []
        self.last_run_query: Optional[SnowfakeResponse] = None
        self.data = {}
        self.default_response: SnowfakeResponse = SnowfakeResponse(
            query="", response={}
        )

    def lookup_query(self, query: str, data: Optional[tuple]) -> SnowfakeResponse:
        # We'll separate this into two stages. First, we find all the responses
        # that _could_ be a match, then we'll filter through those to find the
        # most appropriate match.

        possible_matches = [resp for resp in self.query_map if resp.query == query]

        if not possible_matches:
            return self.default_response

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

    def register_ephemeral(
        self, query: str, response: dict, data: tuple = None
    ) -> None:
        """
        Works the same way as `SnowfakeConfig.register()` with the only difference being
        that after this query is called, it is removed from the list. This can be used
        for tests or other situations where you need a call to succeed only once.
        """
        self.check_for_duplicates(query=query, data=data, ephemeral=True)
        self.query_map.append(
            SnowfakeResponse(query=query, data=data, response=response, ephemeral=True)
        )

    def clear_queries(self) -> None:
        """Remove all the registered queries and responses."""
        self.query_map = []
        self.last_run_query = None


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
        self.query: Optional[str] = None
        self.data: Optional[tuple] = None
        self.arraysize: int = 10

        # used to keep track of "pagination" in `.fetchmany()`
        self.last_page_start: int = 0
        self.last_paginated_query: Optional[int] = None

        if not config:
            raise SnowfakeMissingConfig(
                "If you're making a custom cursor, you will need to"
                " create a configuration and pass it in here."
            )
        self.config: SnowfakeConfig = config

    @property
    def sfqid(self) -> Optional[int]:
        """
        Retrieve the ID of the last-run query or None.

        In Snowflake, the `sfqid` is an ID that's attached to every query
        that's run. In `snowfake_db`, it's a random number attached to a
        query. If you pass this value to `get_results_from_sfqid()`, it will
        reset the cursor to the values from that query to effectively run
        it again.
        """
        if self.config.last_run_query:
            return self.config.last_run_query.sfqid
        return None

    def execute(self, query: str, inserted_data: tuple = None) -> None:
        """
        Pass SQL to `snowfake_db` for processing.

        Saves the SQL and any passed-in data to the cursor and starts the
        process of finding your pre-saved response. To get the data, you will
        need to call one of the fetch* methods listed below.
        """
        self.query = query
        self.data = inserted_data
        self._get()

    def execute_async(self, *args, **kwargs) -> None:
        """Functions the same as `.execute()`."""
        self.execute(*args, **kwargs)

    def _get(self) -> dict | list[dict]:
        resp = self.config.lookup_query(self.query, self.data)
        self.config.remove_ephemeral_response(resp)
        self.config.last_run_query = resp
        return OVERRIDE_RESPONSE if OVERRIDE_RESPONSE else resp.response

    def fetchone(self) -> dict:
        """
        Return the first result from the saved response for a query.

        `fetchone` takes a pre-saved query and only gives the first piece of data
        from the response. Example:

        ```python
        config.register(query="A", response=[{'a':1}, {'b': 2}])
        with snowfake_cursor() as cursor:
            cursor.execute("A")
            resp = cursor.fetchall()

        # resp = {'a':1}
        ```
        """
        resp = self.config.last_run_query.response
        if len(resp) > 1:
            return resp[0]
        return self._get()

    def fetchall(self) -> list[dict]:
        """
        Return the entire saved response.

        Whereas `fetchone` will only return the first entry from a saved response,
        `fetchall` does what it sounds like it does. Example:

        ```python
        config.register(query="A", response=[{'a':1}, {'b': 2}])
        with snowfake_cursor() as cursor:
            cursor.execute("A")
            resp = cursor.fetchall()

        # resp = [{'a':1}, {'b': 2}]
        ```
        """
        return self.config.last_run_query.response

    def fetchmany(self, size: int = None) -> list[dict]:
        """
        Return a paged subset of the saved response.

        Uses `cursor.arraysize` to control the page size or just pass your
        requested page size into the function: `.fetchmany(200)`. Automatically
        paginates the response so that you can just keep calling it until you
        run out of response for it to return. Example:

        ```python
        config.register(query="A", response=[{'a':1}, {'b': 2}])

        cursor.arraysize = 1  # return one response at a time
        with snowfake_cursor() as cursor:
            cursor.execute("A")
            cursor.fetchmany(1)  # [{'a':1}]
            cursor.fetchmany(1)  # [{'b': 2}]
            cursor.fetchmany(1)  # []
        ```
        """
        size = size if size else self.arraysize
        if self.last_paginated_query != self.config.last_run_query.sfqid:
            # this is the first time we're paginating here
            self.last_page_start = 0
            self.last_paginated_query = self.config.last_run_query.sfqid

        response = self.config.last_run_query.response[
            self.last_page_start : size + self.last_page_start
        ]
        self.last_page_start += size
        return response

    def close(self) -> None:
        """
        Reset the queries and "close" the connection.
        """
        self.config.clear_queries()
        return

    def get_results_from_sfqid(self, query_id: int) -> None:
        """
        Resets the last-run information to the given query ID.

        If you pass a sfqid from a previously-run query, it will rebuild the
        cursor using the data from that query, effectively allowing you to
        run the query again without calling `.execute()`.

        !!! warning "Watch out!"

            Ephemeral queries are only recoverable if they are the last query
            you ran. After you run another query, it will be fully replaced
            and cannot be recovered via its ID.
        """
        for option in self.config.query_map:
            if option.sfqid == query_id:
                self.query = option.query
                self.data = option.data
                break
        else:
            # setting the query and data to None if the above lookup fails means
            # that the next fetch will return the default response.
            self.query = None
            self.data = None

    def __enter__(self, *args: Any, **kwargs: Any) -> "SnowfakeCursor":
        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        pass


class SnowfakeConn:
    """
    Connector to house the Snowfake Cursor object.

    The real Snowflake connector has two methods for interacting with it: either a
    cursor object directly (`cursor.execute()`) or a `connection` object that is
    referenced directly (`conn.cursor.execute()`). Since the goal is that this can be
    a more-or-less drop-in replacement, we provide an optional connector that can be
    used to spawn the default cursor.

    !!! note "The SnowfakeConn doesn't use the default config!"

        If you want to use this, you will need to configure it through the `config`
        object that is located on this instance. Example:
        ```python
        from snowfake_db import SnowfakeConn

        myconn = SnowfakeConn()
        myconn.config.register("select * from...", {"MY_EXPECTED": "DATA"})
        with myconn.cursor() as cursor:
            ...
        ```
    """

    def __init__(self, config: SnowfakeConfig = None) -> None:
        self.config = config if config else SnowfakeConfig()

    def cursor(self) -> SnowfakeCursor:
        return SnowfakeCursor(self.config)

    def get_query_status(self, *args: Any) -> int:
        """
        Check on a currently-running async query.

        Returns 2, the Snowflake QueryStatus Success value.
        """
        # https://github.com/snowflakedb/snowflake-connector-python/blob/d957164c5822db5a354baa3aa3366134ed7e98d5/src/snowflake/connector/constants.py#L270-L285
        return 2  # SUCCESS

    def is_still_running(self, *args: Any) -> bool:
        """Check long-running async queries. Will always return False."""
        return False

    def close(self) -> None:
        """Reset the queries and "close" the connection."""
        self.config.clear_queries()
        return
