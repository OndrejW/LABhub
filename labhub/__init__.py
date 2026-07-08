#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from datetime import timedelta

from flask import Flask, session
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_whooshee import Whooshee
from flask_nav import register_renderer
from flask_jsglue import JSGlue
from flask_qrcode import QRcode
from flask_googlecharts import GoogleCharts

from labhub.navigation import nav, TopMenuRenderer, RightMenuRenderer

import logging

SESSIONLIFETIME = timedelta(minutes=60)
os.makedirs('logs', exist_ok=True)
logging.basicConfig(filename=os.environ.get('LABHUB_LOG_FILE', 'logs/error.log'),level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get('LABHUB_SECRET_KEY', 'dev-only-change-me')
app.permanent_session_lifetime = SESSIONLIFETIME
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('LABHUB_DATABASE_URI', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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

import labhub.routes

@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = SESSIONLIFETIME
