from snowfake_db import config, snowfake_cursor
from snowfake_db.snowfake import SnowfakeCursor, SnowfakeConfig, SnowfakeResponse
from snowfake_db.exceptions import SnowfakeMissingConfig, SnowfakeDuplicateQuery

import pytest


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
    with snowfake_cursor() as cursor:
        assert isinstance(cursor, SnowfakeCursor)


def test_default_response_fetchone() -> None:
    with snowfake_cursor() as cursor:
        cursor.execute(INVALID_QUERY)
        assert cursor.fetchone() == {}


def test_default_response_fetchall() -> None:
    with snowfake_cursor() as cursor:
        cursor.execute(INVALID_QUERY)
        assert cursor.fetchall() == {}


def test_query_creation() -> None:
    config.register(query=QUERY, response=RESPONSE)
    with snowfake_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchall() == RESPONSE

    # make sure the query didn't disappear
    assert len(config.query_map) == 1


def test_ephemeral_query_creation() -> None:
    config.register_ephemeral(query=QUERY, response=RESPONSE)
    with snowfake_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchall() == RESPONSE

    # ephemeral queries are only good for one call
    assert len(config.query_map) == 0


def test_fetchone_actually_fetches_one() -> None:
    config.register(query=QUERY, response=RESPONSE)
    with snowfake_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchone() == RESPONSE[0]


def test_query_with_data() -> None:
    resp = {"different": "response"}
    config.register(query=QUERY, data=(1, 2), response=resp)
    with snowfake_cursor() as cursor:
        # Because we built the query with specific data, just a matching
        # query should return the default response because we don't have
        # the whole equation
        cursor.execute(QUERY)
        assert cursor.fetchone() == {}

        cursor.execute(QUERY, (1, 2))
        assert cursor.fetchone() == resp


def test_query_without_data() -> None:
    config.register(query=QUERY, response=RESPONSE)
    with snowfake_cursor() as cursor:
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
    with snowfake_cursor() as cursor:
        cursor.execute(QUERY, (1, 2))
        assert cursor.fetchall() == resp

        cursor.execute(QUERY, ("albuquerque",))
        assert cursor.fetchall() == RESPONSE


def test_queries_with_no_base_response() -> None:
    config.register(query=QUERY, data=(1, 2), response=RESPONSE)
    with snowfake_cursor() as cursor:
        cursor.execute(QUERY)
        assert cursor.fetchall() == {}


def test_add_duplicate_query() -> None:
    with pytest.raises(SnowfakeDuplicateQuery):
        config.register(query=QUERY, response=RESPONSE)
        config.register(query=QUERY, response=RESPONSE)


def test_add_ephemeral_and_regular_duplicate_query() -> None:
    with pytest.raises(SnowfakeDuplicateQuery):
        config.register(query=QUERY, response=RESPONSE)
        config.register_ephemeral(query=QUERY, response=RESPONSE)


def test_cursor_requires_config() -> None:
    with pytest.raises(SnowfakeMissingConfig):
        SnowfakeCursor()
