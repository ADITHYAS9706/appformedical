# Deploying Medical Timeline

## Local
```bash
cp .env.example .env        # set POSTGRES_PASSWORD and an LLM API key
docker compose up --build   # UI: http://localhost:8080   API docs: http://localhost:8000/docs
```
The override file publishes the DB (5432) and API (8000) on localhost only.

## Cloud / production
```bash
docker compose -f docker-compose.yml up -d --build   # ignores the local override
```
- Only the frontend (nginx, port 8080) is published. Put a TLS-terminating load balancer or reverse proxy (ALB, Cloudflare, Caddy, Traefik) in front of it; do not serve PHI over plain HTTP.
- Managed Postgres: set `DATABASE_URL` in `.env` (the bundled `db` service can then be dropped).
- Inject secrets (`POSTGRES_PASSWORD`, API keys) from your platform's secret manager rather than a file on disk.
- Building images separately: `docker build -t timeline-api ./backend`, `docker build -t timeline-web ./frontend`.

## Before real patient data
- Replace `create_all` with Alembic migrations; back up the `pgdata` volume.
- Add authentication and audit logging; sign a BAA / zero-retention agreement with your LLM vendor (or de-identify text first).
- Commit `frontend/package-lock.json` so builds are reproducible (`npm install` once locally).
- Uploaded files live in the `uploads` volume only until processing succeeds; move to object storage if you need retention.
