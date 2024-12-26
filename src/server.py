from lib.structs.address import Address
from raft import RaftNode
from xmlrpc.server import SimpleXMLRPCServer
from lib.structs.kvstore import KVStore

import sys

TAG = "SERVER"


def start_serving(addr: Address, contact_node_addr: Address):
    print(f"[{TAG}] Starting Raft Server at {addr.ip}:{addr.port}")
    with SimpleXMLRPCServer((addr.ip, addr.port), allow_none=True) as server:
        server.register_introspection_functions()
        server.register_instance(RaftNode(KVStore(), addr, contact_node_addr))
        server.serve_forever()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: server.py ip port [contact_ip] [contact_port]")
        exit()

    contact_addr = None
    if len(sys.argv) == 5:
        contact_addr = Address(sys.argv[3], int(sys.argv[4]))
    server_addr = Address(sys.argv[1], int(sys.argv[2]))

    start_serving(server_addr, contact_addr)
