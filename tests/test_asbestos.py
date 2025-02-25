from typing import Any, Callable
from unittest.mock import patch

import pytest

from asbestos import asbestos_cursor, config, conn
import asbestos.asbestos
from asbestos.asbestos import AsbestosConn, AsbestosCursor, EphemeralContext
from asbestos.exceptions import AsbestosDuplicateQuery, AsbestosMissingConfig

QUERY = "query"
QUERY2 = "another query"
INVALID_QUERY = "asdf"
RESPONSE = [{"response": "hi"}, {"hello there": "general kenobi"}]
OVERRIDE_RESPONSE = "Hi!"
SHORT_BATCH_RESPONSE = [
    {"a": 1},
    {"b": 2},
    {"c": 3},
    {"d": 4},
    {"e": 5},
]
LARGE_BATCH_RESPONSE = [
    {"a": 1},
    {"b": 2},
    {"c": 3},
    {"d": 4},
    {"e": 5},
    {"f": 6},
    {"g": 7},
    {"h": 8},
    {"i": 9},
    {"j": 10},
    {"k": 11},
    {"l": 12},
    {"m": 13},
    {"n": 14},
    {"o": 15},
]


def set_override_response(override_value: Any) -> Callable:
    def inner(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> None:
            asbestos.asbestos.OVERRIDE_RESPONSE = override_value
            func(*args, **kwargs)
            asbestos.asbestos.OVERRIDE_RESPONSE = None

        return wrapper

    return inner


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
        assert cursor.fetchall() == []


def test_default_response_fetchmany() -> None:
    with asbestos_cursor() as cursor:
        cursor.execute(INVALID_QUERY)
        assert cursor.fetchmany() == []


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


def test_register_returns_sfqid() -> None:
    with patch("asbestos.asbestos.random.randrange", lambda x, y: 999):
        sfqid = config.register(query=QUERY, response=RESPONSE)
        assert sfqid == 999


def test_register_ephemeral_returns_sfqid() -> None:
    with patch("asbestos.asbestos.random.randrange", lambda x, y: 999):
        sfqid = config.register_ephemeral(query=QUERY, response=RESPONSE)
        assert sfqid == 999


def test_remove_query_by_sfqid() -> None:
    query_id = config.register(query=QUERY, response=RESPONSE)
    assert type(query_id) == int
    assert len(config.query_map) == 1

    result = config.remove_query_by_sfqid(query_id)
    assert result is True
    assert len(config.query_map) == 0


def test_removing_nonexistent_query() -> None:
    assert len(config.query_map) == 0
    result = config.remove_query_by_sfqid(999)
    assert result is False
    assert len(config.query_map) == 0


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
    resp = [{"different": "response"}]  # list because we're testing fetchall()
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
        assert cursor.fetchall() == []


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
    assert cur.fetchall() == []


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
        response=SHORT_BATCH_RESPONSE,
    )
    with asbestos_cursor() as cursor:
        cursor.arraysize = 2
        cursor.execute(QUERY)
        assert cursor.fetchmany() == [{"a": 1}, {"b": 2}]
        assert cursor.fetchmany() == [{"c": 3}, {"d": 4}]
        assert cursor.fetchmany() == [{"e": 5}]


def test_fetchmany_with_value_in_call() -> None:
    config.register(
        query=QUERY,
        response=SHORT_BATCH_RESPONSE,
    )
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchmany(2) == [{"a": 1}, {"b": 2}]
        assert cursor.fetchmany(2) == [{"c": 3}, {"d": 4}]
        assert cursor.fetchmany(2) == [{"e": 5}]


def test_fetchmany_default_page() -> None:
    config.register(query=QUERY, response=LARGE_BATCH_RESPONSE)
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchmany() == LARGE_BATCH_RESPONSE[:10]


def test_fetchmany_local_size_overrides_arraysize() -> None:
    config.register(
        query=QUERY,
        response=SHORT_BATCH_RESPONSE,
    )
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        cursor.arraysize = 10
        assert cursor.fetchmany(2) == [{"a": 1}, {"b": 2}]
        assert cursor.fetchmany(2) == [{"c": 3}, {"d": 4}]
        assert cursor.fetchmany(2) == [{"e": 5}]


def test_fetchmany_local_size_overrides_arraysize() -> None:
    config.register_ephemeral(
        query=QUERY,
        response=SHORT_BATCH_RESPONSE,
    )
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        cursor.arraysize = 10
        assert cursor.fetchmany(2) == [{"a": 1}, {"b": 2}]
        assert cursor.fetchmany(2) == [{"c": 3}, {"d": 4}]
        assert cursor.fetchmany(2) == [{"e": 5}]


def test_fetchmany_force_pagination_size() -> None:
    config.register(query=QUERY, response=SHORT_BATCH_RESPONSE, force_pagination_size=2)
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        cursor.arraysize = 10
        assert cursor.fetchmany(5) == [{"a": 1}, {"b": 2}]
        assert cursor.fetchmany(5) == [{"c": 3}, {"d": 4}]
        assert cursor.fetchmany(5) == [{"e": 5}]


def test_fetchmany_force_pagination_size_ephemeral() -> None:
    config.register_ephemeral(
        query=QUERY, response=SHORT_BATCH_RESPONSE, force_pagination_size=2
    )
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        cursor.arraysize = 10
        assert cursor.fetchmany(5) == [{"a": 1}, {"b": 2}]
        assert cursor.fetchmany(5) == [{"c": 3}, {"d": 4}]
        assert cursor.fetchmany(5) == [{"e": 5}]


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


@set_override_response(OVERRIDE_RESPONSE)
def test_override_response_fetchone() -> None:
    with asbestos_cursor() as cursor:
        cursor.execute(INVALID_QUERY)
        assert cursor.fetchone() == OVERRIDE_RESPONSE


@set_override_response(OVERRIDE_RESPONSE)
def test_override_response_fetchall() -> None:
    with asbestos_cursor() as cursor:
        cursor.execute(INVALID_QUERY)
        assert cursor.fetchall() == OVERRIDE_RESPONSE


@set_override_response(OVERRIDE_RESPONSE)
def test_override_response_fetchmany_with_str() -> None:
    with asbestos_cursor() as cursor:
        cursor.execute(INVALID_QUERY)
        assert cursor.fetchmany() == OVERRIDE_RESPONSE


def test_override_response_fetchmany_with_iterable() -> None:
    asbestos.asbestos.OVERRIDE_RESPONSE = [{"hi": "there"}]

    with asbestos_cursor() as cursor:
        cursor.execute(INVALID_QUERY)
        assert cursor.fetchmany() == [{"hi": "there"}]

    asbestos.asbestos.OVERRIDE_RESPONSE = None


@set_override_response(LARGE_BATCH_RESPONSE)
def test_override_response_fetchmany_large_iterable() -> None:
    with asbestos_cursor() as cursor:
        cursor.execute(INVALID_QUERY)
        assert cursor.fetchmany() == LARGE_BATCH_RESPONSE


def test_fetchmany_after_other_call() -> None:
    config.register(query=QUERY, response=RESPONSE)
    config.register(query=QUERY2, response=LARGE_BATCH_RESPONSE)

    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchall() == RESPONSE

    with asbestos_cursor() as cursor:
        cursor.execute(QUERY2)
        assert cursor.fetchmany() == LARGE_BATCH_RESPONSE[: cursor.arraysize]


def test_ephemeral_context() -> None:
    config.register_ephemeral(query=QUERY, response=RESPONSE)
    assert len(config.query_map) == 1
    with EphemeralContext(config):
        with asbestos_cursor() as cursor:
            cursor.execute(QUERY)
            assert cursor.fetchall() == RESPONSE
    assert len(config.query_map) == 0


def test_unfinished_paginated_query() -> None:
    assert len(config.query_map) == 0
    config.register_ephemeral(query=QUERY, response=LARGE_BATCH_RESPONSE)
    with asbestos_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchmany(2) == [{"a": 1}, {"b": 2}]
    # the ephemeral query has not finished, so it should still be in the query map
    assert len(config.query_map) == 1


def test_unfinished_paginated_query_with_ephemeral_context() -> None:
    assert len(config.query_map) == 0
    config.register_ephemeral(query=QUERY, response=LARGE_BATCH_RESPONSE)
    with EphemeralContext(config):
        with asbestos_cursor() as cursor:
            cursor.execute(QUERY)
            assert cursor.fetchmany(2) == [{"a": 1}, {"b": 2}]
    # the ephemeral query has not finished, but thanks to the ephemeral context,
    # it should have been removed from the query map
    assert len(config.query_map) == 0


def test_ephemeral_context_with_multiple_queries() -> None:
    assert len(config.query_map) == 0
    config.register(query=QUERY, response=LARGE_BATCH_RESPONSE)
    config.register(query=QUERY2, response=SHORT_BATCH_RESPONSE)
    with EphemeralContext(config):
        with asbestos_cursor() as cursor:
            cursor.execute(QUERY)
            assert cursor.fetchmany(2) == [{"a": 1}, {"b": 2}]
            cursor.execute(QUERY2)
            assert cursor.fetchmany(2) == [{"a": 1}, {"b": 2}]
    # the ephemeral queries have not finished, but thanks to the ephemeral context,
    # they've been nuked
    assert len(config.query_map) == 0


def test_ephemeral_context_does_not_remove_uncalled_queries() -> None:
    assert len(config.query_map) == 0
    config.register(query=QUERY, response=LARGE_BATCH_RESPONSE)
    config.register(query=QUERY2, response=SHORT_BATCH_RESPONSE)
    with EphemeralContext(config):
        with asbestos_cursor() as cursor:
            cursor.execute(QUERY)
            assert cursor.fetchmany(2) == [{"a": 1}, {"b": 2}]
    # only one query was called, so only one query should have been removed
    assert len(config.query_map) == 1
