# API reference

Base path: `/api`. All requests and responses are JSON unless stated otherwise.

## Conventions

**Success envelope**

```json
{ "success": true, "data": { } }
```

**Error envelope**

```json
{
  "success": false,
  "error": { "code": "VALIDATION_ERROR", "message": "Human-readable message.", "details": {} }
}
```

| Status | `error.code` | Meaning |
|---|---|---|
| 400 | `BAD_REQUEST` | Malformed request |
| 401 | `UNAUTHORIZED` | Not logged in |
| 403 | `FORBIDDEN` | Logged in but the role does not allow this |
| 404 | `NOT_FOUND` | Unknown route or resource |
| 405 | `METHOD_NOT_ALLOWED` | Route exists but not for this HTTP method |
| 409 | `CONFLICT` | State conflict (e.g. deleting a document used by a session) |
| 413 | `PAYLOAD_TOO_LARGE` | Request or file too large |
| 422 | `VALIDATION_ERROR` | Well-formed but invalid input; `details` lists field errors |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unexpected error (generic message; details are only in server logs) |
| 503 | `SERVICE_UNAVAILABLE` | A dependency (database, Redis) is unavailable |

List endpoints are paginated with `?page=` and `?per_page=`.

---

## Health

### `GET /api/health`

Public. Reports whether the API can reach PostgreSQL and Redis.

**200 OK**

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "version": "0.1.0",
    "checks": { "database": "ok", "redis": "ok" }
  }
}
```

**503 Service Unavailable** — at least one dependency is unreachable:

```json
{
  "success": false,
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "One or more backend services are unavailable.",
    "details": {
      "version": "0.1.0",
      "checks": { "database": "ok", "redis": "unavailable" }
    }
  }
}
```
