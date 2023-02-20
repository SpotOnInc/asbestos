import pytest

from asbestos import config, conn, asbestos_cursor
from asbestos.exceptions import AsbestosDuplicateQuery, AsbestosMissingConfig
from asbestos.asbestos import AsbestosConn, AsbestosCursor


QUERY = "query"
INVALID_QUERY = "asdf"
RESPONSE = [{"response": "hi"}, {"hello there": "general kenobi"}]


@pytest.fixture(autouse=True)
def run_before_and_after_tests() -> None:
    """Ensure the query list is empty between tests."""
    # https://stackoverflow.com/a/62784688/2638784
    yield  # this is where the testing happens

    # Teardown
    config.clear_queries()


def test_generic_start() -> None:
    with asbestos_cursor() as cursor:
        assert isinstance(cursor, AsbestosCursor)


def test_default_response_fetchone() -> None:
    with asbestos_cursor() as cursor:
        cursor.execute(INVALID_QUERY)
        assert cursor.fetchone() == {}


def test_default_response_fetchall() -> None:
    with asbestos_cursor() as cursor:
        cursor.execute(INVALID_QUERY)
        assert cursor.fetchall() == {}


def test_query_creation() -> None:
    config.register(query=QUERY, response=RESPONSE)
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchall() == RESPONSE

    # make sure the query didn't disappear
    assert len(config.query_map) == 1


def test_ephemeral_query_creation() -> None:
    config.register_ephemeral(query=QUERY, response=RESPONSE)
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchall() == RESPONSE

    # ephemeral queries are only good for one call
    assert len(config.query_map) == 0


def test_fetchone_actually_fetches_one() -> None:
    config.register(query=QUERY, response=RESPONSE)
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchone() == RESPONSE[0]


def test_query_with_data() -> None:
    resp = {"different": "response"}
    config.register(query=QUERY, data=(1, 2), response=resp)
    with asbestos_cursor() as cursor:
        # Because we built the query with specific data, just a matching
        # query should return the default response because we don't have
        # the whole equation
        cursor.execute(QUERY)
        assert cursor.fetchone() == {}

        cursor.execute(QUERY, (1, 2))
        assert cursor.fetchone() == resp


def test_query_without_data() -> None:
    config.register(query=QUERY, response=RESPONSE)
    with asbestos_cursor() as cursor:
        # The query doesn't have special data, which means if we
        # pass in special data, we should fall down to the generic
        # "yeah the query matches" response.
        cursor.execute(QUERY, (1, 2))
        assert cursor.fetchall() == RESPONSE


def test_queries_with_different_data() -> None:
    resp = {"different": "response"}
    config.register(query=QUERY, response=RESPONSE)
    config.register(query=QUERY, data=(1, 2), response=resp)

    # Expected results: a query that matches the saved data should
    # return the special response, but a query with different data
    # should match the base response.
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY, (1, 2))
        assert cursor.fetchall() == resp

        cursor.execute(QUERY, ("albuquerque",))
        assert cursor.fetchall() == RESPONSE


def test_queries_with_no_base_response() -> None:
    config.register(query=QUERY, data=(1, 2), response=RESPONSE)
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchall() == {}


def test_add_duplicate_query() -> None:
    with pytest.raises(AsbestosDuplicateQuery):
        config.register(query=QUERY, response=RESPONSE)
        config.register(query=QUERY, response=RESPONSE)


def test_add_ephemeral_and_regular_duplicate_query() -> None:
    with pytest.raises(AsbestosDuplicateQuery):
        config.register(query=QUERY, response=RESPONSE)
        config.register_ephemeral(query=QUERY, response=RESPONSE)


def test_cursor_requires_config() -> None:
    with pytest.raises(AsbestosMissingConfig):
        AsbestosCursor()


def test_conn_cursor_connection() -> None:
    with conn.cursor() as cursor:
        conn.config.register(query=QUERY, response=RESPONSE)
        cursor.execute(QUERY)
        assert cursor.fetchall() == RESPONSE


def test_bare_conn_obj() -> None:
    new_conn = AsbestosConn()
    new_conn.config.register(query=QUERY, response=RESPONSE)
    with new_conn.cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchall() == RESPONSE


def test_async_query_default_response() -> None:
    # This is pulled directly from the documentation:
    # https://docs.snowflake.com/en/user-guide/python-connector-example.html#checking-the-status-of-a-query
    cur = conn.cursor()
    cur.execute_async("select count(*) from table(generator(timeLimit => 25))")
    # Wait for the query to finish running.
    query_id = cur.sfqid
    while conn.is_still_running(conn.get_query_status(query_id)):
        pass

    cur.get_results_from_sfqid(query_id)
    assert cur.fetchall() == {}


def test_async_query_registered_response() -> None:
    # This is pulled directly from the documentation:
    # https://docs.snowflake.com/en/user-guide/python-connector-example.html#checking-the-status-of-a-query
    conn.config.register(query=QUERY, response=RESPONSE)
    cur = conn.cursor()
    cur.execute_async(QUERY)
    # Wait for the query to finish running.
    query_id = cur.sfqid
    while conn.is_still_running(conn.get_query_status(query_id)):
        pass

    cur.get_results_from_sfqid(query_id)
    assert cur.fetchall() == RESPONSE


def test_fetchmany() -> None:
    config.register(
        query=QUERY,
        response=[
            {"a": 1},
            {"b": 2},
            {"c": 3},
            {"d": 4},
            {"e": 5},
        ],
    )
    with asbestos_cursor() as cursor:
        cursor.arraysize = 2
        cursor.execute(QUERY)
        assert cursor.fetchmany() == [{"a": 1}, {"b": 2}]
        assert cursor.fetchmany() == [{"c": 3}, {"d": 4}]
        assert cursor.fetchmany() == [{"e": 5}]


def test_fetchmany_default_page() -> None:
    config.register(query=QUERY, response=RESPONSE)
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchmany() == RESPONSE


def test_documentation_example() -> None:
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

    with asbestos_cursor() as cursor:
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
