# Deployment — Brand3 web app on Fly.io

Target: <https://brand3.fly.dev>. Region `mad`. Single 1-GB machine with a
persistent volume at `/data` and continuous Litestream replication to an
S3-compatible bucket (Cloudflare R2 recommended).

---

## 1. One-time setup

### 1.1 Cloudflare R2 bucket (or any S3-compatible)

Create a bucket named `brand3-prod` and an API token with read/write on it.
Record the four values:

```
LITESTREAM_BUCKET=brand3-prod
LITESTREAM_ENDPOINT=https://<your-account>.r2.cloudflarestorage.com
LITESTREAM_ACCESS_KEY_ID=…
LITESTREAM_SECRET_ACCESS_KEY=…
```

### 1.2 Fly.io app + volume

```bash
fly apps create brand3
fly volumes create brand3_data --region mad --size 1
```

### 1.3 Secrets

```bash
fly secrets set \
  BRAND3_COOKIE_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  BRAND3_TEAM_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(16))')" \
  BRAND3_LLM_API_KEY="<google-ai-studio-key>" \
  EXA_API_KEY="<exa-key>" \
  FIRECRAWL_API_KEY="<firecrawl-key>" \
  LITESTREAM_BUCKET="brand3-prod" \
  LITESTREAM_ENDPOINT="https://<account>.r2.cloudflarestorage.com" \
  LITESTREAM_ACCESS_KEY_ID="…" \
  LITESTREAM_SECRET_ACCESS_KEY="…"
```

Keep `BRAND3_TEAM_TOKEN` somewhere safe — it's the URL parameter that grants
FLOC team unlimited access via `/team/unlock?token=…`.

### 1.4 First deploy

```bash
fly deploy
```

Subsequent deploys: same command. Zero-downtime rolling deploy on a single
machine is **not** supported — the machine restarts, ongoing analyses get
reset to `queued` by `AnalysisQueue.restart_in_flight` and re-processed.

---

## 2. Post-deploy verification

- [ ] `curl https://brand3.fly.dev/` returns 200 with the form.
- [ ] `fly logs` shows the uvicorn banner and `brand3.web starting` line.
- [ ] `fly logs | grep litestream` shows a replication heartbeat (or a
      `snapshot written` line within 1 min).
- [ ] `curl -X POST https://brand3.fly.dev/analyze -d "url=https://example.com"`
      returns 303 and a `/r/<token>/status` location.
- [ ] Wait ~2 min, open the report URL, verify it renders with the footer
      disclaimer and a `/takedown` link.
- [ ] `/team/unlock?token=<BRAND3_TEAM_TOKEN>` sets a cookie and redirects to
      `/`; the 6th analysis from the same IP within 24h returns 429
      **without** the cookie, 303 **with** it.
- [ ] `fly machine restart` and verify the last analysis is still readable
      (`/r/<token>` returns 200) — proves the volume persists.
- [ ] Delete the volume (`fly volumes destroy brand3_data --yes`), create it
      again, and redeploy. The entrypoint should restore from Litestream
      before uvicorn binds — verify the previous reports are still there.

---

## 3. Useful operations

```bash
fly logs                               # stream logs
fly ssh console                        # shell into the machine
fly ssh console -C "sqlite3 /data/brand3.sqlite3 'SELECT COUNT(*) FROM web_requests'"
fly secrets list
fly volumes list
fly machine list
fly status
fly deploy --strategy immediate        # redeploy without rolling
```

To inspect Litestream state remotely:

```bash
fly ssh console -C "litestream snapshots /data/brand3.sqlite3"
fly ssh console -C "litestream generations /data/brand3.sqlite3"
```

---

## 4. Rollback and recovery

Revert to a previous release:

```bash
fly releases
fly deploy --image <previous-image-digest>
```

Restore DB from replica (when live DB is corrupt):

```bash
fly ssh console
mv /data/brand3.sqlite3 /data/brand3.sqlite3.bak
litestream restore -config /app/litestream.yml /data/brand3.sqlite3
# exit; the next request triggers a reconnect
```

---

## 5. Known caveats

- Single machine means single point of failure. For the Sprint 2 volume
  (<100 analyses/day) this is fine; scaling out requires migrating to
  Postgres (the `web_requests` SQL is standard, the engine's
  `sqlite_store.py` is the only place tightly coupled to SQLite).
- `auto_stop_machines = "off"` because the background worker must not be
  killed mid-analysis. Cold-start reduction via `scale to zero` would
  require externalizing the queue (Celery/RQ).
- The rate-limit counter lives in `web_requests`; when an analysis row
  is deleted the counter drops — intentional, because takedowns should
  not penalize the requester IP.
- Litestream replicates the DB **file**, not logical rows. If the volume
  is corrupted mid-WAL, restore recovers up to the last successful
  snapshot plus all applied WAL frames — typically a few seconds of loss.
