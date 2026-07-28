# Deployment Guide

This guide describes the minimum work needed to run LABhub outside the original lab machine.

## 1. Prerequisites

- Python 3.8 or newer is recommended.
- A virtual environment or Conda environment.
- Network access to the JavaScript CDNs used by `labhub/templates/base.html`, unless those assets are vendored later.
- A database location that is backed up. The default is SQLite, but production deployments should choose and document their own storage policy.

## 2. Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On Linux or macOS, activate the environment with `source .venv/bin/activate`.

## 3. Configure

Copy `.env.example` to `.env` for local use and set real values outside version control.

Required:

- `LABHUB_SECRET_KEY`: unique secret for Flask sessions.
- `LABHUB_DATABASE_URI`: SQLAlchemy database URL.

Optional:

- `LABHUB_LOG_FILE`: override the default `logs/error.log`.

Never commit production databases or `.env` files.

## 4. Initialize Database And Runtime Folders

```powershell
python scripts/init_db.py
```

This creates the schema with SQLAlchemy and creates runtime folders for logs, profile pictures, log images, setup files, and sample images.

If you need to migrate existing data, do that as a private, one-time import and document the source, target, and verification steps.

## 5. Run Locally

```powershell
set FLASK_APP=runserver.py
set FLASK_ENV=development
flask run --port=5000 --host=127.0.0.1
```

The included `start.bat` does the same thing for a Windows development machine.

## 6. Production Run

Use a WSGI server instead of Flask's development server. One simple cross-platform option is Waitress:

```powershell
waitress-serve --host=127.0.0.1 --port=8000 wsgi:app
```

Put a reverse proxy in front of it for TLS, compression, request size limits, and access controls. Document the final URL, proxy config, service manager, restart command, and log locations for your deployment.

## 7. Render Demo

For a simple public demo, use the included `render.yaml` Blueprint and follow [Render Demo Deployment](render-demo.md).

The demo configuration uses SQLite on the service filesystem. Treat demo data as temporary unless you add persistent storage.

## 8. Backups

Back up both the database and uploaded files:

- database file or managed database snapshot
- `labhub/static/profile_pics`
- `labhub/static/log`
- `labhub/static/setup`
- `labhub/static/sample`

Backups should have retention, access control, restore testing, and monitoring. The old `backupDB.bat` was tied to a private network share and is not a reusable deployment solution.
