import pytest
from lib.structs.address import Address


def test_address_initialization():
    addr = Address("127.0.0.1", 8080)
    assert addr["ip"] == "127.0.0.1"
    assert addr["port"] == 8080
    assert addr.ip == "127.0.0.1"
    assert addr.port == 8080


def test_address_string_representation():
    addr = Address("127.0.0.1", 8080)
    assert str(addr) == "127.0.0.1:8080"


def test_address_equality():
    addr1 = Address("127.0.0.1", 8080)
    addr2 = Address("127.0.0.1", 8080)
    addr3 = Address("192.168.1.1", 8080)
    addr4 = Address("127.0.0.1", 8081)

    assert addr1 == addr2
    assert addr1 != addr3
    assert addr1 != addr4
    assert addr3 != addr4


def test_address_iterability():
    addr = Address("127.0.0.1", 8080)
    ip, port = addr
    assert ip == "127.0.0.1"
    assert port == 8080
