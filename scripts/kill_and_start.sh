#!/bin/bash

start_port=8000
end_port=8002

echo "Killing processes listening on ports $start_port to $end_port..."

for port in $(seq $start_port $end_port)
do
    pid=$(lsof -ti tcp:$port)
    if [ ! -z "$pid" ]; then
        echo "Killing process $pid on port $port"
        kill -9 $pid
    else
        echo "No process found on port $port"
    fi
done

echo "Process termination complete."

IP="127.0.0.1"

# Set ports
PORT1=8000
PORT2=8001
PORT3=8002

sleep 1
python3 src/server.py $IP $PORT1 &
sleep 1
python3 src/server.py $IP $PORT2 $IP $PORT1 &
sleep 1
python3 src/server.py $IP $PORT3 $IP $PORT1 &

echo "Three Raft servers started on ports $PORT1, $PORT2, and $PORT3"
