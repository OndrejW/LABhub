# Operations Checklist

Use this checklist before handing a LABhub deployment to another group.

## Before First Start

- [ ] Create a virtual environment.
- [ ] Install `requirements.txt`.
- [ ] Create `.env` or service-manager environment variables.
- [ ] Generate a unique `LABHUB_SECRET_KEY`.
- [ ] Set `LABHUB_DATABASE_URI`.
- [ ] Run `python scripts/init_db.py`.
- [ ] Confirm runtime folders exist.
- [ ] Confirm CDN access or vendor frontend assets.

## Security

- [ ] No real `.env` files or database files are tracked.
- [ ] Production secrets are stored outside the repository.
- [ ] Production runs behind TLS.
- [ ] Registration policy is documented.
- [ ] Backups are access-controlled.

## Functional Smoke Test

- [ ] Register a test user.
- [ ] Log in.
- [ ] Create a project.
- [ ] Create a session.
- [ ] Create a setup with attributes.
- [ ] Create a sample and structure.
- [ ] Add a log with an image.
- [ ] Add a note.
- [ ] Add an analysis.
- [ ] Search/filter logs.
- [ ] Add a remark.

## Backup And Restore

- [ ] Back up the database.
- [ ] Back up uploaded files.
- [ ] Document retention.
- [ ] Restore into a test environment.
- [ ] Record the restore result and date.
