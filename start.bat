@echo off
set FLASK_APP=runserver.py
set FLASK_ENV=development
flask run --port=5000 --host=127.0.0.1
