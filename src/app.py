from flask import Flask, render_template, jsonify, request
from client import find_and_execute_command, get_leader_address, get_server_proxy, ping_node, set_value, get_value, delete_value, append_value, get_all_value, get_length
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

# @app.route('/api/nodes')
# def get_nodes():
#     ip = '127.0.0.1'
#     port = 8000
#     command = 'request_log'
    
#     result = find_and_execute_command(ip, port, command, local_debug=True)
#     return jsonify(result)

@app.route('/api/set', methods=['POST']) 
def send_value():
    data = request.json 
    set_value(data['ip'], int(data['port']), data['key'], data['value'])
    return jsonify({"message": "Request received"}) 

@app.route('/api/append', methods=['POST']) 
def concat_value():
    data = request.json 
    append_value(data['ip'], int(data['port']), data['key'], data['value'])
    return jsonify({"message": "Request received"}) 

@app.route('/api/get') 
def receive_value():
    ip = request.args.get('ip')
    port = int(request.args.get('port'))
    key = request.args.get('key')
    value = get_value(ip, port, key)
    if (value):
        return jsonify({"value": value})
    else:
        return jsonify({})
    
@app.route('/api/length') 
def receive_length():
    ip = request.args.get('ip')
    port = int(request.args.get('port'))
    key = request.args.get('key')
    value = get_length(ip, port, key)
    if (value):
        return jsonify({"value": value})
    else:
        return jsonify({})
    
@app.route('/api/getall') 
def receive_all_value():
    ip = request.args.get('ip')
    port = int(request.args.get('port'))
    value = get_all_value(ip, port, local_debug=True)
    if (value):
        return jsonify({"value": value})
    else:
        return jsonify({})
    
@app.route('/api/delete', methods=['DELETE']) 
def remove_value():
    data = request.json
    ip = data.get('ip')
    port = int(data.get('port'))
    key = data.get('key')
    result = delete_value(ip, port, key)
    print("RESULT", result)
    if result:
        return jsonify({"message": "Value deleted successfully"})
    else:
        return jsonify({"error": "Value not found"}), 404


@app.route('/api/leader')
def get_leader():
    ip = '127.0.0.1'
    port = 8000
    proxy = get_server_proxy(ip, port)
    
    result = get_leader_address(proxy)
    return jsonify(result)

@app.route('/api/node_details')
def get_node_details():
    command = 'request_log'
    
    nodes_info = []
    nodes = [
        {'ip': '127.0.0.1', 'port': 8000},
        {'ip': '127.0.0.1', 'port': 8001},
        {'ip': '127.0.0.1', 'port': 8002},
        {'ip': '127.0.0.1', 'port': 8003},
        {'ip': '127.0.0.1', 'port': 8004},
        {'ip': '127.0.0.1', 'port': 8005}
    ]

    leader_addr = None
    for node in nodes:
      leader_addr_response = get_leader_address(get_server_proxy(node['ip'], node['port']))
      if (leader_addr_response):
        leader_addr = leader_addr_response['leader_address']
        # print("ADDR", leader_addr)
        break
    
    for node in nodes:
      is_online = ping_node(node['ip'], node['port'])
      status = 'Online' if is_online else 'Offline'
      node_info = find_and_execute_command(node['ip'], node['port'], command, local_debug=True)

      if (node_info):
        node_info['address'] = node
        node_info['status'] = status
      else :
        node_info = {'address': node, 'status': status, "election_term": ""}
      # leader_status returned in request log by every node
      # if (leader_addr):
      #   if (node['ip'] == leader_addr['ip'] and node['port'] == leader_addr['port']):
      #     node_info['leader_status'] = "Leader"
      #   else:
      #     node_info['leader_status'] = "Follower"
      # else:
      #   node_info['leader_status'] = "Follower"

      nodes_info.append(node_info)
      print(nodes_info)
    
    return jsonify(nodes_info)

if __name__ == '__main__':
    app.run(port=5001, debug=True)
