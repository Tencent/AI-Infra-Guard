# Data Auto-Sync API

> **Base URL**: `http://<host>:8088/api/v1`
>
> All endpoints require the same authentication as the rest of the AIG API
> (session cookie / `X-Token` header set during login).

---

## Overview

AIG's detection rules live in the `data/` directory on disk:

| Sub-directory | Contents |
|---|---|
| `data/fingerprints/` | YAML fingerprint rules for AI components |
| `data/vuln/` | Chinese CVE/GHSA vulnerability rules |
| `data/vuln_en/` | English CVE/GHSA vulnerability rules |
| `data/mcp/` | MCP security detection rules |
| `data/eval/` | Jailbreak / prompt-security evaluation datasets |
| `data/agents/` | Agent scan configuration |

The **data auto-sync** feature lets you pull the latest rules from the
official GitHub repository (`Tencent/AI-Infra-Guard`) without restarting
the server or rebuilding the Docker image.

---

## Endpoints

### POST `/api/v1/system/update-data`

Trigger an asynchronous sync of the `data/` directory from GitHub.

Only **one sync** can run at a time. If a sync is already in progress the
endpoint returns `200 OK` with the current status instead of starting a new
one.

#### Request Body (JSON, optional)

| Field | Type | Default | Description |
|---|---|---|---|
| `ref` | `string` | `"main"` | Branch name or tag to sync from |
| `is_tag` | `bool` | `false` | Set `true` when `ref` is a Git tag (e.g. `"v4.1.3"`) |
| `github_token` | `string` | `""` | Personal access token — avoids GitHub's anonymous rate limit (60 req/h) |
| `dirs` | `string` | `"fingerprints,vuln,vuln_en,mcp,eval,agents"` | Comma-separated list of `data/` sub-directories to sync |

#### Response — `202 Accepted` (sync started) or `200 OK` (already running)

```json
{
  "running": true,
  "started_at": "2026-04-10T17:20:00Z",
  "finished_at": null,
  "message": "downloading archive from GitHub…",
  "files_updated": 0,
  "ref": "main"
}
```

#### Examples

**Sync latest `main` (anonymous)**
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

**Sync only vulnerability rules (authenticated)**
```bash
curl -X POST http://localhost:8088/api/v1/system/update-data \
  -H "Content-Type: application/json" \
  -d '{
    "ref": "main",
    "github_token": "ghp_xxxxxxxxxxxx",
    "dirs": "vuln,vuln_en"
  }'
```

---

### GET `/api/v1/system/update-status`

Return the status of the current (or most recent) sync operation.

#### Response — `200 OK`

```json
{
  "running": false,
  "success": true,
  "started_at": "2026-04-10T17:20:00Z",
  "finished_at": "2026-04-10T17:20:42Z",
  "message": "sync complete — 312 file(s) updated from ref \"main\"",
  "files_updated": 312,
  "ref": "main"
}
```

#### Response Fields

| Field | Type | Description |
|---|---|---|
| `running` | `bool` | `true` while a sync is in progress |
| `success` | `bool \| null` | `true` = completed OK, `false` = error, `null` = never run |
| `started_at` | `string (RFC3339)` | When the current/last sync started |
| `finished_at` | `string (RFC3339) \| null` | When it finished; `null` if still running |
| `message` | `string` | Human-readable status/error description |
| `files_updated` | `int` | Number of files written to disk |
| `ref` | `string` | Branch or tag used |

#### Example — poll until done
```bash
while true; do
  STATUS=$(curl -s http://localhost:8088/api/v1/system/update-status)
  echo "$STATUS"
  RUNNING=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['running'])")
  [ "$RUNNING" = "False" ] && break
  sleep 3
done
```

---

## Workflow

```
Client                          AIG Server                    GitHub
  |                                 |                            |
  |-- POST /system/update-data ---> |                            |
  |<-- 202 Accepted (running=true)  |                            |
  |                                 |-- GET codeload.github.com -->|
  |                                 |<-- zip archive --------------|
  |                                 | (unzip + overwrite data/)   |
  |                                 |                            |
  |-- GET /system/update-status --> |                            |
  |<-- 200 OK (running=false,       |                            |
  |            success=true)        |                            |
```

---

## Error Cases

| Scenario | `success` | `message` example |
|---|---|---|
| GitHub unreachable / timeout | `false` | `"download failed: Get … context deadline exceeded"` |
| Invalid ref / 404 | `false` | `"download failed: HTTP 404 from …"` |
| Disk write error | `false` | `"extraction failed: write data/vuln/…: permission denied"` |
| Rate limited (anonymous) | `false` | `"download failed: HTTP 429 from …"` — use `github_token` |

---

## Notes

- The sync **overwrites** matching files in `data/` but does **not delete** files that no longer exist in the upstream repo. To do a full clean sync, remove the `data/` sub-directories manually before triggering the update.
- The server does **not** need to restart after a sync — rule files are read from disk at scan time.
- In-progress scans are not interrupted; they will use the new rules on the next run.
- The `github_token` field value is **never logged or stored**.
