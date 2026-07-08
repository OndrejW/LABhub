# Developer Guide

## Project Layout

- `runserver.py`: development entrypoint.
- `wsgi.py`: WSGI entrypoint for production servers.
- `labhub/__init__.py`: Flask app, extensions, config, login manager.
- `labhub/routes.py`: route handlers and application workflows.
- `labhub/lib/models.py`: SQLAlchemy models.
- `labhub/lib/forms.py`: WTForms form classes.
- `labhub/navigation.py`: top navigation.
- `labhub/templates`: Jinja templates.
- `labhub/static`: CSS, icons, images, JavaScript, and manual diagrams.
- `scripts/init_db.py`: creates runtime directories and database schema.

The old duplicated `labhub/lib/labhub` package copy has been removed from the repository to avoid stale code and duplicate sensitive data.

## Configuration

Configuration is environment-driven:

- `LABHUB_SECRET_KEY`
- `LABHUB_DATABASE_URI`
- `LABHUB_LOG_FILE`

Keep local configuration in `.env` or in the service manager, not in tracked files.

## Database

Models live in `labhub/lib/models.py`. There is no migration system checked in yet, even though `alembic.ini` exists. Until migrations are added, schema creation is done by:

```powershell
python scripts/init_db.py
```

Before making schema changes, add a real Alembic migration directory and document upgrade and rollback commands.

## Routes To Know

- `/`, `/index/`: authenticated home/search page.
- `/login`, `/register/`, `/logout/`, `/account`: account flow.
- `/addLog/`, `/log/<id>`, `/log/<id>/update`: measurement logs.
- `/addOccasion/`: notes.
- `/addAnalysis/`: analyses.
- `/addProject/`, `/project/<id>`: projects.
- `/addSession/`, `/session/<id>`: sessions.
- `/addSample/`, `/sample/<id>`: samples.
- `/addStructure/`, `/structure/<id>`: structures.
- `/addSetup/`, `/setup/<id>`: setups.
- `/addDrawer/`, `/drawer/<id>`: sample storage drawers.
## Compatibility Notes

The app uses older Flask/WTForms patterns such as `TextField` and `wtforms.ext.sqlalchemy.fields.QuerySelectField`. Dependency upgrades should be tested as code changes, not treated as simple version bumps.

## Frontend Assets

The base template loads Bootstrap, jQuery, Popper, Lightbox, and Google Charts from CDNs. Production deployments should either pin and validate those URLs or vendor the assets locally.
