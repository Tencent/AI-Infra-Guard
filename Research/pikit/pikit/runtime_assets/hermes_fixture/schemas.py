def _source(name, description, field):
    return {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": {field: {"type": "string"}}, "required": [field]},
    }

READ_DOCUMENT = _source("pikit_read_document", "Read an untrusted test document by reference.", "ref")
FETCH_URL = _source("pikit_fetch_url", "Fetch an untrusted test web page by URL.", "url")
READ_EMAIL = _source("pikit_read_email", "Read an untrusted test email by identifier.", "id")
SEARCH_KNOWLEDGE = _source("pikit_search_knowledge", "Search untrusted test knowledge-base content.", "query")
LOAD_SKILL = _source("pikit_load_skill", "Load an untrusted test agent skill by name.", "name")
RECORD_SINK = {
    "name": "pikit_record_sink", "description": "Record a requested external action without performing it.",
    "parameters": {"type": "object", "properties": {"action": {"type": "string"}, "target": {"type": "string"}, "content": {"type": "string"}}, "required": ["action", "target", "content"]},
}
