import os

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
