import random
import socket
import time
import json
import xmlrpc.client

from concurrent.futures import ThreadPoolExecutor
from math import floor
from threading import Thread
from typing import Any, List
from lib.handlers.heartbeat import handle_heartbeat_append_entries
from lib.structs.address import Address
from config.constants import (
    HEARTBEAT_INTERVAL,
    ELECTION_TIMEOUT_MIN,
    ELECTION_TIMEOUT_MAX,
    RPC_TIMEOUT,
)
from config.types import NodeType
from lib.structs.kvstore import KVStore
from lib.structs.log_entry import Command, LogEntry
from lib.utils.json_response import build_json_response
from datetime import datetime


class RaftNode:
    def __init__(self, kvstore, addr: Address, contact_addr: Address = None):
        socket.setdefaulttimeout(RPC_TIMEOUT)
        # General info
        self.address: Address = addr
        self.type: NodeType = NodeType.FOLLOWER
        self.app: KVStore = kvstore
        self.cluster_addr_list: List[Address] = []
        self.cluster_leader_addr: Address = None

        # Raft specific info
        self.election_term: int = 0
        # Key: election Term, Value: Address
        # Perlu election term, biar dia ga bisa ganti vote dia
        self.voted_for: dict = {}
        self.log: List[LogEntry] = []
        self.commit_idx: int = -1
        self.applied_idx: int = -1
        self.next_index: dict = {}
        self.match_index: dict = {}
        self.acknowledgments: dict = {}

        # Follower
        self.last_heartbeat: float = 0
        self.election_timeout_limit = random.uniform(
            ELECTION_TIMEOUT_MIN, ELECTION_TIMEOUT_MAX
        )

        # Highest Log Index to has been applied
        # self.applied_idx = -1
        # Store results of applied commands
        # self.result_dict = {}
        # self.commit_cond = Condition()

        if contact_addr is None:
            self.cluster_addr_list.append(self.address)
            self.__initialize_as_leader()
        else:
            self.__try_to_apply_membership(contact_addr)

    # Utils
    def __send_request(
        self, request: Any, rpc_name: str, addr: Address
    ) -> "json":
        try:
            print(f"[SEND REQUEST]", request)
            # Send request
            self._print_log(
                f"Sending request {rpc_name} to {addr} at {datetime.now()}"
            )
            node = xmlrpc.client.ServerProxy(
                f"http://{addr.ip}:{addr.port}", allow_none=True
            )
            json_request = json.dumps(request, allow_nan=True)
            rpc_function = getattr(node, rpc_name)
            response = json.loads(rpc_function(json_request))
            self._print_log(
                f"Received response for {rpc_name} from {addr} at {datetime.now()}: {response}"
            )
            return response
        except Exception as e:
            self._print_log(
                f"Error while sending request {rpc_name} to {addr}: {e}"
            )
        return None

    def _print_log(self, text: str):
        print(f"[{self.address}] [{time.strftime('%H:%M:%S')}] {text}")

    def __broadcast_to_cluster(self, rpc_name: str, request: Any):
        print("[ADDRESS LIST]", self.cluster_addr_list)
        with ThreadPoolExecutor() as executor:
            futures = []
            for addr in self.cluster_addr_list:
                if addr != self.address:
                    futures.append(
                        executor.submit(self.__send_request, request, rpc_name, addr)
                    )
            responses = [future.result() for future in futures] 
        return responses
    ################

    def __initialize_as_leader(self):
        self._print_log("Initialize as leader node...")
        self.cluster_leader_addr = self.address
        self.type = NodeType.LEADER
        self.next_index = {addr: len(self.log) for addr in self.cluster_addr_list}
        self.match_index = {addr: -1 for addr in self.cluster_addr_list}
        self.acknowledgments = {i: set() for i in range(len(self.log))}

        request = {
            "cluster_leader_addr": self.address,
            "election_term": self.election_term,
        }
        self.__broadcast_to_cluster("notify_leader", request)

        self.heartbeat_thread = Thread(target=self.__start_heartbeat)
        self.heartbeat_thread.start()

    def __start_heartbeat(self):
        while self.type == NodeType.LEADER:
            self._print_log("[HEARTBEAT] Sending heartbeat...")

            # Collect entries to append
            prevLogIndex = self.commit_idx
            prevLogTerm = self.log[prevLogIndex].election_term if self.log else 0
            entries_to_send = [self.log[(len(self.log) -1 )].to_dict()] if len(self.log) > 0 else []
            request = {
                "election_term": self.election_term,
                "leaderId": self.address,
                "prevLogIndex": prevLogIndex,
                "prevLogTerm": prevLogTerm,
                "leaderCommit": self.commit_idx,
                "cluster_addr_list": self.cluster_addr_list,
                "entries": entries_to_send,
                "fromExecute" : False,
            }

            results = self.__broadcast_to_cluster("heartbeat", request)
            for i, result in enumerate(results):
                print("[RESULT]", result)
                if result and 'need_healing' in result and result['need_healing']:
                    healing_index = result["healing_index"]
                    entries_to_send = [entry.to_dict() for entry in self.log[healing_index:] if entry is not None]
                    healing_request = { 
                        "entries": entries_to_send
                    }
                    address = Address(result["healing_address"]["ip"], result["healing_address"]["port"])
                    print("[HEALING ADDRESS]", address)
                    print(f"[HEALING REQUEST]", healing_request)
                    self.__send_request(healing_request, "healing_logs", address)
            # print("[RESULT]", results)
            time.sleep(HEARTBEAT_INTERVAL)

    ############# MEMBERSHIP #########

    def __try_to_apply_membership(self, contact_addr: Address):
        redirected_addr = contact_addr
        response = {
            "status": "redirected",
            "address": {
                "ip": contact_addr.ip,
                "port": contact_addr.port,
            },
        }

        while response["status"] != "success":
            redirected_addr = Address(
                response["address"]["ip"], response["address"]["port"]
            )
            response = self.__send_request(
                self.address, "apply_membership", redirected_addr
            )
            if not response:
                self._print_log(f"[MEMBERSHIP] Error, cannot contact {redirected_addr}")
                exit(1)
            if response["status"] == "error":
                self._print_log(
                    f"[MEMBERSHIP] Error, are you sure address is a leader? This is legit leader "
                    + response["message"]
                )
                exit(1)

        self._print_log(f"[MEMBERSHIP] Membership applied to leader {contact_addr}")
        self.cluster_addr_list = [
            Address(addr["ip"], addr["port"]) for addr in response["cluster_addr_list"]
        ]
        self.cluster_leader_addr = redirected_addr
        
        self.election_timeout_limit = random.uniform(
            ELECTION_TIMEOUT_MIN, ELECTION_TIMEOUT_MAX
        )
        
        self.election_term = response["election_term"]
        
        self.last_heartbeat = time.time()
        self.timeout_thread = Thread(target=self.__start_watch_timeout)
        self.timeout_thread.start()

    def __start_watch_timeout(self):
        while self.type != NodeType.LEADER:
            self._print_log(f"[HEARTBEAT] Watching timeout...")
            if time.time() - self.last_heartbeat > self.election_timeout_limit:
                self._print_log(f"[TIMEOUT] Election timeout {time.time() - self.last_heartbeat} > {self.election_timeout_limit}, starting new election...")
                self.__start_election()
                break
            time.sleep(HEARTBEAT_INTERVAL)

    def apply_membership(self, json_request: str):
        ###
        # syarat: leader
        # 1. Kalau udah registered, langsung return sucess
        # 2. Kalau belom registered, registerin dulu
        ###
        print("APPLY MEMBERSHIP")
        if self.type != NodeType.LEADER:
            response = {
                "status": "error",
                "message": "Not a leader node, try contacting: "
                + str(self.cluster_leader_addr),
            }
            return json.dumps(response)
        request = json.loads(json_request)
        member_address = Address(request["ip"], request["port"])

        # LOG HANDLE DI HEARTBEAT BUAT NODE YG BARU NYALA
        response = {
            "status": "success",
            "address": {
                "ip": self.address.ip,
                "port": self.address.port,
            },
            "cluster_addr_list": self.cluster_addr_list,
            "election_term": self.election_term
        }

        for addr in self.cluster_addr_list:
            if addr == member_address:
                return json.dumps(response)

        self.cluster_addr_list.append(Address(member_address.ip, member_address.port))
        response["cluster_addr_list"] = self.cluster_addr_list
        self._print_log(f"[MEMBERSHIP] New member added : {member_address}")
        return json.dumps(response)

    ###########
    ## LEADERSHIP

    def notify_leader(self, json_request: str):
        request = json.loads(json_request)
        new_election_term = request["election_term"]

        if self.election_term < new_election_term:
            self.election_term = new_election_term
            self.type = NodeType.FOLLOWER
            self.cluster_leader_addr = Address(
                request["cluster_leader_addr"]["ip"],
                request["cluster_leader_addr"]["port"],
            )
            self.voted_for[new_election_term] = self.cluster_leader_addr
            self._print_log(
                f"[LEADERSHIP] New leader announced: {self.cluster_leader_addr}"
            )
        return json.dumps({"status": "ack"})

    def __start_election(self):
        self.type = NodeType.CANDIDATE
        self.election_term += 1
        self.voted_for[self.election_term] = self.address
        vote_count = 1

        with ThreadPoolExecutor() as executor:
            futures = []
            body = {
                "election_term": self.election_term, 
                "candidate_addr": self.address,
                "last_log_index": len(self.log) - 1,
                "last_log_term": self.log[-1].election_term if len(self.log) > 0 else 0
                }

            for addr in self.cluster_addr_list:
                if addr != self.address:
                    future = executor.submit(
                        self.__send_request, body, "request_vote", addr
                    )
                    futures.append(future)

            results = [future.result() for future in futures]

            for result in results:
                if result:
                    print("[ELECTION] VOTING RESULT", result)
                    if result.get("curr_election_term") > self.election_term:
                        self.election_term = result.get("curr_election_term")
                        self.cluster_leader_addr = Address(
                            result.get("curr_leader")["ip"],
                            result.get("curr_leader")["port"],
                        )
                        self.type = NodeType.FOLLOWER
                        self._print_log(
                            f"[ELECTION] Stepdown to follower, waiting for heartbeat from new leader"
                        )
                        return
                    if result.get("voted_for") == self.address:
                        vote_count += 1

        if vote_count >= (floor(len(self.cluster_addr_list) / 2) + 1):
            self._print_log(f"[ELECTION] Elected as leader")
            self.__initialize_as_leader()
        else:
            self._print_log(f"[ELECTION] Failed to be elected. Will restart election")
            self.last_heartbeat = time.time()
            self.timeout_thread = Thread(target=self.__start_watch_timeout)
            self.timeout_thread.start()
            self.election_timeout_limit = random.uniform(
                ELECTION_TIMEOUT_MIN, ELECTION_TIMEOUT_MAX
            )

    def request_vote(self, json_request: str) -> "json":
        request = json.loads(json_request)
        election_term = request["election_term"]
        candidate_addr = Address(
            request["candidate_addr"]["ip"], request["candidate_addr"]["port"]
        )
        last_term = request["last_log_term"]
        last_index = request["last_log_index"]

        body = {
            "curr_election_term": self.election_term,
            "curr_leader": self.cluster_leader_addr,
            "election_term": election_term,
            "voted_for": None
        }
        
        ## If already voted, then return who I voted for.
        if election_term in self.voted_for:
            body["voted_for"] = self.voted_for[election_term]
            self.last_heartbeat = time.time()
        else:
            # Not yet voted, Check if this one is worthy of my vote
            my_term = self.log[-1].election_term if len(self.log) > 0 else 0
            my_index = len(self.log) - 1
            if last_term == my_term:
                if last_index >= my_index:
                    body["voted_for"] = candidate_addr
                    self.voted_for[election_term] = candidate_addr
                    self.last_heartbeat = time.time()
            else:
                if last_term > my_term:
                    body["voted_for"] = candidate_addr
                    self.voted_for[election_term] = candidate_addr
                    self.last_heartbeat = time.time()


        self._print_log(f"[VOTE] Term {election_term}, Voting for {body['voted_for']}")

        return json.dumps(body)

    # Inter-node RPCs
    def heartbeat(self, json_request):
        print("RECEIVED HEARTBEAT")
        return handle_heartbeat_append_entries(json_request, self)

    # Log Replication
    def append_entries(self, json_request: str) -> "json":
        return self.heartbeat(json_request)

    def __apply_committed_log(self, log_index: int):   
        log_entry = self.log[log_index]
        log_entry.make_committed()
        command = log_entry.command
        
        if log_index <= self.applied_idx:
            # Need to still exec if not modify state
            match command.command_type:
                case "get":
                    result = self.app.get(command.key)
                case "strln":
                    result = self.app.strln(command.key)
                case "getall":
                    result = self.app.get_all()
                case _:
                    result = None
            return result
        
        self._print_log(f"Applying committed log entry {log_index}: {command.to_dict()}")
        
        match command.command_type:
            case "get":
                result = self.app.get(command.key)
            case "set":
                result = self.app.set(command.key, command.value)
            case "del":
                result = self.app.delete(command.key)
            case "append":
                result = self.app.append(command.key, command.value)
            case "strln":
                result = self.app.strln(command.key)
            case "getall":
                result = self.app.get_all()
            case _:
                result = None
        self._print_log(f"Result of applying log entry {log_index}: {result}")
        # Update the applied_index with the new log index
        self.applied_idx = log_index
        # Broadcast the commit to all followers
        return result

    def __broadcast_commit(self, log_index: int):
        # Commit the last log
        self.log[-1].make_committed()
        request = {
            "election_term": self.election_term,
            "leaderCommit": log_index,
        }
        self.__broadcast_to_cluster("commit_entries", request)

    def commit_entries(self, json_request: str) -> "json":
        try:
            request = json.loads(json_request)
            print(f"[COMMIT ENTRIES REQ]", request)
            if request["leaderCommit"] > self.commit_idx:
                print("INI SELF COMMIT IDX", self.commit_idx)
                new_commit_idx = min(request["leaderCommit"], len(self.log) - 1)
                print("INI NEW COMMIT IDX", new_commit_idx)
                for i in range(self.commit_idx + 1, new_commit_idx + 1):
                    self.__apply_committed_log(i)
                self.commit_idx = new_commit_idx

                # Commit the last log
                # print(f"INI SELF LOG", self.log)
                # self.log[-1].make_committed()
            return build_json_response(success=True, election_term=self.election_term)
        except json.JSONDecodeError as e:
            self._print_log(f"Error decoding JSON request: {e}")
            return build_json_response(
                success=False, election_term=self.election_term, error="JSONDecodeError"
            )
        except KeyError as e:
            self._print_log(f"Missing key in request: {e}")
            return build_json_response(
                success=False, election_term=self.election_term, error="KeyError"
            )
        except Exception as e:
            self._print_log(f"Unexpected error: {e}")
            return build_json_response(
                success=False, election_term=self.election_term, error="UnexpectedError"
            )

    # Client RPC
    # Only Leader Node can Exec
    def execute(self, json_request: str, local_debug: bool = False) -> str:
        try:
            self._print_log(f"Received execute request: {json_request}")
            request = json.loads(json_request)
            command = request["command"]
            key = request.get("key")
            value = request.get("value")

            # Case of Local Debug
            if local_debug:
                self._print_log(
                    f"Executing command locally at {self.address.ip}:{self.address.port}"
                )
                return self._execute_local_command(command, key, value)

            # Redirect request if the node is not the leader
            if self.type != NodeType.LEADER:
                if self.cluster_leader_addr is None:
                    return build_json_response(
                        success=False,
                        election_term=self.election_term,
                        error="Leader is unknown, cannot execute command",
                    )
                else:
                    self._print_log(
                        f"Leader is at {self.cluster_leader_addr.ip}:{self.cluster_leader_addr.port}, cannot execute command"
                    )
                    return

            # Execute if this is the leader node
            self._print_log(
                f"Executing command {command} with key: {key} and value: {value} from {self.address} as leader"
            )

            log_index = self.commit_idx + 1 
            log_entry = LogEntry(
                command=Command(command_type=command, key=key, value=value),
                election_term=self.election_term,
                index=log_index,
                is_committed =False
            )

            # Rewrite for failed ack handling
            if ((self.commit_idx+1) == len(self.log)): 
                self.log.append(log_entry)
            else :
                self.log[self.commit_idx+1] = log_entry
            self._print_log(f"New log entry index: {log_index}")

            # Track acknowledgments for the new log entry
            self.acknowledgments[log_index] = set()

            prevLogIndex = log_index - 1
            prevLogTerm = (
                self.log[prevLogIndex].election_term if prevLogIndex >= 0 else 0
            )

            entries_to_send = [log_entry.to_dict()]
            print("[EXECUTE]", entries_to_send)
            responses = self.__broadcast_to_cluster(
                "append_entries",
                {
                    "election_term": self.election_term,
                    "leaderId": self.address,
                    "prevLogIndex": prevLogIndex,
                    "prevLogTerm": prevLogTerm,
                    "entries": entries_to_send,
                    "leaderCommit": self.commit_idx,
                    "testing" :"execute",
                    "fromExecute" : True,
                },
            )
            
            num_replies = 1
            result = None
            # print("[RESPONSES]",responses)
            for response in responses:
                if response is not None and response.get("success"):
                    num_replies += 1
            if num_replies >= (floor(len(self.cluster_addr_list) / 2) + 1):
                self.commit_idx = log_index
                result = self.__apply_committed_log(log_index)
                self._print_log(
                    f"Log entry {log_index} committed. Commit index is now {self.commit_idx}"
                )
                self.__broadcast_commit(log_index)
                return build_json_response(
                    success=True, election_term=self.election_term, result=result
                )
            # Case if does not get majority acknowledgement
            return build_json_response(
                success=False,
                election_term=self.election_term,
                error="Failed to get majority acknowledgement.")

        except Exception as e:
            self._print_log(f"Unexpected error during execute: {e}")
            return build_json_response(
                success=False, election_term=self.election_term, error=str(e)
            )


    def get_leader_address(self):
        print("GETTING LEADER ADDR")
        if self.cluster_leader_addr:
            return build_json_response(
                success=True,
                election_term=self.election_term,
                leader_address=self.cluster_leader_addr.to_dict(),
            )
        else:
            next_node = self.get_next_node()
            return build_json_response(
                success=False,
                error="Leader is unknown, try contacting another node",
                election_term=self.election_term,
                next_node=next_node.to_dict(),
            )

    def get_next_node(self):
        current_index = self.cluster_addr_list.index(self.address)
        next_index = (current_index + 1) % len(self.cluster_addr_list)
        return self.cluster_addr_list[next_index]

    def get_leader_address_handler(self):
        return self.get_leader_address()

    def _execute_local_command(self, command, key, value):
        try:
            match command:
                case "get":
                    result = self.app.get(key)
                    return build_json_response(
                        success=True, election_term=self.election_term, result=result
                    )
                case "set":
                    result = self.app.set(key, value)
                    return build_json_response(
                        success=True, election_term=self.election_term, result=result
                    )
                case "del":
                    result = self.app.delete(key)
                    return build_json_response(
                        success=True, election_term=self.election_term, result=result
                    )
                case "append":
                    result = self.app.append(key, value)
                    return build_json_response(
                        success=True, election_term=self.election_term, result=result
                    )
                case "strln":
                    result = self.app.strln(key)
                    return build_json_response(
                        success=True, election_term=self.election_term, result=result
                    )
                case "getall":
                    result = self.app.get_all()
                    return build_json_response(
                        success=True, election_term=self.election_term, result=result
                    )
                case _:
                    return build_json_response(
                        success=False,
                        election_term=self.election_term,
                        error="Invalid command",
                    )
        except Exception as e:
            self._print_log(f"Unexpected error during local execute: {e}")
            return build_json_response(
                success=False, election_term=self.election_term, error=str(e)
            )
        
    def ping(self):
        return build_json_response(success=True, election_term=self.election_term, message="pong")

    def request_log(self, local_debug: bool = False) -> "json":

        def serialize_log():
          # +1 because it stopped until commit_idx, not before commit_idx
          if (self.log and hasattr(self.log[0], "to_dict")):
            returned_log = []
            # return [entry.to_dict() for entry in self.log[:self.commit_idx+1]]
            for entry in self.log:
              returned_log.append(entry.to_dict())
            return [entry.to_dict() for entry in self.log]
          else:
            return self.log

        # For debugging purposes
        if local_debug:
            self._print_log(
                f"Requesting log locally at {self.address.ip}:{self.address.port}"
            )

            # Only get entries that are committed
            serialized_log = serialize_log()
            leader_status = "Leader" if self.type == NodeType.LEADER else ("Follower" if self.type == NodeType.FOLLOWER else "Candidate")
            return build_json_response(
                success=True, election_term=self.election_term, leader_status=leader_status,local_log=serialized_log
            )

        # Redirect request if the node is not the leader
        if self.type != NodeType.LEADER:
            if self.cluster_leader_addr is None:
                serialized_log = serialize_log()
                return build_json_response(
                    success=False,
                    election_term=self.election_term,
                    error="Leader is unknown, cannot execute command",
                    self_log=serialized_log,
                )
            else:
                self._print_log(
                    f"Redirecting command to leader at {self.cluster_leader_addr.ip}:{self.cluster_leader_addr.port}"
                )
                return self.__send_request(
                    request="", rpc_name="request_log", addr=self.cluster_leader_addr
                )

        # If this node is the leader, then send out the log
        self._print_log(f"Executing 'request_log' from {self.address} as leader")
        serialized_log = serialize_log()
        return build_json_response(
            success=True, election_term=self.election_term, log=serialized_log
        )
    def healing_logs(self, json_request : str): 
        # request = json.loads(json_request)
        request = json.loads(json_request.replace("'", '"'))
        response = {
            "status" : "success",
            "message" : "Success adding healing logs"
        }
        entries = request["entries"]
        # print(f"[REQUEST ENTRIES]", entries)
        for entry in entries : 
            print("[ENTRY]", entry)
            command_type = entry["command"]["command_type"]
            key = entry["command"]["key"]
            value = entry["command"].get("value")
            is_commited = entry["is_committed"]
            if(is_commited):
                self.commit_idx += 1
            new_command = Command(command_type=command_type, key=key, value=value)
            new_log_entry = LogEntry(
                command=new_command,
                election_term=entry["election_term"],
                index=entry["index"],
                is_committed=is_commited,
            )        
            self.log.append(new_log_entry)
            self._execute_local_command(command_type, key, value)
            # print("[NEW LOG]", self.log)
        # print("[HEALING REQUEST : ]", request["entries"])
        print("SELF COMMTI IDX", self.commit_idx)
        json.dumps(response)