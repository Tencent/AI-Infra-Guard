"""Register safe test fixture tools with Hermes."""
from . import schemas, tools

def register(ctx):
    entries = [
        ("pikit_read_document", schemas.READ_DOCUMENT, tools.read_document),
        ("pikit_fetch_url", schemas.FETCH_URL, tools.fetch_url),
        ("pikit_read_email", schemas.READ_EMAIL, tools.read_email),
        ("pikit_search_knowledge", schemas.SEARCH_KNOWLEDGE, tools.search_knowledge),
        ("pikit_load_skill", schemas.LOAD_SKILL, tools.load_skill),
        ("pikit_record_sink", schemas.RECORD_SINK, tools.record_sink),
    ]
    for name, schema, handler in entries:
        ctx.register_tool(name=name, toolset="pikit_fixture", schema=schema, handler=handler)
