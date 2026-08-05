# Calculations App

A FastAPI web application for user registration, JWT-based authentication, and performing/storing arithmetic calculations. Includes a server-rendered HTML frontend (Jinja2 + Tailwind) alongside the JSON API, backed by PostgreSQL via SQLAlchemy.

## Features

- **User accounts** — registration, login (JSON and OAuth2 form flows), password hashing with bcrypt
- **JWT authentication** — access/refresh tokens, protected API routes
- **Calculations** — addition, subtraction, multiplication, division, full CRUD scoped to the logged-in user
- **Web UI** — login, registration, dashboard, and per-calculation view/edit pages
- **Dockerized** — app, PostgreSQL, and pgAdmin via `docker-compose`

## BREAD Endpoints for Calculations

The core of the API is a full BREAD (Browse, Read, Edit, Add, Delete) interface for calculations, defined in [app/main.py](app/main.py). Every route below requires a valid access token and only ever operates on calculations owned by the authenticated user.

| Operation | Method & Path | Description |
|---|---|---|
| **Browse** | `GET /calculations` | Retrieve and display all calculations belonging to the logged-in user. |
| **Read** | `GET /calculations/{id}` | Retrieve details of a specific calculation by its ID. |
| **Edit** | `PUT /calculations/{id}` | Update the inputs of an existing calculation; the result is recomputed automatically. |
| **Add** | `POST /calculations` | Create a new calculation by specifying the operation `type` (`addition`, `subtraction`, `multiplication`, `division`) and a list of numeric `inputs`. The result is computed server-side. |
| **Delete** | `DELETE /calculations/{id}` | Remove a calculation by its ID. |

Example — creating a calculation:

```bash
curl -X POST http://localhost:8000/calculations \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"type": "addition", "inputs": [10.5, 3, 2]}'
```

### Screenshots

<!--
  Drop screenshots into docs/screenshots/ using the filenames below and
  they'll show up here automatically. One screenshot per BREAD operation,
  showing it working end-to-end (e.g. the dashboard UI and/or the Swagger
  UI response) is enough.
-->

| Operation | Screenshot |
|---|---|
| **Browse** | ![Browse calculations](docs/screenshots/bread-browse.png) |
| **Read** | ![Read a calculation](docs/screenshots/bread-read.png) |
| **Edit** | ![Edit a calculation](docs/screenshots/bread-edit.png) |
| **Add** | ![Add a calculation](docs/screenshots/bread-add.png) |
| **Delete** | ![Delete a calculation](docs/screenshots/bread-delete.png) |

## Other Endpoints

| Method & Path | Purpose |
|---|---|
| `GET /health` | Health check |
| `POST /auth/register` | Create a new user account |
| `POST /auth/login` | Log in with a JSON `{username, password}` payload; returns access + refresh tokens |
| `POST /auth/token` | Log in with an OAuth2 form payload (used by the Swagger UI's "Authorize" button) |
| `GET /`, `/login`, `/register`, `/dashboard`, `/dashboard/view/{id}`, `/dashboard/edit/{id}` | Server-rendered HTML pages |

Interactive API docs (Swagger UI) are available at `/docs` once the app is running.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic v2
- **Database**: PostgreSQL 17
- **Auth**: python-jose (JWT), passlib/bcrypt (password hashing)
- **Frontend**: Jinja2 templates, Tailwind CSS
- **Testing**: pytest, pytest-cov, Playwright (browser e2e tests)

## Project Structure

```
app/
  main.py              # FastAPI app, routes (web + API)
  database.py           # Engine/session setup, get_db dependency
  database_init.py      # Standalone table creation/drop script
  conftest.py            # Shared pytest fixtures (registered as a plugin)
  auth/
    jwt.py                # Token creation/decoding, password hashing
    dependencies.py       # get_current_user / get_current_active_user
    redis.py              # Token-blacklist helpers
  core/
    config.py             # Settings (env-driven)
  models/
    user.py               # User ORM model
    calculation.py         # Calculation ORM model (polymorphic by type)
  schemas/
    user.py, calculation.py, token.py   # Pydantic request/response schemas
templates/               # Jinja2 HTML pages
static/                  # CSS/JS assets
tests/
  unit/
  integration/            # Model, schema, auth, and route tests
  e2e/                     # Full-stack tests against a live server + browser
```

## Getting Started (Docker)

The simplest way to run everything (app + PostgreSQL + pgAdmin):

```bash
docker compose up --build
```

- App: http://localhost:8000 (docs at `/docs`)
- pgAdmin: http://localhost:5050 (login: `admin@example.com` / `admin`)
- PostgreSQL: `localhost:5432` (user/password: `postgres`/`postgres`)

`docker-compose.yml` sets sensible defaults for all required environment variables (JWT secrets, database URLs, etc.) for local development — **do not reuse these values in production.**

## Getting Started (Local)

Requires Python 3.14 and a running PostgreSQL instance (the `db` service from `docker compose up db` works fine).

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install               # only needed for the e2e/browser tests
```

Set the environment variables below (or create a `.env` file — see [app/core/config.py](app/core/config.py)), then run:

```bash
uvicorn app.main:app --reload
```

### Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/fastapi_db` | Main app database |
| `TEST_DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/fastapi_test_db` | Database used by the test suite |
| `JWT_SECRET_KEY` / `JWT_REFRESH_SECRET_KEY` | dev placeholders | Signing keys for access/refresh tokens — **must** be overridden outside local dev |
| `ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `BCRYPT_ROUNDS` | `12` | Password hashing cost factor |
| `REDIS_URL` | `redis://localhost:6379/0` | Used by the (currently unused) token-blacklist helpers |

## Running Tests

```bash
pytest                      # full suite, with coverage (see pytest.ini)
pytest --run-slow            # also run tests marked @pytest.mark.slow
pytest -m e2e                 # only the browser/e2e suite
pytest tests/integration/    # a single test tier
```

Coverage reports print to the terminal and are written to `htmlcov/` (open `htmlcov/index.html`). The e2e suite spins up a real `uvicorn` server and a headless Chromium browser via Playwright, and needs a reachable PostgreSQL instance at `TEST_DATABASE_URL`.

## CI/CD

[.github/workflows/test.yml](.github/workflows/test.yml) runs the test suite and a Trivy vulnerability scan on every push/PR to `main`, and builds/pushes the Docker image to Docker Hub on `main`.

<!-- Drop screenshots into docs/screenshots/ using the filenames below. -->

| | Screenshot |
|---|---|
| **Successful GitHub Actions run** | ![Successful GitHub Actions run](docs/screenshots/github-actions-run.png) |
| **Docker Hub deployment** | ![Docker Hub deployment](docs/screenshots/dockerhub-deployment.png) |

## License

MIT — see [LICENSE](LICENSE).
