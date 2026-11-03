# DevPilot AI

DevPilot AI is a Gemini-powered coding-agent application with a React/Vite frontend and a FastAPI backend. The current stabilization phase provides a reproducible local setup and a loopback-only Docker deployment.

## Current capabilities

- Project, conversation, file, download, and Gemini-status APIs
- SQLite persistence through SQLAlchemy
- React dashboard with Monaco editor integration
- Configurable Gemini model and server-side API key loading
- Dockerized frontend-to-backend reverse proxy

Project command execution is intentionally disabled. A future phase will add a dedicated restricted Docker sandbox; DevPilot AI never runs agent-provided commands on the backend host.

## Configuration

Copy the appropriate example file without committing the resulting `.env` file.

```sh
cp .env.example .env
cp backend/.env.example backend/.env
```

Set a real value for `GEMINI_API_KEY` only in your local environment or secure environment settings. Keep API keys, passwords, and generated databases out of Git.

The frontend uses relative `/api` paths by default. During Vite development, its proxy forwards requests to `http://127.0.0.1:8000`. Set `VITE_BACKEND_URL` only when that backend address differs.

## Local development

Use Python 3.12 and a current Node.js LTS release.

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
.venv/bin/uvicorn app.main:app --app-dir backend --reload
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

The Vite server listens on `127.0.0.1:5173`; it is intentionally not configured for public binding.

## Docker deployment

Docker Compose builds the Vite frontend into Nginx and proxies `/api` requests to the private backend service. Only the frontend is published, and it is bound to the local machine:

```sh
docker compose up --build
```

Open `http://127.0.0.1:5173`. The backend has no host port mapping. Its SQLite database and project workspace live in the named `devpilot_data` volume.

The backend's former static HTML dashboard remains in the source tree for reference but is no longer served. The Vite frontend is the single supported delivery path.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider
cd frontend && npm run build
docker compose config
```

The current backend test suite covers Gemini configuration behavior plus filesystem-containment and disabled-execution safeguards. It does not make a live Gemini request unless a valid key is configured.

## Dependency locks

- `backend/requirements.lock` pins Python application and test dependencies.
- `frontend/package-lock.json` pins Node dependencies. Use `npm ci`, not `npm install`, for reproducible installs.

## Security status

The next phases must add authentication, project ownership checks, database migrations, and the restricted execution sandbox before any public deployment. Do not expose the current application to untrusted users.
