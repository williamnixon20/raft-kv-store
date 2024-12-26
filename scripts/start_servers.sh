#!/bin/bash

IP="127.0.0.1"

# Set ports
PORT1=8000
PORT2=8001
PORT3=8002
PORT4=8003
PORT5=8004
PORT6=8005

sleep 1
python3 src/server.py $IP $PORT1 &
sleep 2
python3 src/server.py $IP $PORT2 $IP $PORT1 &
sleep 2
python3 src/server.py $IP $PORT3 $IP $PORT1 &
sleep 2
python3 src/server.py $IP $PORT4 $IP $PORT1 &
sleep 2
python3 src/server.py $IP $PORT5 $IP $PORT1 &
sleep 2
python3 src/server.py $IP $PORT6 $IP $PORT1 &

echo "Three Raft servers started on ports $PORT1, $PORT2, and $PORT3"
