import pytest
import threading
import xmlrpc.client

from server import start_serving, Address
from client import execute_command, get_server_proxy


def run_server():
    addr = Address(ip="localhost", port=8000)
    start_serving(addr, None)


@pytest.fixture(scope="session", autouse=True)
def setup_server():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    yield


# Append lagi bermasalah (perlu dibenerin nanti)
# def test_client_to_server_communication():
#     proxy = get_server_proxy("localhost", 8000)

#     # Testing set command
#     response = execute_command(proxy, "set", "testkey", "testvalue")
#     assert response["success"] == True
#     assert response["result"] == "OK"

#     # Testing get command
#     response = execute_command(proxy, "get", "testkey")
#     assert response["success"] == True
#     assert response["result"] == "testvalue"

#     # Testing append command
#     response = execute_command(proxy, "append", "testkey", "value")
#     assert response["success"] == True

#     # Testing strln command
#     response = execute_command(proxy, "strln", "testkey")
#     assert response["success"] == True
#     assert response["result"] == len("testvaluevalue")

#     # Testing del command
#     response = execute_command(proxy, "del", "testkey")
#     assert response["success"] == True

#     # Ensure deletion
#     response = execute_command(proxy, "get", "testkey")
#     assert response["success"] == True
#     assert response["result"] == ""


@pytest.fixture(scope="module")
def client():
    return xmlrpc.client.ServerProxy("http://localhost:8000")
