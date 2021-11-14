set FLASK_APP=runserver.py
set FLASK_ENV=development
pg_ctl -D database -l logs/dbLog.log start
flask run --port=80 --host=0.0.0.0