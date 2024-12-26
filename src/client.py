import xmlrpc.client
import json
import sys
from time import sleep

TAG = "Client"

def get_server_proxy(ip: str, port: int):
    server_url = f"http://{ip}:{port}"
    print("Proxy SERVER URL", server_url)
    return xmlrpc.client.ServerProxy(server_url, allow_none=True)

def make_response_json(json_response):
  # Check the type of the response
  if (isinstance(json_response, str)):
      return json.loads(json_response)
  elif (isinstance(json_response, (dict, list))):
      return json_response
  else:
    print(f"Unexpected response type: {type(json_response)}")
    return None
    
def get_leader_address(proxy):
    try:
        # Get response from leader, make it JSON
        json_response = proxy.get_leader_address()
        response = make_response_json(json_response)
        if (response is None):
            raise ValueError("Unexpected response type")
        return response
    except Exception as e:
        print(f"[{TAG}] Error fetching leader address: {e}")
        return None

def execute_command(proxy, command, key=None, value=None, local_debug=False):
    print("=== Executing Command ===")
    try:
        # Requesting Log
        if command == "request_log":
            json_response = proxy.request_log(local_debug)
        # Requesting Ping to Connect
        elif command == "ping":
            json_response = proxy.ping()
        # Executing other Command
        else:
            request = {"command": command}
            # Make sure of key and value variable
            if key is not None:
                request["key"] = key
            if value is not None:
                request["value"] = value

            # Send request
            json_request = json.dumps(request)
            print("REQUEST", json_request)
            # Get Response from Proxy Execution
            json_response = proxy.execute(json_request, local_debug)
            print("RESPONSE", json_response)

        print(f"Raw JSON response: {json_response}")
        response = make_response_json(json_response)
        if response is None:
            raise ValueError("Unexpected response type")

        # Check if there is Error. If there is, do redirection in the response
        if response.get("error") == "Leader is unknown, try contacting another node":
            next_node = response.get("next_node")
            new_proxy = get_server_proxy(next_node["ip"], next_node["port"])
            print(f"Redirecting to another node at {next_node['ip']}:{next_node['port']}")
            return execute_command(new_proxy, command, key, value, local_debug)
        elif response.get("error") == "Not a leader node, try contacting: ":
            leader_addr = response.get("leader_address")
            new_proxy = get_server_proxy(leader_addr["ip"], leader_addr["port"])
            print(f"Redirecting to leader at {leader_addr['ip']}:{leader_addr['port']}")
            return execute_command(new_proxy, command, key, value, local_debug)
        elif response.get("error") == "Election is in progress, please wait...":
            print("Election is in progress. Please wait. Retrying...")
            sleep(2)
            return execute_command(proxy, command, key, value, local_debug)

        return response

    except Exception as e:
        print(f"[{TAG}] Failed to execute command: {e}.")
        return None

def ping_node(ip: str, port: int):
    proxy = get_server_proxy(ip, port)
    try:
        # Get response from node, make it JSON
        json_response = proxy.ping()
        response = make_response_json(json_response)
        if (response is None):
            raise ValueError("Unexpected response type")
        return response.get("message") == "pong"
    except Exception as e:
        print(f"[{TAG}] Error pinging node {ip}:{port} - {e}")
        return False

def find_and_execute_command(
    ip, port, command, key=None, value=None, local_debug=False, tried=0
):
    # In Local Debug, use current node as Leader
    if local_debug:
        print (f"COMMAND {str(command)} WILL GET EXECUTED ON LOCAL/NONLEADER NODE")
        server_proxy = get_server_proxy(ip, port)
        return execute_command(server_proxy, command, key, value, local_debug)

    tried_nodes = set()
    current_ip, current_port = ip, port

    # Try searching for Leader
    while (current_ip, current_port) not in tried_nodes:
        tried_nodes.add((current_ip, current_port))
        server_proxy = get_server_proxy(current_ip, current_port)

        leader_response = get_leader_address(server_proxy)
        print("Redirecting to LEADER", leader_response)

        # Redirecting Success
        if leader_response and leader_response.get("success"):
            leader_addr = leader_response["leader_address"]
            leader_proxy = get_server_proxy(leader_addr["ip"], leader_addr["port"])
            res = execute_command(leader_proxy, command, key, value, local_debug)
            if res:
                return res
            else:
                if (tried < 3):
                    sleep(2)
                    print(f"[{TAG}] Failed to contact node. Election is in progress. Retrying...")
                    return find_and_execute_command(ip, port, command, key, value, local_debug, tried+1)
                else:
                    return None
        # Leader = next node
        elif leader_response and leader_response.get("next_node"):
            next_node = leader_response["next_node"]
            current_ip, current_port = next_node["ip"], next_node["port"]
        # No Valid Leader
        else:
            print(f"[{TAG}] No valid leader address received and no next node to try.")
            break

    return None

def set_value(ip, port, key, value):
    if (key != "" and value != "" and key is not None and value is not None):
        result = find_and_execute_command(ip, port, "set", key, value, False)
        if result:
            print(result)
        else:
            print(f"[{TAG}] No valid response received.")
        return result
    else:
        print("KEY or VALUE cannot be empty")
        return None
    
def append_value(ip, port, key, value):
    if (key != "" and value != "" and key is not None and value is not None):
        result = find_and_execute_command(ip, port, "append", key, value, False)
        if result:
            print(result)
        else:
            print(f"[{TAG}] No valid response received.")
        return result
    else:
        print("KEY or VALUE cannot be empty")
        return None
    
def get_all_value(ip, port, local_debug=False):
    result = find_and_execute_command(ip, port, "getall", local_debug=local_debug)
    if result:
        print(result)
    else:
        print(f"[{TAG}] No valid response received.")
    return result

def get_value(ip, port, key):
    if (key != ""):
        result = find_and_execute_command(ip, port, "get", key, False)
        if result:
            print(result)
        else:
            print(f"[{TAG}] No valid response received.")
        return result
    else:
        print("KEY or VALUE cannot be empty")
        return None
    
def get_length(ip, port, key):
    if (key != ""):
        result = find_and_execute_command(ip, port, "strln", key, False)
        if result:
            print(result)
        else:
            print(f"[{TAG}] No valid response received.")
        return result
    else:
        print("KEY or VALUE cannot be empty")
        return None
    
def delete_value(ip, port, key):
    if (key != ""):
        result = find_and_execute_command(ip, port, "del", key, False)
        if result:
            print(result)
        else:
            print(f"[{TAG}] No valid response received.")
        return result
    else:
        print("KEY or VALUE cannot be empty")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: client.py ip port command [key] [value] [local_debug]")
        sys.exit()

    ip = sys.argv[1]
    port = int(sys.argv[2])
    command = sys.argv[3]

    if command == "request_log":
        local_debug = sys.argv[4].lower() == "true" if len(sys.argv) > 4 else False
        key = None
        value = None
    else:
        key = sys.argv[4] if len(sys.argv) > 4 else None
        value = sys.argv[5] if len(sys.argv) > 5 else None
        local_debug = sys.argv[6].lower() == "true" if len(sys.argv) > 6 else False

    result = find_and_execute_command(ip, port, command, key, value, local_debug)
    if result:
        print(result)
    else:
        print(f"[{TAG}] No valid response received.")
