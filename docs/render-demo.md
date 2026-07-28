# Render Demo Deployment

This guide creates a public online demo of LABhub on Render.

The demo uses SQLite and Render's free web service plan. This is good for trying the app in a browser, but it is not a production setup. Demo data can disappear when the service restarts, redeploys, or the filesystem is reset.

## What Is Already Configured

The repository includes `render.yaml`, a Render Blueprint file. It defines:

- a Python web service named `labhub-demo`
- the free Render service plan
- `pip install -r requirements.txt` as the build command
- `python scripts/init_db.py && waitress-serve --host=0.0.0.0 --port=$PORT wsgi:app` as the start command
- an automatically generated `LABHUB_SECRET_KEY`
- a local SQLite database for demo use

## Step 1: Create Or Log In To Render

Go to [Render](https://render.com/) and sign in.

Connect your GitHub account if Render asks for GitHub access.

## Step 2: Create A Blueprint

1. In the Render dashboard, click **New**.
2. Choose **Blueprint**.
3. Select the GitHub repository `OndrejW/LABhub`.
4. Keep the branch as `main`.
5. Confirm that Render detected `render.yaml`.
6. Click **Apply** or **Deploy Blueprint**.

Render will create a web service named `labhub-demo`.

## Step 3: Wait For The First Deploy

The first build installs Python dependencies and starts the app. The deploy log should show:

```text
LABhub database schema and runtime directories are ready.
```

When deployment is done, Render gives you a public URL similar to:

```text
https://labhub-demo.onrender.com
```

## Step 4: Try The App

Open the Render URL.

1. Register a test user.
2. Log in.
3. Create a setup.
4. Create a sample.
5. Create a project.
6. Create a session.
7. Add a log or note.

## Demo Limitations

- Free Render web services can spin down when idle.
- SQLite and uploaded files are stored on the service filesystem.
- On the free plan, this filesystem should be treated as temporary.
- Use the demo for presentation and testing, not real lab records.

For persistent demo data, upgrade the Render service and add a persistent disk, or move the database and uploaded files to managed storage.

## Manual Render Settings

If you create a normal Render web service instead of a Blueprint, use:

- **Runtime:** Python
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `python scripts/init_db.py && waitress-serve --host=0.0.0.0 --port=$PORT wsgi:app`
- **Environment variables:**
  - `PYTHON_VERSION=3.10.14`
  - `LABHUB_SECRET_KEY`: generate a secret value
  - `LABHUB_DATABASE_URI=sqlite:///site.db`
  - `LABHUB_LOG_FILE=logs/error.log`
