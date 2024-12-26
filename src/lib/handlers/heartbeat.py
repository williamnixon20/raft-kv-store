from typing import TYPE_CHECKING
from lib.structs.log_entry import Command, LogEntry
from lib.structs.address import Address
from config.types import NodeType
import json
import time
from lib.utils.json_response import build_json_response

if TYPE_CHECKING:
    from raft import RaftNode


def handle_heartbeat_append_entries(json_request: str, node: "RaftNode") -> "json":
    try:
        request = json.loads(json_request)
        node.last_heartbeat = time.time()

        # Step down logic
        if (
            node.type in [NodeType.LEADER, NodeType.CANDIDATE]
            and request["election_term"] > node.election_term
        ):
            node.election_term = request["election_term"]
            node.type = NodeType.FOLLOWER
            node.cluster_leader_addr = Address(
                request["leaderId"]["ip"], request["leaderId"]["port"]
            )
            node._print_log(
                f"[HEARTBEAT] Stepdown to follower, new leader: {node.cluster_leader_addr}"
            )

        # Update cluster address list
        node.cluster_addr_list = [
            Address(addr["ip"], addr["port"])
            for addr in request.get("cluster_addr_list", [])
        ]
        # Handle log entries (append_entries part)
        if "entries" in request:
            node._print_log(f"[HEARTBEAT] Received entries from leader: {request['entries']}")

            # Log current state before appending
            node._print_log(f"[HEARTBEAT] Current log before appending: {node.log}")

            # Append or overwrite entries
            entry_index = request["prevLogIndex"]
            print("[ENTRY INDEX] Before : ", entry_index)

            # Entry index : index sekrang dari si parent 

            # Bandingin panjang log dari si node sama si parent
            print("[REQUEST]", request)

            # if (request['fromExecute']):
            #   print("HEHEHEHE", entry_index, len(node.log))


            # Handle kasus normal
            if(len(node.log) > entry_index and request['fromExecute']):
                print("TEST", entry_index, len(request['entries']), request['entries'])

                if (len(request['entries']) > 0):
                  entry = request['entries'][0]
                  print("[NEW ENTRY]", entry)
                  command_type = entry["command"]["command_type"]
                  key = entry["command"]["key"]
                  value = entry["command"].get("value")
                  new_log_entry = LogEntry(
                      command=Command(command_type=command_type, key=key, value=value),
                      election_term=entry["election_term"],
                      index=entry["index"],
                      is_committed= False,
                  )

                  # Rewrite for failed ack handling
                  print("NODE COMMIT IDX", node.commit_idx)
                  print("[NODE LENGTH]", len(node.log))
                  if ((node.commit_idx+1) == len(node.log)):
                      node.log.append(new_log_entry)
                  else :
                      node.log[node.commit_idx+1] = new_log_entry

                  node._print_log(f"[HEARBEAT] Current log after appending : {node.log}")

            elif(len(node.log) < entry_index): 
                healing_logs = request["entries"][len(node.log) : ]
                print("[HEALING LOGS]", healing_logs)
                return build_json_response(
                    success= True, 
                    election_term=node.election_term, 
                    need_healing = True, 
                    healing_index = len(node.log),
                    healing_address = node.address
                )

            # elif(len(node.log) < entry_index):
            #     healing_logs = request
            # if(entry_index < len(node.log)): 
            #     entry = request[entry_index:] if entry_index >= 0 else request[entry_index]
            #     command_type = entry["command"]["command_type"]
            #     key = entry["command"]["key"]
            #     value = entry["command"].get("value")

            #     new_log_entry = LogEntry(
            #         command=Command(command_type=command_type, key=key, value=value),
            #         election_term=entry["election_term"],
            #         index=entry["index"],
            #     )
            #     print("[HEALING LOGS]", healing_logs) 
            #     node.append_entries(healing_logs)              
            # while entry_index < len(node.log) and entry_index - request[
            #     "prevLogIndex"
            # ] - 1 < len(request["entries"]):
            #     entry_from_leader = request["entries"][
            #         entry_index - request["prevLogIndex"] - 1
            #     ]
            #     if (
            #         node.log[entry_index].election_term
            #         != entry_from_leader["election_term"]
            #     ):
            #         node.log = node.log[:entry_index]
            #         node._print_log(f"[HEARTBEAT] Truncated log due to inconsistency at index {entry_index}")
            #         break
            #     entry_index += 1
            # print("[ENTRY INDEX] After : ", entry_index)

            # for entry in request["entries"][
            #     entry_index - request["prevLogIndex"] - 1 :
            # ]:

                # command_type = entry["command"]["command_type"]
                # key = entry["command"]["key"]
                # value = entry["command"].get("value")

                # new_log_entry = LogEntry(
                #     command=Command(command_type=command_type, key=key, value=value),
                #     election_term=entry["election_term"],
                #     index=entry["index"],
                # )

            #     # Rewrite for failed ack handling
                # if ((node.commit_idx+1) == len(node.log)):
                #     node.log.append(new_log_entry)
                # else :
                #     node.log[node.commit_idx+1] = new_log_entry

            #     # node._execute_local_command(command_type,key, value)
            #     node._print_log(f"[HEARTBEAT] Appended new log entry: {new_log_entry}")

                # if request["leaderCommit"] > node.commit_idx:
                #   node.commit_idx = min(request["leaderCommit"], len(node.log) - 1)

            # Log current state after appending
            node._print_log(f"[HEARTBEAT] Current log after appending: {node.log}")

            # if request["leaderCommit"] > node.commit_idx:
            #     node.commit_idx = min(request["leaderCommit"], len(node.log) - 1)

        return build_json_response(
            success=True,
            election_term=node.election_term,
            index=request["prevLogIndex"],
            follower_addr={"ip": node.address.ip, "port": node.address.port},
        )
    except json.JSONDecodeError as e:
        node._print_log(f"Error decoding JSON request: {e}")
        return build_json_response(
            success=False, election_term=node.election_term, error="JSONDecodeError"
        )
    except KeyError as e:
        node._print_log(f"Missing key in request: {e}")
        return build_json_response(
            success=False, election_term=node.election_term, error="KeyError"
        )
    except Exception as e:
        node._print_log(f"Unexpected error: {e}")
        return build_json_response(
            success=False, election_term=node.election_term, error="UnexpectedError"
        )