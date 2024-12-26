#!/bin/bash

start_port=8000
end_port=8005

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
