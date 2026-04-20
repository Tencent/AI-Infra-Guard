# Data Auto-Sync API

## Overview

AIG detects AI infrastructure vulnerabilities using rule files in the `data/` directory. The **Data Auto-Sync** API allows you to pull the latest rules from the official GitHub repository (`Tencent/AI-Infra-Guard`) without restarting the server or rebuilding the Docker image.

- **Base URL**: `http://localhost:8088` (adjust to your deployment address)
- **Authentication**: No authentication required

The sync is performed by cloning the `main` branch into a temporary directory using `git clone --depth 1`, then copying all `data/` sub-directories into the working directory. No GitHub token is needed.

---

## API Endpoints

### 1. Trigger Data Sync

#### Endpoint Info

| Item | Value |
|---|---|
| URL | `/api/v1/system/update-data` |
| Method | `POST` |
| Request Body | Not required |

No request parameters. The sync always pulls from the `main` branch and updates all data directories.

#### Response Fields

| Field | Type | Description |
|---|---|---|
| `running` | bool | Whether a sync is currently in progress |
| `success` | bool | Whether the last sync succeeded (`null` if never run) |
| `started_at` | string | ISO-8601 timestamp when the sync started |
| `finished_at` | string | ISO-8601 timestamp when the sync finished (`null` if still running) |
| `message` | string | Human-readable status message |
| `files_updated` | int | Number of files written to disk |
| `ref` | string | Branch used for this sync (always `"main"`) |

#### Response Codes

| Code | Meaning |
|---|---|
| `202 Accepted` | Sync started successfully |
| `200 OK` | A sync is already running; returns current status |

#### cURL Example

```bash
curl -X POST http://localhost:8088/api/v1/system/update-data
```

#### Example Response (`202 Accepted`)

```json
{
  "running": true,
  "started_at": "2026-04-20T10:00:00Z",
  "message": "cloning repository…",
  "files_updated": 0,
  "ref": "main"
}
```

#### Python Example

```python
import requests
import time

BASE_URL = "http://localhost:8088"

# Trigger sync
resp = requests.post(f"{BASE_URL}/api/v1/system/update-data")
print(resp.json())

# Poll until done
while True:
    status = requests.get(f"{BASE_URL}/api/v1/system/update-status").json()
    print(f"[{status['message']}] files_updated={status['files_updated']}")
    if not status["running"]:
        break
    time.sleep(3)

if status.get("success"):
    print(f"Sync complete — {status['files_updated']} file(s) updated")
else:
    print(f"Sync failed: {status['message']}")
```

---

### 2. Get Sync Status

#### Endpoint Info

| Item | Value |
|---|---|
| URL | `/api/v1/system/update-status` |
| Method | `GET` |

#### Response Fields

Same fields as the trigger endpoint response (see above).

#### cURL Example

```bash
curl http://localhost:8088/api/v1/system/update-status
```

#### Example Response (sync in progress)

```json
{
  "running": true,
  "started_at": "2026-04-20T10:00:00Z",
  "message": "copying data directories…",
  "files_updated": 0,
  "ref": "main"
}
```

#### Example Response (sync complete)

```json
{
  "running": false,
  "success": true,
  "started_at": "2026-04-20T10:00:00Z",
  "finished_at": "2026-04-20T10:00:45Z",
  "message": "sync complete — 312 file(s) updated from ref \"main\"",
  "files_updated": 312,
  "ref": "main"
}
```

#### Example Response (sync failed)

```json
{
  "running": false,
  "success": false,
  "started_at": "2026-04-20T10:00:00Z",
  "finished_at": "2026-04-20T10:00:05Z",
  "message": "git clone failed: exit status 128\nfatal: unable to access 'https://github.com/...'",
  "files_updated": 0,
  "ref": "main"
}
```

---

## Typical Workflow

1. **Trigger sync** — call `POST /api/v1/system/update-data`; returns `202 Accepted` immediately.
2. **Poll for completion** — call `GET /api/v1/system/update-status` until `running` is `false`.
3. **Check result** — inspect `success` and `message`.
4. **No restart needed** — updated rules take effect on the next scan.

## Notes

- Only one sync can run at a time. A concurrent trigger returns the current status with `200 OK`.
- The `git` binary must be available in the server's `PATH`.
- The server must be able to reach `github.com` on port 443.
