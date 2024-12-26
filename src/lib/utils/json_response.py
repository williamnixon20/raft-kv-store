import json


def build_json_response(success: bool, election_term: int, **kwargs):
    response = {
        "success": success,
        "election_term": election_term,
    }
    response.update(kwargs)
    return json.dumps(response)
