## Quick tip on how to run the program

### Cluster Joining
1. Running the server without joining cluster, creating a new cluster (Node 1)
```sh
python3 src/server.py [ip] [port]
python3 src/server.py localhost 8000
python3 src/server.py localhost 8001 localhost 8000
python3 src/server.py localhost 8002 localhost 8000
```

2. Joining a new cluster (Node 2)
```sh
python3 src/server.py [new_node_ip] [new_node_port] [old_node_ip] [old_node_port]
```

### Executing Single Server and Client
1. Running the server
```sh
python3 src/server.py [ip] [port]
```

2. Running the client
```sh
python3 src/client.py [ip] [port] [command] [key] [value]
python3 src/client.py localhost 8001 set a b
python3 src/client.py localhost 8001 request_log True
python3 src/client.py localhost 8001 getall True
```

### How to Test
1. Run the starting server script, make sure the server is all running
```sh
./scripts/start_servers.sh
```
> [!NOTE]
> This script will start multiple server instances for testing purposes.

2. Try to set a value into the server via the client, note bypass_local is to debug the local command of the node
```sh
python3 src/client.py localhost [any_port] set abc defghji [bypass_local]
```
> [!TIP]
> Use bypass_local=True to execute the command directly on the specified node without redirecting to the leader.

3. Check other node's storage and see if its persisted
> [!IMPORTANT]
> Ensure that the cluster is properly configured and all nodes are connected to verify the persistence of data.

### How to run dashboard
1. Just run the script and open localhost:5000
```sh
./scripts/run_flask.sh
```
