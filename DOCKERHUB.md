# Calculations App

A FastAPI web app for user auth (JWT) and performing/storing arithmetic calculations, with a full BREAD (Browse, Read, Edit, Add, Delete) API plus a server-rendered HTML frontend.

Source & full docs: https://github.com/otkamal/is601-assignment14

## Quick Start

Requires a reachable PostgreSQL instance.

```bash
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/fastapi_db \
  -e JWT_SECRET_KEY=change-me \
  -e JWT_REFRESH_SECRET_KEY=change-me-too \
  otkamal/mod14-assignment:latest
```

Then visit `http://localhost:8000` (API docs at `/docs`, health check at `/health`).

## Environment Variables

| Variable | Default | Required |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/fastapi_db` | Yes, in most setups |
| `JWT_SECRET_KEY` / `JWT_REFRESH_SECRET_KEY` | dev placeholders | **Yes** — override outside local dev |
| `ALGORITHM` | `HS256` | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | No |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | No |
| `BCRYPT_ROUNDS` | `12` | No |

## Tags

| Tag | Description |
|---|---|
| `latest` | Latest build from `main` |
| `<git-sha>` | Immutable build for a specific commit |

## Notes

- Exposes port `8000`; built-in `HEALTHCHECK` against `GET /health`.
- Runs as a non-root user.
- On startup, creates database tables if they don't exist yet (no migration tool — schema changes require a fresh database or manual migration).
