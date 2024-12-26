from lib.structs.log_entry import Command, LogEntry


def test_command_to_dict_with_key_and_value():
    cmd = Command("set", "test_key", "test_value")
    assert cmd.to_dict() == {
        "command_type": "set",
        "key": "test_key",
        "value": "test_value",
    }


def test_command_to_dict_with_only_key():
    cmd = Command("get", "test_key")
    assert cmd.to_dict() == {"command_type": "get", "key": "test_key"}


def test_log_entry_to_dict():
    cmd = Command("set", "test_key", "test_value")
    entry = LogEntry(cmd, 1,1)
    assert entry.to_dict() == {
        "command": {"command_type": "set", "key": "test_key", "value": "test_value"},
        "election_term": 1,
        "index" : 1,
    }


def test_log_entry_to_dict_with_partial_command():
    cmd = Command("get", "test_key")
    entry = LogEntry(cmd, 1,1)
    print(entry.to_dict())
    assert entry.to_dict() == {
        "command": {"command_type": "get", "key": "test_key"},
        "election_term": 1,
        "index" : 1,
    }
