class Command:
    def __init__(self, command_type, key=None, value=None):
        self.command_type = command_type
        self.key = key
        self.value = value

    def to_dict(self):
        if (self.value == None):
            return {"command_type": self.command_type, "key": self.key}
        else:
            return {"command_type": self.command_type, "key": self.key, "value": self.value}
    
    def __str__(self):
        return f"Command({self.command_type}, {self.key}, {self.value})"



class LogEntry:
    def __init__(self, command: Command, election_term: int, index: int, is_committed : bool):
        self.command = command
        self.election_term = election_term
        self.index = index
        self.is_committed = is_committed

    def make_committed(self):
      self.is_committed = True
    
    def make_uncommitted(self):
      self.is_committed = False

    def to_dict(self):
        return {
            "command": (
                self.command.to_dict()
                if hasattr(self.command, "to_dict")
                else str(self.command)
            ),
            "election_term": self.election_term,
            "index": self.index,
            "is_committed": self.is_committed
        }
        
    def __str__(self) -> str:
        return f"LogEntry({self.command}, {self.election_term}, {self.index})"
