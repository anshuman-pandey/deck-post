# Authenticated local API

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export DECK_OWNER_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export DECK_DATABASE=deck.sqlite3
python server.py
```

Development API listens on `127.0.0.1:8099`. No browser UI or production deployment yet. All keys use `Authorization: Bearer <key>`. Query-string keys are not accepted. Keep the owner key private.

| Route | Access | Behavior |
| --- | --- | --- |
| GET /api/files | Owner | File metadata; excludes PDF bytes |
| POST /api/files | Owner | Multipart `file`; PDF validation and storage |
| POST /api/files/{file}/links | Owner | JSON `expires`: integer UTC epoch seconds, in next 366 days; returns key once |
| GET /api/files/{file}/links | Owner | Expiry, revocation and retrieval counts; no secrets |
| POST /api/files/{file}/links/{link}/revoke | Owner | Revoke future access |
| GET /api/links/{link} | Link key | Filename, hash, page count and expiry |
| GET /api/links/{link}/download | Link key | Full PDF attachment, exact SHA-256 response header |

HEAD validates access without returning file bytes or adding a retrieval. Range requests receive the full attachment (200); partial delivery and conditional caching are not supported. Each accepted GET increments retrieval count before transfer. An interrupted transfer may still be counted; these are not completed-download counts, unique visitors or proof of reading.

Expiry is enforced at authorization, including the exact expiry instant. A transfer authorized before expiry/revocation may finish. Copies already saved cannot be revoked. PDFs are structurally checked but not sanitized or malware-scanned.

Denied access returns 401; invalid input 400; oversized requests 413; invalid content types 415; storage unavailability 503. Errors are JSON. No CORS is enabled; responses disable caching and framing. Tests use Flask's HTTP client; actual browser and deployment acceptance remain pending.
