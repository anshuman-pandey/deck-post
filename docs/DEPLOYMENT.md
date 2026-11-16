# Persistent local preview

Docker Engine and Docker Compose are required. From this checkout:

```sh
python3 scripts/setup.py
docker compose up --build -d
```

Open http://127.0.0.1:8099. Read the owner key from your private `.env` locally and enter it in the workspace. Setup creates mode-0600 configuration and refuses to overwrite it. Never commit or share this file. The service runs with Waitress as UID 10001, a read-only root filesystem, no Linux capabilities and a writable named data volume. The port is bound only to localhost. `docker compose down` retains PDFs; **do not use `down -v` unless you intend to delete them**.

This is a local deployment preview. Public hosting requires a trusted HTTPS reverse proxy, operational monitoring, protected backups and actual public-path testing; that acceptance is pending. No HTTPS or hosted demo is included.

## Backup and restore

The database contains original PDF bytes, link credential hashes, expiry/revocation state and retrieval events. Protect it as private data. Preserve `.env` separately to retain owner access. Never publish either file.

Stop the service for a simple consistent copy:

```sh
docker compose stop deck-post
docker compose cp deck-post:/data/deck.sqlite3 /tmp/deck-source.sqlite3
python3 scripts/backup.py /tmp/deck-source.sqlite3 ./deck-backup.sqlite3
rm /tmp/deck-source.sqlite3
docker compose start deck-post
```

The backup utility uses SQLite's backup API, verifies integrity and refuses to overwrite an existing destination. It also supports a live SQLite source when used directly on the host. Keep dated backups outside the checkout.

To restore, use a **separate clean checkout/Compose project** and private `.env`. Start it once to create its volume, then stop it. Restore into this new project, leaving the original volume intact:

```sh
docker compose up -d
docker compose stop deck-post
docker compose cp ./deck-backup.sqlite3 deck-post:/data/deck.sqlite3
docker compose run --rm --user 0 deck-post python -c "import os; os.chown('/data/deck.sqlite3',10001,10001); os.chmod('/data/deck.sqlite3',0o600)"
docker compose start deck-post
```

Verify existing links, counts and revocations before routing any users to the restored instance. Restoring an older backup rolls back revocations and counters made after that backup; reconcile those changes before use. Expiry remains evaluated against the current server clock.

## Reproduce container acceptance

```sh
docker build -t deck-post-acceptance:local .
python3 scripts/container_acceptance.py
```

The host Python needs the requirements installed. The test creates isolated disposable containers/volumes, checks exact PDF downloads and retrieval counts, revokes one link and expires another, restarts, restores into a clean volume, and verifies new link/revoke operations after recovery. It removes its own containers/volumes afterward. If your environment uses a private CA, pass its certificate as the optional `pip_ca` build secret; keep TLS verification enabled.
