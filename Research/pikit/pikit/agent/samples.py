"""Realistic-but-fictional sample artifacts for demos and tests.

These are the *clean* carriers an agent would legitimately read. In a demo
you taint one with ``craft(..., data=SAMPLE_WEBPAGE)`` and watch what the
agent does. They are deliberately benign and self-contained — no real URLs,
addresses, secrets, or exploitable code.

The built-in tools return these by default (see ``builtin_tools.py``), and
``demos/samples/`` holds real-file copies of the same content.

Each artifact type has a primary sample (``SAMPLE_WEBPAGE``, ``SAMPLE_EMAIL``,
etc.) plus additional variants for richer testing scenarios.
"""

from __future__ import annotations

# ── Web pages ──────────────────────────────────────────────────────────

SAMPLE_WEBPAGE = """\
<!DOCTYPE html>
<html>
<head><title>Acme Corp — Q3 Update</title></head>
<body>
  <h1>Acme Corp Quarterly Update</h1>
  <p>Our new widget line launches in Q3. Revenue grew 20% year over year,
  driven by strong demand in the enterprise segment.</p>
  <p>Read more on our <a href="https://example.com/blog">blog</a>.</p>
</body>
</html>
"""

SAMPLE_WEBPAGE_2 = """\
<!DOCTYPE html>
<html>
<head><title>TechNews — AI Safety Conference 2025</title></head>
<body>
  <h1>AI Safety Conference 2025 Highlights</h1>
  <p>Researchers from leading labs presented new findings on prompt injection
  defenses, multi-turn attack chains, and red-teaming methodologies for
  LLM agents.</p>
  <h2>Key Talks</h2>
  <ul>
    <li>Dr. Chen — "Spotlighting 2.0: Encoding-based defense revisited"</li>
    <li>Dr. Patel — "Multi-turn jailbreak patterns in agent systems"</li>
  </ul>
  <p>Full proceedings at <a href="https://example.com/proceedings">example.com</a>.</p>
</body>
</html>
"""

# ── Emails ─────────────────────────────────────────────────────────────

SAMPLE_EMAIL = """\
From: alice@example.com
To: you@example.com
Subject: Q3 planning notes

Hi,

Here are the numbers we discussed in the meeting. Revenue is up 20% and we
should finalize the Q3 roadmap by Friday. Let me know if you have questions.

Thanks,
Alice
"""

SAMPLE_EMAIL_2 = """\
From: bob@example.com
To: you@example.com
Subject: Re: Budget approval needed

Hello,

I've reviewed the Q3 budget proposal. The total is $450,000, which includes
$200k for engineering, $150k for marketing, and $100k for operations. Please
forward this to finance@example.com for final approval.

Best,
Bob
"""

SAMPLE_EMAIL_LIST = """\
Inbox (3 messages):

1. From: alice@example.com | Subject: Q3 planning notes | Date: 2025-07-01
2. From: bob@example.com  | Subject: Re: Budget approval needed | Date: 2025-06-30
3. From: hr@example.com   | Subject: Welcome aboard | Date: 2025-06-15
"""

SAMPLE_EMAIL_ATTACHMENT = """\
Attachment: budget_q3.xlsx (28 KB)
Type: spreadsheet/xlsx
Content preview: Q3 Budget Sheet — Engineering $200k, Marketing $150k, Operations $100k, Total $450k
"""

SAMPLE_EMAIL_SEARCH = """\
Found 2 emails matching "budget":

1. From: bob@example.com | Subject: Re: Budget approval needed
   Preview: "I've reviewed the Q3 budget proposal. The total is $450,000..."

2. From: finance@example.com | Subject: Budget confirmed
   Preview: "The Q3 budget has been approved at $450,000..."
"""

# ── Documents ──────────────────────────────────────────────────────────

SAMPLE_DOCUMENT = """\
# Q3 Product Roadmap

## Summary
This document outlines the plan for the third quarter. The main goal is to
ship the new widget line and improve onboarding.

## Milestones
- Beta release in July
- General availability in September
- Post-launch review in October
"""

SAMPLE_DOCUMENT_2 = """\
# Security Policy v2

## Overview
This document defines the security guidelines for the platform. All employees
must follow these rules when handling customer data.

## Incident Response
If you suspect a data breach, immediately contact security@example.com and
do not discuss the incident outside the security team.

## Access Control
- API keys must be stored in the vault, never in code
- Production access requires manager approval
- Audit logs are reviewed weekly
"""

# ── Source code ────────────────────────────────────────────────────────

SAMPLE_CODE = """\
def calculate_total(items):
    \"\"\"Return the sum of item prices, applying a 10% discount over $100.\"\"\"
    total = 0
    for item in items:
        total += item["price"] * item["quantity"]
    if total > 100:
        total *= 0.9
    return round(total, 2)
"""

SAMPLE_CODE_2 = """\
import os

def read_config(path="config.yaml"):
    \"\"\"Read a YAML config file and return it as a dict.\"\"\"
    with open(path) as f:
        return _parse_yaml(f.read())

def _parse_yaml(text):
    # Minimal YAML parser — supports key: value pairs only.
    result = {}
    for line in text.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            result[k.strip()] = v.strip()
    return result
"""

# ── Agent skills ───────────────────────────────────────────────────────

SAMPLE_SKILL = """\
---
name: pdf-summarizer
description: Summarize the key points of a PDF document into a short bullet list.
---

# PDF Summarizer

When the user provides a PDF, extract the main sections and produce a concise
bullet-point summary.

## Instructions
1. Read the document text.
2. Identify the main topics.
3. Return 3-5 bullet points capturing the key ideas.
"""

SAMPLE_SKILL_2 = """\
---
name: code-reviewer
description: Review code for common security issues and suggest fixes.
---

# Code Reviewer

When the user asks for a code review, analyze the provided code for security
vulnerabilities, style issues, and potential bugs.

## Instructions
1. Read the code carefully.
2. Check for: injection risks, hardcoded secrets, unsafe file operations.
3. Suggest fixes with code examples.
"""

# ── Search results ─────────────────────────────────────────────────────

SAMPLE_SEARCH_RESULT = """\
## Search Results for: Q3 roadmap

### Result 1 (score: 0.95)
**Source:** internal-docs/roadmap-q3.md
**Content:** The Q3 roadmap focuses on shipping the widget line and improving
onboarding. Key milestones: Beta in July, GA in September, review in October.

### Result 2 (score: 0.78)
**Source:** internal-docs/budget-q3.md
**Content:** Q3 budget approved at $450,000 split across engineering,
marketing, and operations.
"""

SAMPLE_SEARCH_RESULT_2 = """\
## Search Results for: prompt injection defense

### Result 1 (score: 0.92)
**Source:** papers/spotlighting.pdf
**Content:** Spotlighting is an encoding-based defense that separates
untrusted content from system instructions using delimiters and data
transformations.

### Result 2 (score: 0.85)
**Source:** papers/bipia-benchmark.pdf
**Content:** BIPIA is a benchmark for indirect prompt injection attacks on
LLM agents, evaluating both attack effectiveness and defense robustness.
"""

# ── File system ────────────────────────────────────────────────────────

SAMPLE_FILE_LISTING = """\
project/
  src/
    main.py          (2.1 KB, modified 2025-06-28)
    config.py        (1.5 KB, modified 2025-06-25)
    utils.py         (0.8 KB, modified 2025-06-20)
  docs/
    roadmap.md       (3.2 KB, modified 2025-07-01)
    security.md      (2.0 KB, modified 2025-06-15)
  tests/
    test_main.py     (1.1 KB, modified 2025-06-28)
    test_config.py   (0.9 KB, modified 2025-06-25)
  README.md          (4.5 KB, modified 2025-07-01)
  requirements.txt   (0.3 KB, modified 2025-06-20)
"""

SAMPLE_FILE_INFO = """\
File: src/main.py
Size: 2,145 bytes
Modified: 2025-06-28 14:30:00
Permissions: rw-r--r--
Owner: developer
"""

# ── Codebase search ────────────────────────────────────────────────────

SAMPLE_CODEBASE_SEARCH = """\
Found 3 matches in 2 files:

src/config.py:15
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/app")

src/config.py:23
    API_KEY = os.getenv("API_KEY", "")

src/main.py:8
    config = read_config("config.yaml")
"""

# ── Test results ───────────────────────────────────────────────────────

SAMPLE_TEST_RESULT = """\
Ran 12 tests in 0.34s

OK (12 passed, 0 failed, 0 skipped)
- test_calculate_total (0.02s) ... ok
- test_discount (0.01s) ... ok
- test_edge_cases (0.03s) ... ok
"""

# ── Package install ────────────────────────────────────────────────────

SAMPLE_INSTALL_RESULT = """\
Successfully installed:
  numpy-1.26.0
  pandas-2.1.1
  matplotlib-3.8.0
"""

# ── Meeting ────────────────────────────────────────────────────────────

SAMPLE_MEETING_RESULT = """\
Meeting scheduled successfully.
Title: Q3 Roadmap Review
Time: 2025-07-05 14:00-15:00
Attendees: alice@example.com, bob@example.com
Location: Conference Room B
"""

# ── Ticket ─────────────────────────────────────────────────────────────

SAMPLE_TICKET_RESULT = """\
Ticket created successfully.
ID: TKT-2025-042
Title: Fix login redirect bug
Priority: High
Status: Open
"""

# ── Messages ───────────────────────────────────────────────────────────

SAMPLE_MESSAGE_RESULT = """\
Message posted to #engineering channel:
"Q3 code freeze starts Friday. Please merge all PRs by Thursday EOD."
Posted by: bot
Timestamp: 2025-07-01T10:30:00Z
"""

# ── Downloaded file ────────────────────────────────────────────────────

SAMPLE_DOWNLOAD_RESULT = """\
Downloaded file from https://example.com/data/report.pdf
Size: 245 KB
Type: application/pdf
Saved to: /tmp/report.pdf
Content preview: Q3 Financial Report — Revenue $2.3M, Growth 20% YoY
"""

# ── Page title ─────────────────────────────────────────────────────────

SAMPLE_PAGE_TITLE = "Acme Corp — Q3 Update"

# ── Web search ─────────────────────────────────────────────────────────

SAMPLE_WEB_SEARCH = """\
## Web Search Results for: best practices for LLM security

### 1. OWASP Top 10 for LLM Applications (2025)
**URL:** https://owasp.org/llm-top-10
**Snippet:** The OWASP Top 10 for LLMs covers prompt injection, insecure
output handling, training data tainting, and more.

### 2. NIST AI Risk Management Framework
**URL:** https://nist.gov/ai-rmf
**Snippet:** The NIST AI RMF provides guidelines for managing risks
associated with AI systems, including adversarial attacks.

### 3. Prompt Injection Attacks and Defenses
**URL:** https://example.com/prompt-injection-guide
**Snippet:** A comprehensive guide on prompt injection attack vectors and
defense strategies for LLM-based applications.
"""

# ── Translation ────────────────────────────────────────────────────────

SAMPLE_TRANSLATION_RESULT = """\
Translation (en → zh):
原文: Revenue grew 20% year over year.
译文: 收入同比增长20%。
"""

# ── Structured data (JSON / CSV / TSV) ─────────────────────────────────

SAMPLE_JSON = """\
{"status": "ok", "count": 3, "items": ["widget", "gadget", "gizmo"]}
"""

SAMPLE_CSV = """\
name,category,price
Widget,Hardware,29.99
Gadget,Accessory,14.99
Gizmo,Hardware,49.99
"""

# ── PDF metadata ───────────────────────────────────────────────────────

SAMPLE_PDF_METADATA = """\
Title: Q3 Financial Report
Author: Finance Team
Subject: Quarterly Results
Keywords: finance, q3, report
"""

# ── Log file ───────────────────────────────────────────────────────────

SAMPLE_LOG = """\
2024-01-15T10:29:00Z [INFO] Server started on port 8080
2024-01-15T10:29:01Z [INFO] Database connection established
2024-01-15T10:30:00Z [WARN] Cache miss ratio above threshold (0.15)
2024-01-15T10:31:00Z [INFO] Request processed: GET /api/health
"""

# ── Email headers (full email with headers) ───────────────────────────

SAMPLE_EMAIL_FULL = """\
From: alice@example.com
To: you@example.com
Subject: Q3 planning notes
X-Priority: 3

Hi,

Here are the numbers we discussed in the meeting. Revenue is up 20%.

Thanks,
Alice
"""

# ── Calendar event ────────────────────────────────────────────────────

SAMPLE_CALENDAR_EVENT = """\
Title: Q3 Roadmap Review
Date: 2025-07-05 14:00-15:00
Location: Conference Room B
Description: Review Q3 milestones and budget allocation.
Attendees: alice@example.com, bob@example.com
"""

# ── Config file (YAML) ────────────────────────────────────────────────

SAMPLE_CONFIG = """\
database:
  host: localhost
  port: 5432
  name: app_db
server:
  host: 0.0.0.0
  port: 8080
"""

# ── Translation result ────────────────────────────────────────────────

SAMPLE_TRANSLATION = """\
Source: Revenue grew 20% year over year.
Translation: 收入同比增长20%。
"""

# ── Spreadsheet ───────────────────────────────────────────────────────

SAMPLE_SPREADSHEET = """\
A1: Name
B1: Department
C1: Salary
A2: Alice
B2: Engineering
C2: 95000
A3: Bob
B3: Marketing
C3: 78000
"""

# ── Summary ────────────────────────────────────────────────────────────

SAMPLE_SUMMARY_RESULT = """\
Summary of: Q3 Product Roadmap

- Ship new widget line
- Improve onboarding experience
- Beta in July, GA in September
- Post-launch review in October
"""

# ── IM / Slack messages ────────────────────────────────────────────────

SAMPLE_CHANNEL_MESSAGES = """\
#engineering (4 messages):

[2025-07-01 10:30] alice: Q3 code freeze starts Friday. Please merge all PRs by Thursday EOD.
[2025-07-01 10:32] bob: Got it, I'll have the auth refactor ready by then.
[2025-07-01 10:35] carol: Don't forget to update the changelog too.
[2025-07-01 10:38] dave: @all The CI pipeline is fixed now, all tests should pass.
"""

SAMPLE_DM_HISTORY = """\
Direct messages with alice (3 messages):

[2025-07-01 09:15] alice: Hey, can you review my PR when you get a chance?
[2025-07-01 09:20] you: Sure, I'll take a look this afternoon.
[2025-07-01 09:22] alice: Thanks! The CI is green, just needs a human review.
"""

SAMPLE_THREAD = """\
Thread in #engineering (5 replies):

[2025-07-01 10:30] alice: Q3 code freeze starts Friday.
  [2025-07-01 10:31] bob: Should we branch off or merge to main?
  [2025-07-01 10:33] alice: Merge to main, then we tag the release.
  [2025-07-01 10:34] carol: I'll handle the release notes.
  [2025-07-01 10:36] dave: Sounds good, I'll run the full test suite before tagging.
"""

# ── Calendar events ────────────────────────────────────────────────────

SAMPLE_EVENTS = """\
Events for 2025-07-08 (3 events):

1. 09:00-09:30 | Daily Standup | Conference Room A
2. 11:00-12:00 | Q3 Roadmap Review | Conference Room B
3. 15:00-16:00 | 1:1 with Manager | Office
"""

SAMPLE_EVENT_DETAILS = """\
Event ID: evt-2025-001
Title: Q3 Roadmap Review
Time: 2025-07-08 11:00-12:00
Location: Conference Room B
Description: Review Q3 milestones, budget allocation, and team assignments. Alice will present the engineering plan and Bob will cover the marketing strategy.
Attendees: alice@example.com, bob@example.com, carol@example.com
Status: Confirmed
"""

# ── Finance / banking ──────────────────────────────────────────────────

SAMPLE_BALANCE = """\
Account: Checking (****4521)
Balance: $12,450.75
Available: $12,350.75
Last updated: 2025-07-08 08:00:00 UTC
"""

SAMPLE_TRANSACTIONS = """\
Recent transactions for Checking (****4521):

1. 2025-07-07 | Coffee Shop | -$4.50 | Balance: $12,455.25
2. 2025-07-06 | Salary Deposit | +$5,200.00 | Balance: $12,459.75
3. 2025-07-05 | Electric Bill | -$145.30 | Balance: $7,259.75
4. 2025-07-04 | Grocery Store | -$87.20 | Balance: $7,405.05
5. 2025-07-03 | Online Subscription | -$12.99 | Balance: $7,492.25
"""

SAMPLE_ACCOUNT_INFO = """\
Account: Checking (****4521)
Type: Personal Checking
Holder: John Doe
Opened: 2020-03-15
Currency: USD
Monthly fee: $0 (waived with direct deposit)
Transfer limit: $10,000 per day
"""

SAMPLE_TRANSFER_RESULT = """\
Transfer initiated successfully.
From: Checking (****4521)
To: Savings (****8930)
Amount: $1,000.00
Reference: TRX-2025-07-08-001
Status: Completed
"""

SAMPLE_PAYMENT_RESULT = """\
Bill payment processed.
Biller: City Electric
Amount: $145.30
From: Checking (****4521)
Confirmation: PMT-2025-07-08-003
Status: Completed
"""

# ── Travel ─────────────────────────────────────────────────────────────

SAMPLE_FLIGHT_SEARCH = """\
Flights from SFO to JFK on 2025-07-15:

1. AA 123 | 08:00→17:30 | $320 | 1 stop (ORD) | 7h30m
2. UA 456 | 10:00→18:45 | $410 | Nonstop | 5h45m
3. DL 789 | 14:00→23:15 | $280 | 1 stop (ATL) | 6h15m
4. B6 012 | 18:00→06:30+1 | $350 | Nonstop (Redeye) | 5h30m
"""

SAMPLE_HOTEL_SEARCH = """\
Hotels in New York (2025-07-15 to 2025-07-18, 3 nights):

1. Grand Hotel | ★★★★★ | $350/night | Midtown | Free WiFi, Pool, Gym
2. City Inn | ★★★☆☆ | $120/night | Chelsea | Free WiFi, Breakfast
3. Boutique Suites | ★★★★☆ | $220/night | SoHo | Free WiFi, Spa, Restaurant
4. Budget Lodge | ★★☆☆☆ | $75/night | Queens | Free parking
"""

SAMPLE_FLIGHT_DETAILS = """\
Flight: UA 456
Date: 2025-07-15
Route: SFO → JFK
Departure: 10:00 AM (SFO Terminal 3)
Arrival: 5:45 PM (JFK Terminal 4)
Duration: 5h 45m
Aircraft: Boeing 757
Class: Economy
Price: $410.00
Seats available: 12
"""

SAMPLE_HOTEL_DETAILS = """\
Hotel: Grand Hotel
Rating: ★★★★★ (4.8/5 from 1,240 reviews)
Location: Midtown Manhattan, 123 Park Ave
Check-in: 2025-07-15 (3:00 PM)
Check-out: 2025-07-18 (11:00 AM)
Room type: Deluxe King
Price: $350/night ($1,050 total)
Amenities: Free WiFi, Pool, Gym, Spa, Restaurant, Room Service
Cancellation: Free until 48h before check-in
"""

SAMPLE_BOOKING_RESULT = """\
Booking confirmed.
Type: Flight
Reference: BK-2025-07-08-FL001
Details: UA 456 on 2025-07-15, SFO→JFK, Economy
Passenger: John Doe
Total: $410.00
Status: Confirmed
"""

# ── Social media ────────────────────────────────────────────────────────

SAMPLE_FEED = """\
Social feed (5 posts):

1. @tech_news | 2h ago | "Breaking: New AI safety framework released by major labs. Key focus on prompt injection defenses and agent security."
   Likes: 342 | Comments: 28 | Shares: 15

2. @alice_dev | 5h ago | "Just shipped the Q3 roadmap! Excited to share what we've been building. Thread incoming 🧵"
   Likes: 89 | Comments: 12 | Shares: 5

3. @product_blog | 8h ago | "Our latest deep dive into LLM agent architectures is live. We cover tool-use, RAG, and multi-step reasoning."
   Likes: 156 | Comments: 34 | Shares: 42

4. @bob_sec | 12h ago | "Reminder: never paste untrusted content into your AI tools without sanitization. Indirect injection is real."
   Likes: 203 | Comments: 19 | Shares: 67

5. @carol_design | 1d ago | "New design system v2 is out! Updated components, better accessibility, and dark mode support."
   Likes: 78 | Comments: 8 | Shares: 3
"""

SAMPLE_POST_DETAILS = """\
Post by @tech_news (2 hours ago):
"Breaking: New AI safety framework released by major labs. Key focus on prompt injection defenses and agent security."

Likes: 342 | Comments: 28 | Shares: 15
URL: https://social.example.com/post/12345
"""

SAMPLE_NOTIFICATIONS = """\
Notifications (3):

1. @alice_dev mentioned you in a comment: "Great point about the security review!"
2. Your post received 50+ likes.
3. @product_blog shared your post about agent security.
"""

SAMPLE_POST_RESULT = """\
Post created successfully.
Content: "Excited to announce our Q3 roadmap! Stay tuned for updates."
Posted by: you
Timestamp: 2025-07-08T14:30:00Z
Post ID: post-2025-789
"""

SAMPLE_SHARE_RESULT = """\
Post shared successfully.
Original post by @tech_news
Your comment: "Important thread on AI safety — worth a read."
Shared to your feed.
"""

__all__ = [
    # Primary samples (used by builtin_tools.py defaults)
    "SAMPLE_WEBPAGE",
    "SAMPLE_EMAIL",
    "SAMPLE_DOCUMENT",
    "SAMPLE_CODE",
    "SAMPLE_SKILL",
    # Additional variants for richer testing
    "SAMPLE_WEBPAGE_2",
    "SAMPLE_EMAIL_2",
    "SAMPLE_DOCUMENT_2",
    "SAMPLE_CODE_2",
    "SAMPLE_SKILL_2",
    "SAMPLE_SEARCH_RESULT",
    # New samples for expanded tool pool
    "SAMPLE_EMAIL_LIST",
    "SAMPLE_EMAIL_ATTACHMENT",
    "SAMPLE_EMAIL_SEARCH",
    "SAMPLE_SEARCH_RESULT_2",
    "SAMPLE_FILE_LISTING",
    "SAMPLE_FILE_INFO",
    "SAMPLE_CODEBASE_SEARCH",
    "SAMPLE_TEST_RESULT",
    "SAMPLE_INSTALL_RESULT",
    "SAMPLE_MEETING_RESULT",
    "SAMPLE_TICKET_RESULT",
    "SAMPLE_MESSAGE_RESULT",
    "SAMPLE_DOWNLOAD_RESULT",
    "SAMPLE_PAGE_TITLE",
    "SAMPLE_WEB_SEARCH",
    "SAMPLE_TRANSLATION_RESULT",
    "SAMPLE_SUMMARY_RESULT",
    # New channel samples
    "SAMPLE_JSON",
    "SAMPLE_CSV",
    "SAMPLE_PDF_METADATA",
    "SAMPLE_LOG",
    "SAMPLE_EMAIL_FULL",
    "SAMPLE_CALENDAR_EVENT",
    "SAMPLE_CONFIG",
    "SAMPLE_TRANSLATION",
    "SAMPLE_SPREADSHEET",
    # IM / Slack
    "SAMPLE_CHANNEL_MESSAGES",
    "SAMPLE_DM_HISTORY",
    "SAMPLE_THREAD",
    # Calendar
    "SAMPLE_EVENTS",
    "SAMPLE_EVENT_DETAILS",
    # Finance / banking
    "SAMPLE_BALANCE",
    "SAMPLE_TRANSACTIONS",
    "SAMPLE_ACCOUNT_INFO",
    "SAMPLE_TRANSFER_RESULT",
    "SAMPLE_PAYMENT_RESULT",
    # Travel
    "SAMPLE_FLIGHT_SEARCH",
    "SAMPLE_HOTEL_SEARCH",
    "SAMPLE_FLIGHT_DETAILS",
    "SAMPLE_HOTEL_DETAILS",
    "SAMPLE_BOOKING_RESULT",
    # Social media
    "SAMPLE_FEED",
    "SAMPLE_POST_DETAILS",
    "SAMPLE_NOTIFICATIONS",
    "SAMPLE_POST_RESULT",
    "SAMPLE_SHARE_RESULT",
    # Sample pools for data diversity
    "WEBPAGE_POOL",
    "EMAIL_POOL",
    "DOCUMENT_POOL",
    "CODE_POOL",
    "SKILL_POOL",
    "CHANNEL_MESSAGES_POOL",
    "TRANSACTIONS_POOL",
    "FEED_POOL",
    "SEARCH_RESULT_POOL",
    "EVENTS_POOL",
    "FLIGHT_SEARCH_POOL",
    "HOTEL_SEARCH_POOL",
]

# ═══════════════════════════════════════════════════════════════════════
#  SAMPLE POOLS — multiple variants per data source for realistic diversity
# ═══════════════════════════════════════════════════════════════════════

#: Webpage variants — different topics, lengths, and structures.
WEBPAGE_POOL = [SAMPLE_WEBPAGE, SAMPLE_WEBPAGE_2, """\
<!DOCTYPE html>
<html>
<head><title>GitHub — pikit / Issues</title></head>
<body>
  <h1>pikit Issues</h1>
  <p>Open issues: 3. Closed: 12.</p>
  <h2>Open</h2>
  <ul>
    <li>#8 Add multi-agent support — assigned to @alice</li>
    <li>#9 Unicode channel test failures — assigned to @bob</li>
    <li>#10 Docs: add attack reference table — unassigned</li>
  </ul>
</body>
</html>
"""]

#: Email variants — different senders, subjects, and content.
EMAIL_POOL = [SAMPLE_EMAIL, SAMPLE_EMAIL_2, """\
From: carol@example.com
To: you@example.com
Subject: Meeting moved to Thursday

Hi,

Just a heads up that the Q3 review meeting has been moved to Thursday at
2pm. The agenda is the same. Please update your calendar.

Best,
Carol
"""]

#: Document variants — different topics and structures.
DOCUMENT_POOL = [SAMPLE_DOCUMENT, SAMPLE_DOCUMENT_2, """\
# Incident Report — 2025-07-06

## Summary
At 14:32 UTC, the API gateway returned elevated 502 errors for 12 minutes.

## Root Cause
A misconfigured rate-limit rule caused legitimate traffic to be dropped.

## Actions Taken
- Rolled back the rate-limit config to previous version
- Added monitoring alert for 502 error rate > 5%
- Scheduled post-mortem for 2025-07-10
"""]

#: Code variants — different languages and purposes.
CODE_POOL = [SAMPLE_CODE, SAMPLE_CODE_2, """\
// config.js — Application configuration
const config = {
  api: {
    baseUrl: process.env.API_URL || 'https://api.example.com',
    timeout: 5000,
  },
  db: {
    host: process.env.DB_HOST || 'localhost',
    port: 5432,
  },
};

module.exports = config;
"""]

#: Skill variants — different skill types.
SKILL_POOL = [SAMPLE_SKILL, SAMPLE_SKILL_2, """\
---
name: email-drafter
description: Draft professional email responses based on context.
---

# Email Drafter

When the user asks to draft or reply to an email, compose a professional
response based on the conversation context and email thread.

## Instructions
1. Read the email thread and understand the context.
2. Draft a concise, professional reply.
3. Include a clear subject line and greeting.
"""]

#: Channel messages variants — different channels and conversations.
CHANNEL_MESSAGES_POOL = [SAMPLE_CHANNEL_MESSAGES, """\
#general (5 messages):

[2025-07-01 14:00] erin: Reminder: company all-hands tomorrow at 10am in the main auditorium.
[2025-07-01 14:05] frank: Will it be recorded? I have a conflicting meeting.
[2025-07-01 14:06] erin: Yes, it'll be posted to the intranet by EOD.
[2025-07-01 14:10] grace: @frank I'll share my notes with you too.
[2025-07-01 14:15] henry: Don't forget to submit your Q3 OKRs before Friday.
""", """\
#support (4 messages):

[2025-07-01 09:00] ivan: Customer #1234 is reporting that exports are failing.
[2025-07-01 09:03] judy: I'll take a look. What error are they seeing?
[2025-07-01 09:05] ivan: They get a timeout after 30 seconds.
[2025-07-01 09:08] judy: Likely the S3 bucket is full. I'll clean it up and retry.
"""]

#: Transaction variants — different spending patterns.
TRANSACTIONS_POOL = [SAMPLE_TRANSACTIONS, """\
Recent transactions for Savings (****8930):

1. 2025-07-07 | Interest Payment | +$12.50 | Balance: $25,450.00
2. 2025-07-06 | Auto Transfer from Checking | +$500.00 | Balance: $25,437.50
3. 2025-07-05 | Mortgage Payment | -$1,850.00 | Balance: $24,937.50
4. 2025-07-01 | Auto Transfer from Checking | +$500.00 | Balance: $26,787.50
""", """\
Recent transactions for Credit Card (****1122):

1. 2025-07-07 | Restaurant | -$68.40 | Balance: -$68.40
2. 2025-07-06 | Gas Station | -$52.15 | Balance: -$120.55
3. 2025-07-05 | Online Shopping | -$234.99 | Balance: -$173.15
4. 2025-07-04 | Streaming Service | -$15.99 | Balance: -$61.95
5. 2025-07-03 | Grocery Store | -$112.30 | Balance: -$45.96
"""]

#: Feed variants — different social media content.
FEED_POOL = [SAMPLE_FEED, """\
Social feed (5 posts):

1. @startup_life | 1h ago | "Hiring alert! We're looking for a senior AI security engineer. Remote-friendly, competitive comp. DM me!"
   Likes: 45 | Comments: 8 | Shares: 22

2. @alice_dev | 3h ago | "Hot take: most agent benchmarks test the wrong thing. Real threats are indirect injections through tool results, not jailbreaks."
   Likes: 178 | Comments: 45 | Shares: 89

3. @tech_news | 6h ago | "New paper shows that instruction hierarchy defenses reduce indirect injection success by 70% across tested models."
   Likes: 312 | Comments: 56 | Shares: 134

4. @bob_sec | 10h ago | "If your agent reads external data without spotlighting, you're vulnerable. Full stop."
   Likes: 201 | Comments: 23 | Shares: 67

5. @design_daily | 1d ago | "Beautiful dashboard redesign from @carol_design. Love the attention to accessibility details."
   Likes: 92 | Comments: 11 | Shares: 4
""", """\
Social feed (4 posts):

1. @news_breaking | 30m ago | "Breaking: Major tech companies announce joint AI safety initiative focusing on agent security standards."
   Likes: 892 | Comments: 134 | Shares: 456

2. @alice_dev | 2h ago | "Just published my deep dive on indirect prompt injection defenses. Link in bio!"
   Likes: 245 | Comments: 38 | Shares: 102

3. @devops_life | 5h ago | "Pro tip: always sanitize tool outputs before passing them to your LLM agent. Trust me on this one."
   Likes: 156 | Comments: 19 | Shares: 73

4. @carol_design | 8h ago | "Updated our security dashboard with real-time injection attempt monitoring. Really proud of this one."
   Likes: 87 | Comments: 12 | Shares: 15
"""]

#: Search result variants.
SEARCH_RESULT_POOL = [SAMPLE_SEARCH_RESULT, SAMPLE_SEARCH_RESULT_2, """\
## Search Results for: agent security

### Result 1 (score: 0.91)
**Source:** papers/instruction-hierarchy.pdf
**Content:** Instruction hierarchy is a defense that assigns trust levels
to different instruction sources. System > developer > user > external data.

### Result 2 (score: 0.83)
**Source:** blogs/agent-red-teaming.md
**Content:** Red-teaming LLM agents requires testing indirect injection
through tool results, not just direct prompt manipulation.
"""]

#: Event variants.
EVENTS_POOL = [SAMPLE_EVENTS, """\
Events for 2025-07-09 (4 events):

1. 08:30-09:00 | Morning Coffee | Kitchen
2. 10:00-11:30 | Product Strategy | Room 301
3. 13:00-14:00 | Lunch with Client | Café Central
4. 16:00-17:00 | Sprint Retrospective | Room 205
""", """\
Events for 2025-07-10 (2 events):

1. 09:00-10:00 | Weekly 1:1 | Manager's Office
2. 14:00-15:30 | Security Training (Mandatory) | Auditorium
"""]

#: Flight search variants.
FLIGHT_SEARCH_POOL = [SAMPLE_FLIGHT_SEARCH, """\
Flights from JFK to LHR on 2025-07-20:

1. BA 178 | 22:00→10:15+1 | $650 | Nonstop | 7h15m
2. VS 4 | 21:30→09:45+1 | $580 | Nonstop | 7h15m
3. AA 106 | 18:00→06:30+1 | $720 | 1 stop (DUB) | 9h30m
4. DL 410 | 17:00→05:45+1 | $540 | 1 stop (AMS) | 9h45m
""", """\
Flights from LAX to NRT on 2025-08-01:

1. JL 5 | 13:00→16:45+1 | $890 | Nonstop | 11h45m
2. NH 7 | 11:00→14:30+1 | $820 | Nonstop | 11h30m
3. UA 837 | 10:00→17:15+1 | $760 | 1 stop (HND) | 14h15m
4. SQ 11 | 20:00→23:50+1 | $950 | 1 stop (SIN) | 16h50m
"""]

#: Hotel search variants.
HOTEL_SEARCH_POOL = [SAMPLE_HOTEL_SEARCH, """\
Hotels in London (2025-07-20 to 2025-07-23, 3 nights):

1. The Ritz | ★★★★★ | $650/night | Mayfair | Spa, Restaurant, Butler Service
2. Travelodge | ★★☆☆☆ | $90/night | Kings Cross | Free WiFi
3. Premier Inn | ★★★☆☆ | $120/night | Westminster | Free Breakfast, WiFi
4. boutique Stay | ★★★★☆ | $280/night | Shoreditch | Free WiFi, Bar, Gym
""", """\
Hotels in Tokyo (2025-08-01 to 2025-08-04, 3 nights):

1. Park Hyatt | ★★★★★ | $480/night | Shinjuku | Pool, Spa, City View
2. Capsule Inn | ★☆☆☆☆ | $35/night | Asakusa | Shared Bath
3. APA Hotel | ★★★☆☆ | $85/night | Ginza | Free WiFi, Breakfast
4. ryokan Style | ★★★★☆ | $220/night | Shibuya | Traditional, Onsen
"""]
