# Data Auto-Sync API

## Overview

AIG detects AI infrastructure vulnerabilities using rule files in the `data/` directory. The **Data Auto-Sync** API allows you to pull the latest rules from the official GitHub repository (`Tencent/AI-Infra-Guard`) without restarting the server or rebuilding the Docker image.

- **Base URL**: `http://localhost:8088` (adjust to your deployment address)
- **Content-Type**: `application/json`
- **Authentication**: No authentication required

The sync is performed by cloning the repository into a temporary directory using `git clone`, then copying the requested `data/` sub-directories into the working directory. No GitHub token is needed.

## Data Directory Layout

| Sub-directory | Contents |
|---|---|
| `data/fingerprints/` | YAML fingerprint rules for AI components |
| `data/vuln/` | Chinese CVE/GHSA vulnerability rules |
| `data/vuln_en/` | English CVE/GHSA vulnerability rules |
| `data/mcp/` | MCP security detection rules |
| `data/eval/` | Jailbreak / prompt-security evaluation datasets |
| `data/agents/` | Agent scan configuration |

---

## API Endpoints

### 1. Trigger Data Sync

#### Endpoint Info

- **URL**: `/api/v1/system/update-data`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `ref` | string | No | `"main"` | Branch name or Git tag to sync from |
| `is_tag` | bool | No | `false` | Set `true` when `ref` is a Git tag (e.g. `"v4.1.3"`) |
| `dirs` | string | No | `"fingerprints,vuln,vuln_en,mcp,eval,agents"` | Comma-separated list of `data/` sub-directories to sync |

An empty request body (`{}`) is valid and triggers a sync of all directories from the `main` branch.

#### Response Fields

| Field | Type | Description |
|---|---|---|
| `running` | bool | Whether a sync is currently in progress |
| `success` | bool | Whether the last sync succeeded (absent if never run) |
| `started_at` | string | ISO-8601 timestamp when the sync started |
| `finished_at` | string | ISO-8601 timestamp when the sync finished (absent if still running) |
| `message` | string | Human-readable status message |
| `files_updated` | int | Number of files written to disk |
| `ref` | string | Branch or tag that was used |

#### Response Codes

| Code | Meaning |
|---|---|
| `202 Accepted` | Sync started successfully |
| `200 OK` | A sync is already running; returns current status |

#### cURL Examples

**Sync latest `main` branch**
```bash
curl -X POST http://localhost:8088/api/v1/system/update-data \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Sync a specific release tag**
```bash
curl -X POST http://localhost:8088/api/v1/system/update-data \
  -H "Content-Type: application/json" \
  -d '{
    "ref": "v4.1.3",
    "is_tag": true
  }'
```

**Sync only fingerprint and vulnerability rules**
```bash
curl -X POST http://localhost:8088/api/v1/system/update-data \
  -H "Content-Type: application/json" \
  -d '{
    "dirs": "fingerprints,vuln,vuln_en"
  }'
```

#### Python Example

```python
import requests
import time

BASE_URL = "http://localhost:8088"

def trigger_sync(ref="main", is_tag=False, dirs=None):
    payload = {"ref": ref, "is_tag": is_tag}
    if dirs:
        payload["dirs"] = dirs
    resp = requests.post(f"{BASE_URL}/api/v1/system/update-data", json=payload)
    return resp.json()

def wait_for_sync(poll_interval=3, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        status = requests.get(f"{BASE_URL}/api/v1/system/update-status").json()
        print(f"[{status.get('message')}] files_updated={status.get('files_updated')}")
        if not status.get("running"):
            return status
        time.sleep(poll_interval)
    raise TimeoutError("sync timed out")

# Trigger and wait
result = trigger_sync()
print(result)
final = wait_for_sync()
if final.get("success"):
    print(f"Sync complete — {final['files_updated']} file(s) updated")
else:
    print(f"Sync failed: {final['message']}")
```

---

### 2. Get Sync Status

#### Endpoint Info

- **URL**: `/api/v1/system/update-status`
- **Method**: `GET`

#### Response Fields

Same fields as the trigger endpoint response (see above).

#### cURL Example

```bash
curl http://localhost:8088/api/v1/system/update-status
```

#### Example Response

```json
{
  "running": false,
  "success": true,
  "started_at": "2026-04-17T10:00:00Z",
  "finished_at": "2026-04-17T10:00:45Z",
  "message": "sync complete — 312 file(s) updated from ref \"main\"",
  "files_updated": 312,
  "ref": "main"
}
```

---

## Typical Workflow

1. **Trigger sync** — call `POST /api/v1/system/update-data`; the operation runs in the background and the endpoint returns `202 Accepted` immediately.
2. **Poll for completion** — call `GET /api/v1/system/update-status` periodically until `running` is `false`.
3. **Check result** — inspect `success` and `message` to confirm the sync succeeded.
4. **No restart needed** — AIG reads rule files at scan time, so updated rules take effect on the next scan without a server restart.

## Notes

- Only one sync can run at a time. Concurrent requests return the current status with `200 OK`.
- The `git` binary must be available in the server's `PATH`.
- The server must be able to reach `github.com` on port 443.
- The sync uses `git clone --depth 1` to minimise bandwidth and clone time.
