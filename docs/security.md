# Security Notes

LABhub was originally built around a specific lab environment. Public or shared deployment requires cleaning up local assumptions.

## Secrets

The application reads deploy-time configuration from environment variables. Do not add secrets to source control.

## Data

SQLite databases that contain real users, logs, remarks, paths, or images are private operational data. They should not be committed to the public repository. Use private migration or import processes when historical data is required.

## Authentication And Registration

The app supports public self-registration at the route level. Deployers must decide whether that is acceptable, whether the app is network-restricted, and whether an approval/admin workflow is needed.

## Uploads

Uploaded images and files are stored under `labhub/static`. Production deployments should document allowed file types, maximum request size, malware scanning policy if needed, and backup coverage.

## External Services

Do not add external-service integrations until the data flow is approved for the deployment environment.

## Hardening Settings

| Variable | Default | Purpose |
|---|---|---|
| `LABHUB_SECRET_KEY` | random per process | Must be set in production; without it sessions reset on every restart. |
| `LABHUB_SECURE_COOKIES` | `false` | Set to `true` behind HTTPS so session and remember-me cookies are marked `Secure`. |
| `LABHUB_MAX_UPLOAD_MB` | `32` | Requests larger than this are rejected with HTTP 413. |
| `LABHUB_LOG_LEVEL` | `INFO` | Avoid `DEBUG` in production; it can log request data. |
| `LABHUB_DEBUG` | `false` | Enables the Werkzeug debugger for `runserver.py`. Never enable it on a reachable host. |

Destructive AJAX actions (deleting log images and remarks) accept `POST` only and require the `X-CSRFToken` header. Only the log's operator or a cooperator can delete its images.

## Dependency Audits

Run `pip-audit -r requirements.txt` before each deployment. As of October 2026, Werkzeug (<3.1.9) and Flask (<3.1.3) still have open advisories that require the Flask 3 migration; setuptools stays pinned below 81 because Flask-GoogleCharts relies on `pkg_resources`. Pillow 13 requires Python 3.11 or newer.
