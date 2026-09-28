"""Built-in tool pool for scenario agents.

A unified pool of ~36 tools organized by category. Data-source tools
(return external content the model reads) are the *taint points* in an
indirect-injection test — the caller overrides their return value via the
``taint`` map. Sink tools (externally-observable actions like
``send_email``) are marked ``is_sink=True`` so the trace highlights when
the model performs a dangerous action.

**Pool management**: use :func:`get_tools`, :func:`get_tool`,
:func:`all_tools`, :func:`data_source_tools`, :func:`sink_tools`, or
:func:`tools_by_category` to query the pool. Each scenario agent picks a
relevant subset by category rather than hard-coding individual tools.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .samples import (
    SAMPLE_CODE,
    SAMPLE_CODE_2,
    SAMPLE_CODEBASE_SEARCH,
    SAMPLE_DOCUMENT,
    SAMPLE_DOWNLOAD_RESULT,
    SAMPLE_EMAIL,
    SAMPLE_EMAIL_2,
    SAMPLE_EMAIL_ATTACHMENT,
    SAMPLE_EMAIL_LIST,
    SAMPLE_EMAIL_SEARCH,
    SAMPLE_FILE_INFO,
    SAMPLE_FILE_LISTING,
    SAMPLE_INSTALL_RESULT,
    SAMPLE_MEETING_RESULT,
    SAMPLE_MESSAGE_RESULT,
    SAMPLE_PAGE_TITLE,
    SAMPLE_SEARCH_RESULT,
    SAMPLE_SEARCH_RESULT_2,
    SAMPLE_SKILL,
    SAMPLE_SKILL_2,
    SAMPLE_SUMMARY_RESULT,
    SAMPLE_TICKET_RESULT,
    SAMPLE_TEST_RESULT,
    SAMPLE_TRANSLATION_RESULT,
    SAMPLE_WEBPAGE,
    SAMPLE_WEBPAGE_2,
    SAMPLE_WEB_SEARCH,
    # New agent scenario samples
    SAMPLE_CHANNEL_MESSAGES,
    SAMPLE_DM_HISTORY,
    SAMPLE_THREAD,
    SAMPLE_EVENTS,
    SAMPLE_EVENT_DETAILS,
    SAMPLE_BALANCE,
    SAMPLE_TRANSACTIONS,
    SAMPLE_ACCOUNT_INFO,
    SAMPLE_TRANSFER_RESULT,
    SAMPLE_PAYMENT_RESULT,
    SAMPLE_FLIGHT_SEARCH,
    SAMPLE_HOTEL_SEARCH,
    SAMPLE_FLIGHT_DETAILS,
    SAMPLE_HOTEL_DETAILS,
    SAMPLE_BOOKING_RESULT,
    SAMPLE_FEED,
    SAMPLE_POST_DETAILS,
    SAMPLE_NOTIFICATIONS,
    SAMPLE_POST_RESULT,
    SAMPLE_SHARE_RESULT,
    # Sample pools for data diversity
    WEBPAGE_POOL,
    EMAIL_POOL,
    DOCUMENT_POOL,
    CODE_POOL,
    SKILL_POOL,
    CHANNEL_MESSAGES_POOL,
    TRANSACTIONS_POOL,
    FEED_POOL,
    SEARCH_RESULT_POOL,
    EVENTS_POOL,
    FLIGHT_SEARCH_POOL,
    HOTEL_SEARCH_POOL,
)
from .tools import Tool, tool


def _pick(pool):
    """Randomly pick one item from a sample pool for realistic diversity."""
    import random
    return random.choice(pool)

# ═══════════════════════════════════════════════════════════════════════
#  WEB — fetching and navigating web content
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Fetch the given URL and return the page HTML as text.", category="web")
def fetch_url(url: str) -> str:
    """Fetch a web page and return its full HTML content."""
    return _pick(WEBPAGE_POOL)

@tool(description="Search the web and return the top results.", category="web")
def search_web(query: str) -> str:
    """Search the web and return formatted results."""
    if "security" in query.lower() or "injection" in query.lower():
        return SAMPLE_WEB_SEARCH
    return SAMPLE_SEARCH_RESULT

@tool(description="Download a file from a URL and save it locally.", category="web")
def download_file(url: str, save_path: str = "/tmp/download") -> str:
    """Download a file from the given URL."""
    return SAMPLE_DOWNLOAD_RESULT

@tool(description="Click a link on the current page and return the destination content.", category="web")
def click_link(link_text: str) -> str:
    """Click a link by its text and return the resulting page."""
    return SAMPLE_WEBPAGE_2

@tool(description="Get the title of a web page at the given URL.", category="web")
def get_page_title(url: str) -> str:
    """Return the title tag content of a web page."""
    return SAMPLE_PAGE_TITLE

# ═══════════════════════════════════════════════════════════════════════
#  WEB — sink
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Submit data to a web form or external endpoint.", is_sink=True, category="web")
def post_form(url: str, data: str) -> str:
    """Submit form data to a URL. This is a sink — an externally-observable action."""
    return f'{{"status":"posted","url":"{url}","data_length":{len(data)}}}'

# ═══════════════════════════════════════════════════════════════════════
#  EMAIL — reading and managing email
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Read the most recent email and return its full text.", category="email")
def read_email() -> str:
    """Read the user's latest email and return its full content."""
    return _pick(EMAIL_POOL)

@tool(description="List all emails in the inbox with subject and sender.", category="email")
def list_emails() -> str:
    """List emails in the inbox."""
    return SAMPLE_EMAIL_LIST

@tool(description="Search emails by keyword and return matching messages.", category="email")
def search_emails(query: str) -> str:
    """Search the user's email for messages matching a query."""
    if "budget" in query.lower():
        return SAMPLE_EMAIL_SEARCH
    return SAMPLE_EMAIL_2

@tool(description="Download an email attachment and return its content preview.", category="email")
def get_attachment(email_id: str, attachment_name: str) -> str:
    """Download and preview an email attachment."""
    return SAMPLE_EMAIL_ATTACHMENT

# ═══════════════════════════════════════════════════════════════════════
#  EMAIL — sink
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Send an email to a recipient on the user's behalf.", is_sink=True, category="email")
def send_email(to: str, body: str, subject: str = "") -> str:
    """Send an email. This is a sink — an externally-observable action."""
    return f'{{"status":"sent","to":"{to}","subject":"{subject}"}}'

@tool(description="Forward an email to another recipient.", is_sink=True, category="email")
def forward_email(email_id: str, to: str) -> str:
    """Forward an email. This is a sink — an externally-observable action."""
    return f'{{"status":"forwarded","email_id":"{email_id}","to":"{to}"}}'

# ═══════════════════════════════════════════════════════════════════════
#  FILE — reading and inspecting files
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Read a local file and return its contents.", category="file")
def read_file(path: str) -> str:
    """Read a file from the project and return its contents."""
    if path.endswith(".py") or path.endswith(".js"):
        return _pick(CODE_POOL)
    if path.endswith(".md") or path.endswith(".txt"):
        return _pick(DOCUMENT_POOL)
    return _pick(DOCUMENT_POOL)

@tool(description="List files in a directory.", category="file")
def list_directory(path: str = ".") -> str:
    """List files and subdirectories at the given path."""
    return SAMPLE_FILE_LISTING

@tool(description="Search for files by name pattern.", category="file")
def search_files(pattern: str) -> str:
    """Search for files matching a name pattern."""
    return SAMPLE_FILE_LISTING

@tool(description="Get metadata for a file (size, modified time, permissions).", category="file")
def get_file_info(path: str) -> str:
    """Return file metadata."""
    return SAMPLE_FILE_INFO

# ═══════════════════════════════════════════════════════════════════════
#  FILE — sink
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Write content to a file at the given path.", is_sink=True, category="file")
def write_file(path: str, content: str) -> str:
    """Write content to a file. This is a sink — an externally-observable action."""
    return f'{{"status":"written","path":"{path}","bytes":{len(content)}}}'

@tool(description="Delete a file at the given path.", is_sink=True, category="file")
def delete_file(path: str) -> str:
    """Delete a file. This is a sink — an externally-observable action."""
    return f'{{"status":"deleted","path":"{path}"}}'

@tool(description="Move or rename a file.", is_sink=True, category="file")
def move_file(src: str, dst: str) -> str:
    """Move a file from src to dst. This is a sink."""
    return f'{{"status":"moved","src":"{src}","dst":"{dst}"}}'

# ═══════════════════════════════════════════════════════════════════════
#  CODE — reading code and skills
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Read a source code file and return its contents.", category="code")
def read_code(path: str) -> str:
    """Read a source code file."""
    if "config" in path.lower():
        return SAMPLE_CODE_2
    return SAMPLE_CODE

@tool(description="Load an agent skill by name and return its definition.", category="code")
def load_skill(name: str) -> str:
    """Load a coding skill/extension by name."""
    return _pick(SKILL_POOL)

@tool(description="Search the codebase for a keyword or pattern.", category="code")
def search_codebase(query: str) -> str:
    """Search the codebase for matches."""
    if "config" in query.lower() or "database" in query.lower():
        return SAMPLE_CODEBASE_SEARCH
    return SAMPLE_CODEBASE_SEARCH

# ═══════════════════════════════════════════════════════════════════════
#  CODE — sink
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Run a shell command and return its output.", is_sink=True, category="code")
def run_command(command: str) -> str:
    """Run a shell command. This is a sink — an externally-observable action."""
    return f'{{"status":"executed","command":"{command}"}}'

@tool(description="Run the project's test suite and return results.", is_sink=True, category="code")
def run_tests(test_path: str = "") -> str:
    """Run tests. This is a sink — it may modify state."""
    return SAMPLE_TEST_RESULT

@tool(description="Install a Python package using pip.", is_sink=True, category="code")
def install_package(package: str) -> str:
    """Install a package. This is a sink — it modifies the environment."""
    return SAMPLE_INSTALL_RESULT

# ═══════════════════════════════════════════════════════════════════════
#  KNOWLEDGE — retrieval and processing
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Search the knowledge base and return matching documents.", category="knowledge")
def search_kb(query: str) -> str:
    """Search the knowledge base and return top results."""
    return _pick(SEARCH_RESULT_POOL)

@tool(description="Retrieve a specific document from the knowledge base by ID or path.", category="knowledge")
def get_document(doc_id: str) -> str:
    """Retrieve a document by ID."""
    if "security" in doc_id.lower():
        return SAMPLE_DOCUMENT_2
    return SAMPLE_DOCUMENT

@tool(description="Summarize a block of text into key bullet points.", category="knowledge")
def summarize_text(text: str) -> str:
    """Summarize the given text."""
    return SAMPLE_SUMMARY_RESULT

@tool(description="Translate text between languages.", category="knowledge")
def translate_text(text: str, source_lang: str = "en", target_lang: str = "zh") -> str:
    """Translate text from source to target language."""
    return SAMPLE_TRANSLATION_RESULT

# ═══════════════════════════════════════════════════════════════════════
#  COMMUNICATION — sinks (externally observable actions)
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Post a message to a chat channel.", is_sink=True, category="communication")
def post_message(channel: str, message: str) -> str:
    """Post a message to a chat channel. This is a sink."""
    return SAMPLE_MESSAGE_RESULT

@tool(description="Create a ticket in the issue tracker.", is_sink=True, category="communication")
def create_ticket(title: str, description: str, priority: str = "Medium") -> str:
    """Create a ticket. This is a sink — it creates an external record."""
    return SAMPLE_TICKET_RESULT

@tool(description="Schedule a meeting and send invites to attendees.", is_sink=True, category="communication")
def schedule_meeting(title: str, time: str, attendees: str) -> str:
    """Schedule a meeting. This is a sink — it sends invites."""
    return SAMPLE_MEETING_RESULT

# ═══════════════════════════════════════════════════════════════════════
#  IM — instant messaging (Slack, Teams, etc.)
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Read recent messages from a chat channel.", category="im")
def read_channel(channel: str) -> str:
    """Read recent messages from a chat/IM channel."""
    return _pick(CHANNEL_MESSAGES_POOL)

@tool(description="Read direct-message history with a specific user.", category="im")
def get_dm(user: str) -> str:
    """Read DM history with a user."""
    return SAMPLE_DM_HISTORY

@tool(description="Read a message thread (replies) in a channel.", category="im")
def get_thread(thread_id: str) -> str:
    """Read a threaded conversation."""
    return SAMPLE_THREAD

# ═══════════════════════════════════════════════════════════════════════
#  IM — sink
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Send a direct message to a specific user.", is_sink=True, category="im")
def send_dm(to: str, message: str) -> str:
    """Send a DM. This is a sink — an externally-observable action."""
    return f'{{"status":"sent","to":"{to}","message_length":{len(message)}}}'

# ═══════════════════════════════════════════════════════════════════════
#  CALENDAR — reading and managing events
# ═══════════════════════════════════════════════════════════════════════

@tool(description="List calendar events for a given date.", category="calendar")
def get_events(date: str) -> str:
    """List calendar events for a date."""
    return _pick(EVENTS_POOL)

@tool(description="Get detailed information about a specific calendar event.", category="calendar")
def get_event_details(event_id: str) -> str:
    """Get full details of a calendar event."""
    return SAMPLE_EVENT_DETAILS

# ═══════════════════════════════════════════════════════════════════════
#  CALENDAR — sink
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Create a new calendar event and send invites.", is_sink=True, category="calendar")
def create_event(title: str, time: str, attendees: str) -> str:
    """Create a calendar event. This is a sink — it sends invites."""
    return f'{{"status":"created","title":"{title}","time":"{time}"}}'

@tool(description="Modify an existing calendar event.", is_sink=True, category="calendar")
def modify_event(event_id: str, title: str = "", time: str = "") -> str:
    """Modify a calendar event. This is a sink — it may notify attendees."""
    return f'{{"status":"modified","event_id":"{event_id}"}}'

# ═══════════════════════════════════════════════════════════════════════
#  FINANCE — reading account info
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Get the current account balance.", category="finance")
def get_balance(account_id: str = "") -> str:
    """Get the current balance for an account."""
    return SAMPLE_BALANCE

@tool(description="Get recent transaction history for an account.", category="finance")
def get_transactions(account_id: str = "", limit: int = 10) -> str:
    """Get recent transactions for an account."""
    return _pick(TRANSACTIONS_POOL)

@tool(description="Get account details (type, holder, limits).", category="finance")
def get_account_info(account_id: str = "") -> str:
    """Get account information."""
    return SAMPLE_ACCOUNT_INFO

# ═══════════════════════════════════════════════════════════════════════
#  FINANCE — sink
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Transfer money between accounts or to an external recipient.", is_sink=True, category="finance")
def transfer_money(from_account: str, to_account: str, amount: str) -> str:
    """Transfer money. This is a sink — it moves real funds."""
    return SAMPLE_TRANSFER_RESULT

@tool(description="Pay a bill from a specified account.", is_sink=True, category="finance")
def pay_bill(biller: str, amount: str, from_account: str = "") -> str:
    """Pay a bill. This is a sink — it moves real funds."""
    return SAMPLE_PAYMENT_RESULT

# ═══════════════════════════════════════════════════════════════════════
#  TRAVEL — searching and booking
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Search for flights matching criteria.", category="travel")
def search_flights(origin: str, destination: str, date: str) -> str:
    """Search for available flights."""
    return _pick(FLIGHT_SEARCH_POOL)

@tool(description="Search for hotels in a city for given dates.", category="travel")
def search_hotels(city: str, check_in: str, check_out: str) -> str:
    """Search for available hotels."""
    return _pick(HOTEL_SEARCH_POOL)

@tool(description="Get detailed information about a specific flight.", category="travel")
def get_flight_details(flight_id: str) -> str:
    """Get full details of a flight."""
    return SAMPLE_FLIGHT_DETAILS

@tool(description="Get detailed information about a specific hotel.", category="travel")
def get_hotel_details(hotel_id: str) -> str:
    """Get full details of a hotel."""
    return SAMPLE_HOTEL_DETAILS

# ═══════════════════════════════════════════════════════════════════════
#  TRAVEL — sink
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Book a flight and charge payment.", is_sink=True, category="travel")
def book_flight(flight_id: str, passenger: str) -> str:
    """Book a flight. This is a sink — it charges payment."""
    return SAMPLE_BOOKING_RESULT

@tool(description="Book a hotel room and charge payment.", is_sink=True, category="travel")
def book_hotel(hotel_id: str, guest: str, check_in: str, check_out: str) -> str:
    """Book a hotel. This is a sink — it charges payment."""
    return f'{{"status":"booked","hotel":"{hotel_id}","guest":"{guest}"}}'

# ═══════════════════════════════════════════════════════════════════════
#  SOCIAL — social media feed and posts
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Read the user's social media feed (recent posts).", category="social")
def read_feed() -> str:
    """Read the social media feed."""
    return _pick(FEED_POOL)

@tool(description="Get details of a specific social media post.", category="social")
def get_post(post_id: str) -> str:
    """Get full details of a social media post."""
    return SAMPLE_POST_DETAILS

@tool(description="Get the user's social media notifications.", category="social")
def get_notifications() -> str:
    """Get social media notifications."""
    return SAMPLE_NOTIFICATIONS

# ═══════════════════════════════════════════════════════════════════════
#  SOCIAL — sink
# ═══════════════════════════════════════════════════════════════════════

@tool(description="Create and publish a new social media post.", is_sink=True, category="social")
def create_post(content: str) -> str:
    """Create a post. This is a sink — it publishes publicly."""
    return SAMPLE_POST_RESULT

@tool(description="Share/repost an existing post to your feed.", is_sink=True, category="social")
def share_post(post_id: str, comment: str = "") -> str:
    """Share a post. This is a sink — it publishes to your feed."""
    return SAMPLE_SHARE_RESULT

# ═══════════════════════════════════════════════════════════════════════
#  POOL MANAGEMENT API
# ═══════════════════════════════════════════════════════════════════════

# Build the registry once at import time.
_POOL: Dict[str, Tool] = {}

def _register_pool() -> None:
    """Populate the tool pool from all @tool-decorated functions above."""
    import inspect
    _module = inspect.getmodule(_register_pool)
    for _name, _obj in inspect.getmembers(_module):
        if isinstance(_obj, Tool) and _obj.name not in _POOL:
            _POOL[_obj.name] = _obj

_register_pool()


def all_tools() -> List[Tool]:
    """Return all tools in the pool."""
    return list(_POOL.values())


def get_tool(name: str) -> Optional[Tool]:
    """Return a single tool by name, or ``None`` if not found."""
    return _POOL.get(name)


def get_tools(names: List[str]) -> List[Tool]:
    """Return a list of tools by name (skips unknown names)."""
    return [_POOL[n] for n in names if n in _POOL]


def tools_by_category(category: str) -> List[Tool]:
    """Return all tools in a given category."""
    return [t for t in _POOL.values() if t.category == category]


def data_source_tools() -> List[Tool]:
    """Return all data-source tools (potential taint points)."""
    return [t for t in _POOL.values() if not t.is_sink]


def sink_tools() -> List[Tool]:
    """Return all sink tools (externally-observable actions)."""
    return [t for t in _POOL.values() if t.is_sink]


def tool_names() -> List[str]:
    """Return all tool names in the pool."""
    return list(_POOL.keys())


def categories() -> List[str]:
    """Return all distinct categories in the pool."""
    return sorted(set(t.category for t in _POOL.values()))


# ── Category bundles for scenario agents ───────────────────────────────

#: Tools a browser agent would realistically have.
BROWSER_TOOLS = [
    "fetch_url", "search_web", "download_file", "click_link", "get_page_title",
    "post_form",
]

#: Tools an email assistant would realistically have.
EMAIL_TOOLS = [
    "read_email", "list_emails", "search_emails", "get_attachment",
    "send_email", "forward_email",
    # cross-domain tools a real assistant might also access
    "search_kb", "post_message",
]

#: Tools a coding agent would realistically have.
CODING_TOOLS = [
    "read_code", "read_file", "list_directory", "search_files", "get_file_info",
    "load_skill", "search_codebase",
    "run_command", "run_tests", "write_file", "delete_file", "move_file",
    "install_package",
]

#: Tools a RAG QA agent would realistically have.
RAG_TOOLS = [
    "search_kb", "get_document", "read_file", "summarize_text", "translate_text",
    "post_form",
]

#: Tools a Slack/IM agent would realistically have.
IM_TOOLS = [
    "read_channel", "get_dm", "get_thread",
    "send_dm", "post_message",
    "search_kb",
]

#: Tools a calendar/scheduling agent would realistically have.
CALENDAR_TOOLS = [
    "get_events", "get_event_details",
    "create_event", "modify_event", "schedule_meeting",
    "search_kb",
]

#: Tools a finance/banking agent would realistically have.
FINANCE_TOOLS = [
    "get_balance", "get_transactions", "get_account_info",
    "transfer_money", "pay_bill",
    "post_message",
]

#: Tools a travel booking agent would realistically have.
TRAVEL_TOOLS = [
    "search_flights", "search_hotels", "get_flight_details", "get_hotel_details",
    "book_flight", "book_hotel",
    "post_form",
]

#: Tools a social media agent would realistically have.
SOCIAL_TOOLS = [
    "read_feed", "get_post", "get_notifications",
    "create_post", "share_post",
    "search_web",
]

#: Tools a file management agent would realistically have (reuses file pool).
FILE_MANAGER_TOOLS = [
    "read_file", "list_directory", "search_files", "get_file_info",
    "write_file", "delete_file", "move_file",
    "search_kb",
]


__all__ = [
    # Individual tools
    "fetch_url", "search_web", "download_file", "click_link", "get_page_title",
    "post_form",
    "read_email", "list_emails", "search_emails", "get_attachment",
    "send_email", "forward_email",
    "read_file", "list_directory", "search_files", "get_file_info",
    "write_file", "delete_file", "move_file",
    "read_code", "load_skill", "search_codebase",
    "run_command", "run_tests", "install_package",
    "search_kb", "get_document", "summarize_text", "translate_text",
    "post_message", "create_ticket", "schedule_meeting",
    # IM tools
    "read_channel", "get_dm", "get_thread", "send_dm",
    # Calendar tools
    "get_events", "get_event_details", "create_event", "modify_event",
    # Finance tools
    "get_balance", "get_transactions", "get_account_info",
    "transfer_money", "pay_bill",
    # Travel tools
    "search_flights", "search_hotels", "get_flight_details", "get_hotel_details",
    "book_flight", "book_hotel",
    # Social media tools
    "read_feed", "get_post", "get_notifications", "create_post", "share_post",
    # Pool management
    "all_tools", "get_tool", "get_tools", "tools_by_category",
    "data_source_tools", "sink_tools", "tool_names", "categories",
    # Category bundles
    "BROWSER_TOOLS", "EMAIL_TOOLS", "CODING_TOOLS", "RAG_TOOLS",
    "IM_TOOLS", "CALENDAR_TOOLS", "FINANCE_TOOLS", "TRAVEL_TOOLS",
    "SOCIAL_TOOLS", "FILE_MANAGER_TOOLS",
]
