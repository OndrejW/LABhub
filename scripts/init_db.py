import os
import sys
from pathlib import Path

# Make this script runnable from the repository root and from its scripts folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from labhub import app, db


RUNTIME_DIRS = [
    "logs",
    os.path.join("labhub", "static", "profile_pics"),
    os.path.join("labhub", "static", "log"),
    os.path.join("labhub", "static", "setup"),
    os.path.join("labhub", "static", "sample"),
]


def main():
    for path in RUNTIME_DIRS:
        os.makedirs(path, exist_ok=True)

    with app.app_context():
        db.create_all()

    print("LABhub database schema and runtime directories are ready.")


if __name__ == "__main__":
    main()
