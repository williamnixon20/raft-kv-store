import pytest
from lib.structs.kvstore import KVStore


@pytest.fixture
def kvstore():
    return KVStore()


def test_set_and_get(kvstore):
    result = kvstore.set("test_key", "test_value")
    assert result == "OK"
    assert kvstore.get("test_key") == "test_value"


def test_get_nonexistent_key(kvstore):
    assert kvstore.get("nonexistent_key") == ""


def test_strln(kvstore):
    kvstore.set("test_key", "test_value")
    assert kvstore.strln("test_key") == len("test_value")
    assert kvstore.strln("nonexistent_key") == 0


def test_delete(kvstore):
    kvstore.set("test_key", "test_value")
    assert kvstore.delete("test_key") == "test_value"
    assert kvstore.delete("nonexistent_key") == ""


def test_append(kvstore):
    kvstore.set("test_key", "value")
    assert kvstore.append("test_key", "_appended") == "OK"
    assert kvstore.get("test_key") == "value_appended"

    assert kvstore.append("new_key", "start") == "OK"
    assert kvstore.get("new_key") == "start"
