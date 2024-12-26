# types.py
from enum import Enum


class NodeType(Enum):
    LEADER = 1
    CANDIDATE = 2
    FOLLOWER = 3
