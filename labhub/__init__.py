#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import collections
import collections.abc
from datetime import timedelta

if not hasattr(collections, 'MutableMapping'):
    collections.MutableMapping = collections.abc.MutableMapping

from flask import Flask, request, session
from flask import send_file
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, login_user
from flask_sqlalchemy import SQLAlchemy
from flask_whooshee import Whooshee
from flask_nav import register_renderer
from flask_jsglue import JSGlue
from flask_qrcode import QRcode
from flask_googlecharts import GoogleCharts
import pkg_resources

from labhub.navigation import nav, TopMenuRenderer, RightMenuRenderer

import logging


def serve_googlecharts_init():
    chart_script = pkg_resources.resource_stream("flask_googlecharts", "static/charts.init.js")
    try:
        return send_file(chart_script, download_name="charts.init.js", mimetype="application/javascript")
    except TypeError:
        return send_file(chart_script, attachment_filename="charts.init.js", mimetype="application/javascript")


# Flask-GoogleCharts still uses Flask's removed attachment_filename argument.
GoogleCharts._get_static_init = staticmethod(serve_googlecharts_init)

SESSIONLIFETIME = timedelta(minutes=60)
os.makedirs('logs', exist_ok=True)
logging.basicConfig(filename=os.environ.get('LABHUB_LOG_FILE', 'logs/error.log'),level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get('LABHUB_SECRET_KEY', 'dev-only-change-me')
app.permanent_session_lifetime = SESSIONLIFETIME
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('LABHUB_DATABASE_URI', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['LABHUB_AUTO_LOGIN_DEMO'] = os.environ.get('LABHUB_AUTO_LOGIN_DEMO', '').lower() in {'1', 'true', 'yes'}
app.config['LABHUB_DEMO_EMAIL'] = os.environ.get('LABHUB_DEMO_EMAIL', 'demo@labhub.example')
db = SQLAlchemy(app)
whooshee = Whooshee(app)
bcrypt = Bcrypt(app)
charts = GoogleCharts(app)

register_renderer(app, 'top_menu_renderer', TopMenuRenderer)
register_renderer(app, 'right_menu_renderer', RightMenuRenderer)

jsglue = JSGlue(app)

QRcode(app)

nav.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = 'info'


@app.before_request
def auto_login_demo_user():
    if request.endpoint == 'static' or current_user.is_authenticated or not app.config['LABHUB_AUTO_LOGIN_DEMO']:
        return

    from labhub.lib.models import User

    demo_user = User.query.filter_by(email=app.config['LABHUB_DEMO_EMAIL']).first()
    if demo_user:
        login_user(demo_user)


import labhub.routes

@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = SESSIONLIFETIME
