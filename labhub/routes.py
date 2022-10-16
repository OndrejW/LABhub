#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import secrets
import imghdr
import base64
import urllib.parse
import csv
from sqlalchemy import desc, asc, or_, func
from io import BytesIO, StringIO
from PIL import Image
from copy import copy
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, g
from flask_paginate import Pagination
from flask_login import login_user, logout_user, login_required, current_user
from flask_googlecharts import PieChart
from bokeh.plotting import figure, output_file, show
from bokeh.embed import components
from bokeh.models import LinearAxis, Range1d, FixedTicker, AdaptiveTicker, ColumnDataSource
from bokeh.models.tools import HoverTool
from bokeh.layouts import column
from datetime import datetime

import numpy as np
import pandas as pd
import yagmail
import SpinWaveToolkit as SWT

from labhub import app, db, bcrypt, whooshee, charts

from labhub.lib.forms import LoginForm, AddMeasurementLog, RegistrationForm, UpdateAccountForm, AddSetup, AddSample, AddProject, Attribute, AddStructure, AddSession, FilterSession, AddOccasion, LimitOccs, AddLocationSample, FilterLogs, Dispersion, addRemarkToLog, DispersionWaveguide, LabSensorDay, AddDrawer
from labhub.lib.pagination import Pagination
from labhub.lib.models import User, Log, LogImages, Setup, SetupImages, Sample, SampleImages, Project, Structure, StructureImages, Session, LogCooperators, SampleLocations, SetupFiles, LogRemark, Drawer


@app.before_request
def before_request_sidebar():
    if current_user.is_authenticated:
        g.userSessions = Session.query.join(Log, Log.session_id == Session.id).order_by(desc('date')).filter_by(user_id=current_user.id).limit(50).all()
        g.userCooperate = Session.query.join(Log, Log.session_id == Session.id).join(LogCooperators, LogCooperators.log_id == Log.id).order_by(desc('date')).filter_by(user_id=current_user.id).limit(50).all() 
        g.userLogs = Log.query.order_by(desc('date')).filter_by(user_id=current_user.id).limit(7).all()

@app.route("/")
@app.route("/index/")
@login_required
def index():
    form = FilterLogs()
    return render_template("index.html", title="Home page", form=form)

##################
# routes with view
##################

##################
# User
##################

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/register/", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/logout/")
def logout():
    logout_user()
    return redirect(url_for('index'))


def save_profile_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_profile_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title=current_user.username, image_file=image_file, form=form)

@app.route("/userInfo/<int:user_id>")
@login_required
def user_info(user_id):
    user = User.query.get_or_404(user_id)
    image_file = url_for('static', filename='profile_pics/' + user.image_file)

    # Pie chart of used setups and Projects
    usedSetupsbyUser = db.session.query(Setup.name, db.func.count(Log.setup_id)).join(Log, Setup.id == Log.setup_id).group_by(Setup.name).filter_by(user_id=user.id).all()
    setupsUsedByUserChart = PieChart("setupsUsedByUserChart", options={"width": '100%', "height": 500})
    setupsUsedByUserChart .add_column("string", "Setups")
    setupsUsedByUserChart .add_column("number", "Number of measurements")
    setupsUsedByUserChart .add_rows(usedSetupsbyUser)
    charts.register(setupsUsedByUserChart)

    ProjectFromUser = db.session.query(Project.name, db.func.count(Log.project_id)).join(Log, Project.id == Log.project_id).group_by(Project.name).filter_by(user_id=user.id).all()
    ProjectFromUserChart = PieChart("ProjectFromUserChart", options={"width": '100%', "height": 500})
    ProjectFromUserChart .add_column("string", "Setups")
    ProjectFromUserChart .add_column("number", "Number of measurements")
    ProjectFromUserChart .add_rows(ProjectFromUser)
    charts.register(ProjectFromUserChart)   

    return render_template('userinfo.html', title='User info', image_file=image_file, user=user)

@app.route("/users")
@login_required
def list_users():
    users = User.query.order_by(asc('username')).all()
    return render_template("listusers.html", title="List of users", users=users)
##################
# Measurement log
##################
def save_log_picture(form_picture, logID):
    form_pictureSplitted = form_picture.split(',')
    form_pictureDecodded = BytesIO(base64.b64decode(form_pictureSplitted[1]))
    random_hex = secrets.token_hex(8)
    if form_pictureSplitted[0].find('PNG'):
        f_ext = '.png'
    else:
        f_ext = '.jpg'
    picture_fn = random_hex + f_ext
    # Create target Directory if don't exist
    dirP = os.path.join(app.root_path, 'static\\log\\', str(logID))
    if not os.path.exists(dirP):
        os.makedirs(dirP)
    picture_path = os.path.join(dirP, picture_fn)
    dirS = 'log/' + str(logID) + '/' + picture_fn

    i = Image.open(form_pictureDecodded)
    i.save(picture_path)

    return dirS

@app.route("/addLog/", methods=['GET', 'POST'])
@login_required
def addMeasurementLog():
    form = AddMeasurementLog()
    users = [(g.id, g.username) for g in User.query.order_by('username').filter(User.id != current_user.id).all()]
    form.cooperator.choices = users 
    attributes = ''
    for entry in form.attr.entries:
        attributes = attributes + entry.data['attrName'] + ',' + entry.data['attrValue'] + '\n'
    if form.validate_on_submit():
        if form.sample.data:
            structure = Structure.query.filter_by(name=form.structure.data, sample_id=form.sample.data.id).first()
            if not structure and form.structure.data != "":
                descStruc = 'This structure was created during measurement with name ' + form.nameOfMeasurement.data
                structure = Structure(name=form.structure.data, desc=descStruc, attribute='', sample_id=form.sample.data.id)
                db.session.add(structure)
                db.session.flush()
        if hasattr(form.sample.data, 'id'):
            structure = Structure.query.filter_by(name=form.structure.data, sample_id=form.sample.data.id).first()
        else:
            structure = None
        log = Log(name=form.nameOfMeasurement.data, idea=form.idea.data, comment=form.comment.data, path=form.path.data, operator=current_user, used_setup=form.setup.data, sample=form.sample.data, structure=structure, project=form.project.data, attribute=attributes, session_id=form.session.data, typeOfOcc=0)
        db.session.add(log)
        db.session.flush()

        if request.form.getlist('image[]'):
            i = 0
            for image in request.form.getlist('image[]'):
                picture_file = save_log_picture(image, log.id)
                logImages = LogImages(log_id=log.id, title=request.form.getlist('imageTitle[]')[i], path=picture_file)
                i = i + 1
                db.session.add(logImages)
        if form.cooperator.data:
            for operator in form.cooperator.data:
                logCooperator = LogCooperators(log_id=log.id, user_id=operator)
                db.session.add(logCooperator)

        db.session.commit()
        flash(f'Log was created with name: {form.nameOfMeasurement.data}!', 'success')
        return redirect(url_for('index'))
    return render_template("addmeasurementlog.html", title="Add log", form=form)

@app.route("/log/<int:log_id>/update", methods=['GET', 'POST'])
@login_required
def update_log(log_id):
    log = Log.query.get_or_404(log_id)
    if log.typeOfOcc == 1 or log.typeOfOcc == 2 or log.typeOfOcc == 3:
        form=AddOccasion()
    else:
        form = AddMeasurementLog()
    users = [(g.id, g.username) for g in User.query.order_by('username').filter(User.id != current_user.id).all()]
    form.cooperator.choices = users
    if form.validate_on_submit():
        if form.sample.data:
            structure = Structure.query.filter_by(name=form.structure.data, sample_id=form.sample.data.id).first()
            if not structure and form.structure.data != "":
                descStruc = 'This structure was created during measurement with name ' + form.nameOfMeasurement.data
                structure = Structure(name=form.structure.data, desc=descStruc, attribute='', sample_id=form.sample.data.id)
                db.session.add(structure)
                db.session.flush()
        if hasattr(form.sample.data, 'id'):
            structure = Structure.query.filter_by(name=form.structure.data, sample_id=form.sample.data.id).first()
        else:
            structure = None
        if log.typeOfOcc == 1 or log.typeOfOcc == 2 or log.typeOfOcc == 3:
            log.name = form.name.data
            log.comment = form.desc.data
            log.typeOfOcc = form.typeOfOcc.data
        else:
            log.name = form.nameOfMeasurement.data
            log.comment = form.comment.data
            log.path = form.path.data
            log.idea = form.idea.data
        log.project = form.project.data
        log.session_id = form.session.data
        log.sample = form.sample.data
        log.used_setup = form.setup.data
        log.structure = structure
        attributes = ''
        for entry in form.attr.entries:
            attributes = attributes + entry.data['attrName'] + ',' + entry.data['attrValue'] + '\n'
            log.attribute = attributes
        if form.cooperator.data:
            for operator in form.cooperator.data:
                logCooperator = LogCooperators(log_id=log.id, user_id=operator)
                db.session.add(logCooperator)
        if request.form.getlist('image[]'):
            i = 0
            for image in request.form.getlist('image[]'):
                picture_file = save_log_picture(image, log.id)
                logImages = LogImages(log_id=log.id, title=request.form.getlist('imageTitle[]')[i], path=picture_file)
                i = i + 1
                db.session.add(logImages)
        db.session.commit()
        flash('Your log has been updated!', 'success')
        return redirect(url_for('log', log_id=log.id))
    elif request.method == 'GET':
        if log.typeOfOcc == 1 or log.typeOfOcc == 2 or log.typeOfOcc == 3:
            form.name.data = log.name
            form.desc.data = log.comment
        else:
            form.nameOfMeasurement.data = log.name
            form.comment.data = log.comment
            form.path.data = log.path
            form.idea.data = log.idea
        form.hid.data = log.id
        form.project.data = log.project
        form.session.data = log.session
        form.sample.data = log.sample
        form.setup.data = log.used_setup
        form.structure.data = log.structure
        test = csv.reader(StringIO(log.attribute), delimiter=',')
        for row in test:
            at = Attribute()
            at.attrName.data = row[0]
            at.attrValue.data = row[1]
            form.attr.append_entry(at.data)
    if log.typeOfOcc == 1 or log.typeOfOcc == 2 or log.typeOfOcc == 3:
        return render_template('addoccasion.html', title='Update log', form=form, log=log, legend='Update log')
    else:
        return render_template('addmeasurementlog.html', title='Update log', form=form, log=log, legend='Update log')

@app.route("/log/<int:log_id>/addRemark", methods=['GET', 'POST'])
@login_required
def add_RemarkToLog(log_id):
    log = Log.query.get_or_404(log_id)
    form = addRemarkToLog()
    if form.validate_on_submit():
        logRemark = LogRemark(log_id=log.id, remark=form.remark.data, user_id=current_user.id)
        db.session.add(logRemark)
        db.session.commit()
        yag = yagmail.SMTP('labhubmagnetism@gmail.com')
        contents = [
            "<h2>Hi,</h2>",
            "you get new Remark from user <b>{}</b>".format(current_user),
            "<b>Remark:</b>",
            "{}".format(form.remark.data),
            "<br>You can find your log <b><a href='{}'>here</a></b> <br>".format(url_for('log', log_id=log.id, _external=True)),

            "Cheers,",
            "Yours <b>LABhub</b>"
            ]
        yag.send(log.operator.email, 'You have new remark!', contents)
        flash('Your remark has been added!', 'success')
        return redirect(url_for('log', log_id=log.id))

    # elif request.method == 'GET':
    return render_template('addRemarkToLog.html', title='Add remark to log', form=form, legend='Add remark to log')

@app.route("/remark/<int:remark_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_remark(remark_id):
    remark = LogRemark.query.get_or_404(remark_id)
    if current_user.id == remark.user_id:
        db.session.delete(remark)
        db.session.commit()
        flash('Remark was deleted!', 'success')
        return redirect(url_for('log', log_id=remark.log_id))
    else:
        flash('Remark wasn\'t deleted! You are allowed to delete only yours remarks!', 'warning')
        return redirect(url_for('log', log_id=remark.log_id))

@app.route("/image/<int:image_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_logImage(image_id):
    image = LogImages.query.get_or_404(image_id)
    db.session.delete(image)
    db.session.commit()
    flash('Image was deleted!', 'success')
    return redirect(url_for('update_log', log_id=image.log_id))

@app.route("/addLogToSession/<int:session_id>", methods=['GET', 'POST'])
@login_required
def addMeasurementLogToSession(session_id):
    form = AddMeasurementLog()
    users = [(g.id, g.username) for g in User.query.order_by('username').filter(User.id != current_user.id).all()]
    form.cooperator.choices = users
    attributes = ''
    for entry in form.attr.entries:
        attributes = attributes + entry.data['attrName'] + ',' + entry.data['attrValue'] + '\n'
    if form.validate_on_submit():
        if form.sample.data:
            structure = Structure.query.filter_by(name=form.structure.data, sample_id=form.sample.data.id).first()
            if not structure and form.structure.data != "":
                descStruc = 'This structure was created during measurement with name ' + form.nameOfMeasurement.data
                structure = Structure(name=form.structure.data, desc=descStruc, attribute='', sample_id=form.sample.data.id)
                db.session.add(structure)
                db.session.flush()
        if hasattr(form.sample.data, 'id'):
            structure = Structure.query.filter_by(name=form.structure.data, sample_id=form.sample.data.id).first()
        else:
            structure = None
        log = Log(name=form.nameOfMeasurement.data, idea=form.idea.data, comment=form.comment.data, path=form.path.data, operator=current_user, used_setup=form.setup.data, sample=form.sample.data, structure=structure, project=form.project.data, attribute=attributes, session_id=form.session.data, typeOfOcc=0)
        db.session.add(log)
        db.session.flush()

        if request.form.getlist('image[]'):
            i = 0
            for image in request.form.getlist('image[]'):
                picture_file = save_log_picture(image, log.id)
                logImages = LogImages(log_id=log.id, title=request.form.getlist('imageTitle[]')[i], path=picture_file)
                i = i + 1
                db.session.add(logImages)
        if form.cooperator.data:
            for operator in form.cooperator.data:
                logCooperator = LogCooperators(log_id=log.id, user_id=operator)
                db.session.add(logCooperator)

        db.session.commit()
        flash(f'Measurement log was created with name: {form.nameOfMeasurement.data}!', 'success')
        return redirect(url_for('session', session_id=form.session.data, sort='desc'))
    elif form.nameOfMeasurement.data == None:
        log = Log.query.filter_by(session_id=session_id, typeOfOcc=0).order_by(desc('date')).first()
        session = Session.query.filter_by(id=session_id).first()
        form.project.data = session.project
        form.session.data = session
        if log:
            form.nameOfMeasurement.data = log.name
            form.setup.data = log.used_setup
            form.sample.data = log.sample
            form.structure.data = log.structure
            form.idea.data = log.idea
            form.path.data= log.path
            form.comment.data = log.comment
            coops = [(g.user_id) for g in log.cooperators]
            form.cooperator.data = coops
            csvAtt = csv.reader(StringIO(log.attribute), delimiter=',')
            for row in csvAtt:
                at = Attribute()
                at.attrName.data = row[0]
                at.attrValue.data = row[1]
                form.attr.append_entry(at.data)
        form.hid.data = 'addToSession'
        return render_template("addmeasurementlog.html", title="Add log", form=form)
    else:   
        log = Log.query.filter_by(session_id=session_id).order_by(desc('date')).first()
        form.project.data = log.project
        form.session.data = log.session
        form.hid.data = 'addToSession'
        return render_template("addmeasurementlog.html", title="Add log", form=form)

@app.route('/_listLogsFiltered', methods=['GET', 'POST'])
def _listLogsFiltered():
    idProject = request.values.get('idProject')
    idSetup = request.values.get('idSetup')
    idSample = request.values.get('idSample')
    idStructure = request.values.get('idStructure')
    idSession = request.values.get('idSession')
    limit = request.values.get('limit')
    tLog = request.values.get('tLog')
    tInfo = request.values.get('tInfo')
    ftSearch = request.values.get('ftSearch')
    query = Log.query
    if idProject and idProject != '__None':
        query = query.filter_by(project_id=idProject)
    if idSetup and idSetup != '__None':
        query = query.filter_by(setup_id=idSetup)
    if idSample and idSample != '__None':
        query = query.filter_by(sample_id=idSample)
    if idStructure and idStructure != '__None':
        query = query.filter_by(structure_id=idStructure)
    if idSession and idSession != '__None':
        query = query.filter_by(session_id=idSession)
    if tLog and tLog == '0':
        query = query.filter(or_(Log.typeOfOcc != 0) )
    if tInfo and tInfo == '0':
        query = query.filter(Log.typeOfOcc != 1)
    if ftSearch and ftSearch != '__None':
        query = query.whooshee_search(ftSearch, match_substrings=True)
    else:
        query = query.order_by(desc('date'))
    if limit and limit != '__None':
        query = query.limit(limit)

    logs = query.all()
    listOfCooperators = []
    if logs:
        for log in logs:
            cooperators = User.query.filter(User.id.in_(cooperator.user_id for cooperator in log.cooperators)).all()
            listOfCooperators.append(cooperators)
        return render_template("logs.html", title="Home page", logs=logs, cooperators=listOfCooperators)
    else:
       return 'There are not any logs yet!'

@app.route('/_listLogsFilteredPagination', methods=['GET', 'POST'])
def _listLogsFilteredPagination():
    page = request.values.get('page', 1, type=int)
    idProject = request.values.get('idProject')
    idSetup = request.values.get('idSetup')
    idSample = request.values.get('idSample')
    idStructure = request.values.get('idStructure')
    idSession = request.values.get('idSession')
    idUser = request.values.get('idUser')
    limit = request.values.get('limit')
    tLog = request.values.get('tLog')
    tInfo = request.values.get('tInfo')
    ftSearch = request.values.get('ftSearch')
    query = Log.query
    if idProject and idProject != '__None':
        query = query.filter_by(project_id=idProject)
    if idSetup and idSetup != '__None':
        query = query.filter_by(setup_id=idSetup)
    if idSample and idSample != '__None':
        query = query.filter_by(sample_id=idSample)
    if idStructure and idStructure != '__None':
        query = query.filter_by(structure_id=idStructure)
    if idSession and idSession != '__None':
        query = query.filter_by(session_id=idSession)
    if idUser and idUser != '__None':
        query = query.filter_by(user_id=idUser)
    if tLog and tLog == '0':
        query = query.filter(or_(Log.typeOfOcc != 0) )
    if tInfo and tInfo == '0':
        query = query.filter(Log.typeOfOcc != 1)
    if ftSearch and ftSearch != '__None':
        query = query.whooshee_search(ftSearch, match_substrings=True)
    else:
        query = query.order_by(desc('date'))
    if limit and limit != '__None':
        query = query.limit(limit)

    logs = query.paginate(page=page, per_page=10)
    listOfCooperators = []
    if logs.items:
        for log in logs.items:
            cooperators = User.query.filter(User.id.in_(cooperator.user_id for cooperator in log.cooperators)).all()
            listOfCooperators.append(cooperators)
        return render_template("logspagination.html", title="Home page", logs=logs, cooperators=listOfCooperators)
    else:
       return 'There are not any logs yet!'

@app.route("/log/<int:log_id>")
@login_required
def log(log_id):
    log = Log.query.get_or_404(log_id)
    cooperators = User.query.filter(User.id.in_(cooperator.user_id for cooperator in log.cooperators)).all()
    attrTable = csv.reader(StringIO(log.attribute), delimiter=',')
    return render_template('log.html', title=log.name, log=log, attrTable = attrTable, cooperators=cooperators)

##################
# Setup
##################
def save_setup_picture(form_picture, setupID):
    form_pictureSplitted = form_picture.split(',')
    form_pictureDecodded = BytesIO(base64.b64decode(form_pictureSplitted[1]))
    random_hex = secrets.token_hex(8)
    if form_pictureSplitted[0].find('PNG'):
        f_ext = '.png'
    else:
        f_ext = '.jpg'
    picture_fn = random_hex + f_ext
    # Create target Directory if don't exist
    dirP = os.path.join(app.root_path, 'static\\setup\\', str(setupID))
    if not os.path.exists(dirP):
        os.makedirs(dirP)
    picture_path = os.path.join(dirP, picture_fn)
    dirS = 'setup/' + str(setupID) + '/' + picture_fn

    i = Image.open(form_pictureDecodded)
    i.save(picture_path)

    return dirS

@app.route("/addSetup/", methods=['GET', 'POST'])
@login_required
def addSetup():
    form = AddSetup()
    if form.validate_on_submit():
        if form.manuals.data:
                manual_file_path = save_file(form.manuals.data, setup.id)
                setupFiles = SetupFiles(setup_id=setup.id, title=form.manualsName.data, path=manual_file_path)
                db.session.add(setupFiles)
        attributes = ''
        for entry in form.attr.entries:
            attributes = attributes + entry.data['attrName'] + ',' + ''+ '\n'
        setup = Setup(name=form.name.data, desc=form.desc.data, attribute=attributes)
        db.session.add(setup)
        db.session.flush()

        if request.form.getlist('image[]'):
            i = 0
            for image in request.form.getlist('image[]'):
                picture_file = save_setup_picture(image, setup.id)
                setupImages = SetupImages(setup_id=setup.id, title=request.form.getlist('imageTitle[]')[i], path=picture_file)
                i = i + 1
                db.session.add(setupImages)

        db.session.commit()
        flash(f'Setup was created with name: {form.name.data}!', 'success')
        return redirect(url_for('index'))
    return render_template("addsetup.html", title="Add setup", form=form, legend='Add setup')

@app.route("/setup/<int:setup_id>")
@login_required
def setup(setup_id):
    setup = Setup.query.get_or_404(setup_id)
    form = LimitOccs()
    return render_template('setup.html', title=setup.name, setup=setup, form=form)

def save_file(form_manual, setupID):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_manual.filename)
    manual_fn = random_hex + f_ext
    dirP = os.path.join(app.root_path, 'static\\setup\\', str(setupID))
    if not os.path.exists(dirP):
        os.makedirs(dirP)
    manual_path = os.path.join(dirP, manual_fn)
    dirS = 'setup/' + str(setupID) + '/' + manual_fn
    form_manual.save(manual_path)

    return dirS

@app.route("/setup/<int:setup_id>/update", methods=['GET', 'POST'])
@login_required
def update_setup(setup_id):
    setup = Setup.query.get_or_404(setup_id)
    form = AddSetup()
    if form.validate_on_submit():
        if form.manuals.data:
                manual_file_path = save_file(form.manuals.data, setup.id)
                setupFiles = SetupFiles(setup_id=setup.id, title=form.manualsName.data, path=manual_file_path)
                db.session.add(setupFiles)
        setup.name = form.name.data
        setup.desc = form.desc.data
        attributes = ''
        for entry in form.attr.entries:
            attributes = attributes + entry.data['attrName'] + ',' + ''+ '\n'
        setup.attribute = attributes
        if request.form.getlist('image[]'):
            i = 0
            for image in request.form.getlist('image[]'):
                picture_file = save_setup_picture(image, setup.id)
                setupImages = SetupImages(setup_id=setup.id, title=request.form.getlist('imageTitle[]')[i], path=picture_file)
                i = i + 1
                db.session.add(setupImages)
        db.session.commit()
        flash('Your setup has been updated!', 'success')
        return redirect(url_for('setup', setup_id=setup.id))
    elif request.method == 'GET':
        form.name.data = setup.name
        form.desc.data = setup.desc
        form.idHid.data = setup.id
        test = csv.reader(StringIO(setup.attribute), delimiter=',')
        for row in test:
            at = Attribute()
            at.attrName.data = row[0]
            at.attrValue.data = row[1]
            form.attr.append_entry(at.data)
    return render_template('addsetup.html', title='Update setup', form=form, legend='Update setup')

@app.route("/setup/list")
@login_required
def list_setup():
    setup = Setup.query.order_by(asc('name')).all()
    return render_template("listsetup.html", title="List of setups", setups=setup)

@app.route('/_listSetupAttr', methods=['GET', 'POST'])
def _listSetupAttr():
    idSetup = request.values.get('idSetup')
    setup = Setup.query.filter_by(id=idSetup).first()
    if setup:
        setupJSON = []
        attrTable = csv.reader(StringIO(setup.attribute), delimiter=',')
        for attr in attrTable:
            setupJSON = setupJSON + [
            {
            'attrName': attr[0],
            'attrValue': attr[1]
            }]
        return jsonify(setupJSON)
    else:
       return jsonify({'error' : 'There are not attributes on this setup yet!'}) 
    return jsonify({'error' : 'Setup doesn\'t exists!'})



##################
# Sample
##################
def save_sample_picture(form_picture, sampleID):
    form_pictureSplitted = form_picture.split(',')
    form_pictureDecodded = BytesIO(base64.b64decode(form_pictureSplitted[1]))
    random_hex = secrets.token_hex(8)
    if form_pictureSplitted[0].find('PNG'):
        f_ext = '.png'
    else:
        f_ext = '.jpg'
    picture_fn = random_hex + f_ext
    # Create target Directory if don't exist
    dirP = os.path.join(app.root_path, 'static\\sample\\', str(sampleID))
    if not os.path.exists(dirP):
        os.makedirs(dirP)
    picture_path = os.path.join(dirP, picture_fn)
    dirS = 'sample/' + str(sampleID) + '/' + picture_fn

    i = Image.open(form_pictureDecodded)
    i.save(picture_path)

    return dirS

@app.route("/addSample/", methods=['GET', 'POST'])
@login_required
def addSample():
    form = AddSample()
    if form.validate_on_submit():
        attributes = ''
        for entry in form.attr.entries:
            attributes = attributes + entry.data['attrName'] + ',' + entry.data['attrValue'] + '\n'
        sample = Sample(name=form.name.data, desc=form.desc.data, attribute=attributes, drawer=form.drawer.data)
        db.session.add(sample)
        db.session.flush()

        if request.form.getlist('image[]'):
            i = 0
            for image in request.form.getlist('image[]'):
                picture_file = save_sample_picture(image, sample.id)
                sampleImages = SampleImages(sample_id=sample.id, title=request.form.getlist('imageTitle[]')[i], path=picture_file)
                i = i + 1
                db.session.add(sampleImages)

        db.session.commit()
        flash(f'Sample was created with name: {form.name.data}!', 'success')
        return redirect(url_for('index'))
    return render_template("addsample.html", title="Add sample", form=form, legend='Add sample')

@app.route("/sample/<int:sample_id>")
@login_required
def sample(sample_id):
    sample = Sample.query.get_or_404(sample_id)
    structure = Structure.query.filter_by(sample_id=sample_id).all()
    attrTable = csv.reader(StringIO(sample.attribute), delimiter=',')
    form = LimitOccs()
    return render_template('sample.html', title=sample.name, sample=sample, attrTable = attrTable, structures = structure, form=form)

@app.route("/sample/<int:sample_id>/update", methods=['GET', 'POST'])
@login_required
def update_sample(sample_id):
    sample = Sample.query.get_or_404(sample_id)
    form = AddSample()
    if form.validate_on_submit():
        attributes = ''
        for entry in form.attr.entries:
            attributes = attributes + entry.data['attrName'] + ',' + entry.data['attrValue'] + '\n'
        sample.name = form.name.data
        sample.desc = form.desc.data
        sample.attribute = attributes
        sample.drawer = form.drawer.data

        if request.form.getlist('image[]'):
            i = 0
            for image in request.form.getlist('image[]'):
                picture_file = save_sample_picture(image, sample.id)
                sampleImages = SampleImages(sample_id=sample.id, title=request.form.getlist('imageTitle[]')[i], path=picture_file)
                i = i + 1
                db.session.add(sampleImages)

        db.session.commit()
        flash('Your sample has been updated!', 'success')
        return redirect(url_for('sample', sample_id=sample.id))
    elif request.method == 'GET':
        form.name.data = sample.name
        form.drawer.data = sample.drawer
        form.desc.data = sample.desc
        form.idHid.data = sample.id
        test = csv.reader(StringIO(sample.attribute), delimiter=',')
        for row in test:
            at = Attribute()
            at.attrName.data = row[0]
            at.attrValue.data = row[1]
            form.attr.append_entry(at.data)
    return render_template('addsample.html', title='Update sample', form=form, legend='Update sample')

@app.route("/sample/<int:sample_id>/addlocation", methods=['GET', 'POST'])
@login_required
def addLocation_sample(sample_id):
    sample = Sample.query.get_or_404(sample_id)
    form = AddLocationSample()
    if form.validate_on_submit():
        SampleLocation = SampleLocations(sample_id=sample.id, location=form.location.data)
        db.session.add(SampleLocation)
        db.session.commit()
        flash('Your sample location has been updated!', 'success')
        return redirect(url_for('sample', sample_id=sample.id))

    # elif request.method == 'GET':
    return render_template('addlocationsample.html', title='Add location of sample', form=form, legend='Add location of sample')

@app.route("/sample/list")
@login_required
def list_sample():
    sample = Sample.query.order_by(desc('date')).all()
    return render_template("listsample.html", title="List of samples", samples=sample)

@app.route("/drawer/<int:drawer_id>")
@login_required
def drawer(drawer_id):
    drawer = Drawer.query.get_or_404(drawer_id)
    sample = Sample.query.filter_by(drawer_id=drawer_id).all()
    return render_template('drawer.html', title=drawer.name, drawer=drawer, samples = sample)

@app.route("/addDrawer/", methods=['GET', 'POST'])
@login_required
def addDrawer():
    form = AddDrawer()
    if form.validate_on_submit():
        drawer = Drawer(name=form.name.data, desc=form.desc.data, number=form.number.data)
        db.session.add(drawer)
        db.session.flush()
        db.session.commit()
        flash(f'Drawer was created with name: {form.name.data}!', 'success')
        return redirect(url_for('index'))
    return render_template("adddrawer.html", title="Add drawer", form=form, legend='Add drawer')

@app.route("/drawer/list")
@login_required
def list_drawer():
    drawers = Drawer.query.order_by(asc('id')).all()
    return render_template("listdrawer.html", title="List of drawers", drawers=drawers)

@app.route("/drawer/<int:drawer_id>/update", methods=['GET', 'POST'])
@login_required
def update_drawer(drawer_id):
    drawer = Drawer.query.get_or_404(drawer_id)
    form = AddDrawer()
    if form.validate_on_submit():
        drawer.name = form.name.data
        drawer.desc = form.desc.data
        drawer.number = form.number.data
        db.session.commit()
        flash('Your drawer has been updated!', 'success')
        return redirect(url_for('drawer', drawer_id=drawer.id))
    elif request.method == 'GET':
        form.name.data = drawer.name
        form.desc.data = drawer.desc
        form.idHid.data = drawer.id
        form.number.data = drawer.number
    return render_template('adddrawer.html', title='Update drawer', form=form, legend='Update drawer')


##################
# Structure
##################
def save_structure_picture(form_picture, sampleID, structureID):
    form_pictureSplitted = form_picture.split(',')
    form_pictureDecodded = BytesIO(base64.b64decode(form_pictureSplitted[1]))
    random_hex = secrets.token_hex(8)
    if form_pictureSplitted[0].find('PNG'):
        f_ext = '.png'
    else:
        f_ext = '.jpg'
    picture_fn = random_hex + f_ext
    # Create target Directory if don't exist
    dirP = os.path.join(app.root_path, 'static\\sample\\', str(sampleID), str(structureID) )
    if not os.path.exists(dirP):
        os.makedirs(dirP)
    picture_path = os.path.join(dirP, picture_fn)
    dirS = 'sample/' + str(sampleID) + '/' + str(structureID) + '/' + picture_fn

    i = Image.open(form_pictureDecodded)
    i.save(picture_path)

    return dirS



@app.route("/addStructure/", methods=['GET', 'POST'])
@login_required
def addStructure():
    form = AddStructure()
    if form.validate_on_submit():
        attributes = ''
        for entry in form.attr.entries:
            attributes = attributes + entry.data['attrName'] + ',' + entry.data['attrValue'] + '\n'
        structure = Structure(name=form.name.data, desc=form.desc.data, attribute=attributes, sample_id=form.sample.data.id)
        db.session.add(structure)
        db.session.flush()

        if request.form.getlist('image[]'):
            i = 0
            for image in request.form.getlist('image[]'):
                picture_file = save_structure_picture(image, form.sample.data.id, structure.id)
                structureImages = StructureImages(structure_id=structure.id, title=request.form.getlist('imageTitle[]')[i], path=picture_file)
                i = i + 1
                db.session.add(structureImages)

        db.session.commit()
        flash(f'Structure was created with name: {form.name.data}!', 'success')
        return redirect(url_for('index'))
    return render_template("addstructure.html", title="Add structure", form=form, legend='Add structure')

@app.route("/structure/<int:structure_id>")
@login_required
def structure(structure_id):
    structure = Structure.query.get_or_404(structure_id)
    sample = Sample.query.get_or_404(structure.sample_id)
    attrTable = csv.reader(StringIO(structure.attribute), delimiter=',')
    return render_template('structure.html', title=structure.name, structure=structure, attrTable = attrTable, sample=sample)

@app.route("/structure/<int:structure_id>/update", methods=['GET', 'POST'])
@login_required
def update_structure(structure_id):
    structure = Structure.query.get_or_404(structure_id)
    form = AddStructure()
    if form.validate_on_submit():
        attributes = ''
        for entry in form.attr.entries:
            attributes = attributes + entry.data['attrName'] + ',' + entry.data['attrValue'] + '\n'
        structure.name = form.name.data
        structure.desc = form.desc.data
        structure.attribute = attributes

        if request.form.getlist('image[]'):
            i = 0
            for image in request.form.getlist('image[]'):
                picture_file = save_structure_picture(image, form.sample.data.id, structure.id)
                structureImages = StructureImages(structure_id=structure.id, title=request.form.getlist('imageTitle[]')[i], path=picture_file)
                i = i + 1
                db.session.add(structureImages)

        db.session.commit()
        flash('Your structure has been updated!', 'success')
        return redirect(url_for('structure', structure_id=structure.id))
    elif request.method == 'GET':
        form.name.data = structure.name
        form.desc.data = structure.desc
        form.idHid.data = structure.id
        test = csv.reader(StringIO(structure.attribute), delimiter=',')
        for row in test:
            at = Attribute()
            at.attrName.data = row[0]
            at.attrValue.data = row[1]
            form.attr.append_entry(at.data)
    return render_template('addstructure.html', title='Update structure', form=form, legend='Update structure')

@app.route('/_listStructures', methods=['GET', 'POST'])
def _listStructures():
    idSample = request.values.get('idSample')
    sample = Sample.query.filter_by(id=idSample).first()
    if sample:
        structures = Structure.query.filter_by(sample_id = idSample)
        if len(structures.all()) != 0:
            structuresJSON = []
            for structure in structures:
                structuresJSON = structuresJSON + [
                {
                'name': structure.name,
                'id': structure.id
                }]
            return jsonify(structuresJSON)
        else:
           return jsonify({'error' : 'There are not structures on this sample yet! You can add structure just by typing its name.'}) 
    return jsonify({'error' : 'Sample doesn\'t exists!'})

##################
# Project
##################
@app.route("/addProject/", methods=['GET', 'POST'])
@login_required
def addProject():
    form = AddProject()
    if form.validate_on_submit():
        project = Project(name=form.name.data, desc=form.desc.data)
        db.session.add(project)
        db.session.flush()
        db.session.commit()
        flash(f'Project was created with name: {form.name.data}!', 'success')
        return redirect(url_for('index'))
    return render_template("addproject.html", title="Add project", form=form, legend='Add project')

@app.route("/project/<int:project_id>")
@login_required
def project(project_id):
    project = Project.query.get_or_404(project_id)
    sessions = Session.query.order_by(desc('date')).filter_by(project_id=project.id)
    # List of samples
    samplesInProj = db.session.query(Sample, db.func.count(Log.sample_id)).join(Log, Sample.id == Log.sample_id).group_by(Sample.name).filter_by(project_id=project.id).order_by(desc('date')).all()
    # Pie chart of users and setups involved in Project
    usersInProj = db.session.query(User.username, db.func.count(Log.user_id)).join(Log, User.id == Log.user_id).group_by(User.username).filter_by(project_id=project.id).all()
    usersInProjChart = PieChart("usersInProjChart", options={"width": '100%', "height": 500})
    usersInProjChart.add_column("string", "User name")
    usersInProjChart.add_column("number", "Number of measurements")
    usersInProjChart.add_rows(usersInProj)
    charts.register(usersInProjChart)

    setupsInProj = db.session.query(Setup.name, db.func.count(Log.setup_id)).join(Log, Setup.id == Log.setup_id).group_by(Setup.name).filter_by(project_id=project.id).all()
    setupsInProjChart = PieChart("setupsInProjChart", options={"width": '100%', "height": 500})
    setupsInProjChart.add_column("string", "Setups")
    setupsInProjChart.add_column("number", "Number of measurements")
    setupsInProjChart.add_rows(setupsInProj)
    charts.register(setupsInProjChart)

    return render_template('project.html', title=project.name, project=project, sessions=sessions, samples=samplesInProj)

@app.route("/project/<int:project_id>/update", methods=['GET', 'POST'])
@login_required
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    form = AddProject()
    if form.validate_on_submit():
        project.name = form.name.data
        project.desc = form.desc.data
        db.session.commit()
        flash('Your project has been updated!', 'success')
        return redirect(url_for('project', project_id=project.id))
    elif request.method == 'GET':
        form.name.data = project.name
        form.desc.data = project.desc
        form.idHid.data = project.id
    return render_template('addproject.html', title='Update project', form=form, legend='Update project')

@app.route("/project/list")
@login_required
def list_project():
    project = Project.query.order_by(asc('name')).all()
    return render_template("listproject.html", title="List of samples", projects=project)

##################
# Session
##################
@app.route("/addSession/", methods=['GET', 'POST'])
@login_required
def addSession():
    form = AddSession()
    if form.validate_on_submit():
        session = Session(name=form.name.data, comment=form.comment.data, idea=form.idea.data, project_id=form.project.data.id, findings=form.findings.data)
        db.session.add(session)
        db.session.flush()
        db.session.commit()
        flash(f'Session was created with name: {form.name.data}!', 'success')
        return redirect(url_for('index'))
    return render_template("addsession.html", title="Add session", form=form, legend='Add session')

@app.route("/session/<int:session_id>", defaults={'sort': 'desc'})
@app.route("/session/<int:session_id>/<string:sort>")
@login_required
def session(session_id, sort):
    session = Session.query.get_or_404(session_id)
    if sort == 'desc':
        logs = Log.query.filter_by(session_id=session_id).order_by(desc('date')).all()
    else:
        logs = Log.query.filter_by(session_id=session_id).order_by(asc('date')).all()
    listOfCooperators = []
    attrTables = []
    attrTable = []
    for log in logs:
        csvTemp = csv.reader(StringIO(log.attribute), delimiter=',')
        for row in csvTemp:
            attrTable.append(row)
        attrTables = attrTables + [attrTable]
        attrTable = []
        cooperators = User.query.filter(User.id.in_(cooperator.user_id for cooperator in log.cooperators)).all()
        listOfCooperators.append(cooperators)
    return render_template('session.html', title=session.name, session=session, logs=logs, attrTables=attrTables, sort=sort, cooperators=listOfCooperators)

@app.route("/session/<int:session_id>/update", methods=['GET', 'POST'])
@login_required
def update_session(session_id):
    session = Session.query.get_or_404(session_id)
    form = AddSession()
    if form.validate_on_submit():
        session.name = form.name.data
        session.comment = form.comment.data
        session.idea = form.idea.data
        session.project_id = form.project.data.id
        session.findings = form.findings.data
        db.session.commit()
        flash('Your session has been updated!', 'success')
        return redirect(url_for('session', session_id=session.id))
    elif request.method == 'GET':
        form.name.data = session.name
        form.comment.data = session.comment
        form.idea.data = session.idea
        form.project.data = session.project
        form.findings.data = session.findings
    return render_template('addsession.html', title='Update session', form=form, legend='Update session')

@app.route("/session/list")
@login_required
def list_session():
    form = FilterSession()
    return render_template("listsession.html", title="List of sessions", form=form)

@app.route('/_listSessions', methods=['GET', 'POST'])
def _listSessions():
    idProject = request.values.get('idProject')
    project = Project.query.filter_by(id=idProject).first()
    if project:
        sessions = Session.query.filter_by(project_id = idProject)
        if len(sessions.all()) != 0:
            sessionsJSON = []
            for session in sessions:
                sessionsJSON = sessionsJSON + [
                {
                'name': session.name,
                'id': session.id
                }]
            return jsonify(sessionsJSON)
        else:
           return jsonify({'error' : 'There are not sessions in this project yet!'}) 
    return jsonify({'error' : 'Project doesn\'t exists!'})

@app.route('/_listSessionsFiltered', methods=['GET', 'POST'])
def _listSessionsFiltered():
    idProject = request.values.get('idProject')
    idSetup = request.values.get('idSetup')
    idSample = request.values.get('idSample')
    query = Session.query.order_by(desc('date'))
    if idProject and idProject != '__None':
        query = query.filter_by(project_id=idProject)
    if idSetup and idSetup != '__None':
        query = query.join(Log, Log.session_id == Session.id).filter_by(setup_id=idSetup)
    if idSample and idSample != '__None':
        query = query.join(Log, Log.session_id == Session.id).filter_by(sample_id=idSample)
    sessions = query.all()
    if len(sessions) != 0:
        sessionsJSON = []
        for session in sessions:
            sessionsJSON = sessionsJSON + [
            {
            'name': session.name,
            'id': session.id,
            'date': session.date,
            'idea': session.idea,
            'findings': session.findings
            }]
        return jsonify(sessionsJSON)
    else:
       return jsonify({'error' : 'There are not sessions with these parameters!'}) 


@app.route("/addOccasion/", methods=['GET', 'POST'])
@login_required
def addOccasion():
    form = AddOccasion()
    users = [(g.id, g.username) for g in User.query.order_by('username').filter(User.id != current_user.id).all()]
    form.cooperator.choices = users
    attributes = ''
    for entry in form.attr.entries:
        attributes = attributes + entry.data['attrName'] + ',' + entry.data['attrValue'] + '\n'
    if form.validate_on_submit():
        if form.sample.data:
            structure = Structure.query.filter_by(name=form.structure.data, sample_id=form.sample.data.id).first()
            if not structure and form.structure.data != "":
                descStruc = 'This structure was created during measurement with name ' + form.name.data
                structure = Structure(name=form.structure.data, desc=descStruc, attribute='', sample_id=form.sample.data.id)
                db.session.add(structure)
                db.session.flush()
        if hasattr(form.sample.data, 'id'):
            structure = Structure.query.filter_by(name=form.structure.data, sample_id=form.sample.data.id).first()
        else:
            structure = None
        log = Log(name=form.name.data, comment=form.desc.data, operator=current_user, used_setup=form.setup.data, sample=form.sample.data, structure=structure, project=form.project.data, session_id=form.session.data, typeOfOcc=form.typeOfOcc.data, attribute=attributes)
        db.session.add(log)
        db.session.flush()

        if request.form.getlist('image[]'):
            i = 0
            for image in request.form.getlist('image[]'):
                picture_file = save_log_picture(image, log.id)
                logImages = LogImages(log_id=log.id, title=request.form.getlist('imageTitle[]')[i], path=picture_file)
                i = i + 1
                db.session.add(logImages)
        if form.cooperator.data:
            for operator in form.cooperator.data:
                logCooperator = LogCooperators(log_id=log.id, user_id=operator)
                db.session.add(logCooperator)

        db.session.commit()
        flash(f'Note was created with name: {form.name.data}!', 'success')
        return redirect(url_for('index'))
    return render_template("addoccasion.html", title="Add note", form=form)

@app.route("/addOccasionToSession/<int:session_id>", methods=['GET', 'POST'])
@login_required
def addOccasionToSession(session_id):
    form = AddOccasion()
    users = [(g.id, g.username) for g in User.query.order_by('username').filter(User.id != current_user.id).all()]
    form.cooperator.choices = users
    if form.validate_on_submit():
        structure = Structure.query.filter_by(name=form.structure.data, sample_id=form.sample.data.id).first()
        if not structure and form.structure.data != "":
            descStruc = 'This structure was created during measurement with name ' + form.name.data
            structure = Structure(name=form.structure.data, desc=descStruc, attribute='', sample_id=form.sample.data.id)
            db.session.add(structure)
            db.session.flush()
        log = Log(name=form.name.data, comment=form.desc.data, operator=current_user, used_setup=form.setup.data, sample=form.sample.data, structure=structure, project=form.project.data, session_id=form.session.data, typeOfOcc=form.typeOfOcc.data)
        db.session.add(log)
        db.session.flush()

        if request.form.getlist('image[]'):
            i = 0
            for image in request.form.getlist('image[]'):
                picture_file = save_log_picture(image, form.name.data)
                logImages = LogImages(log_id=log.id, title=request.form.getlist('imageTitle[]')[i], path=picture_file)
                i = i + 1
                db.session.add(logImages)
        if form.cooperator.data:
            for operator in form.cooperator.data:
                logCooperator = LogCooperators(log_id=log.id, user_id=operator)
                db.session.add(logCooperator)

        db.session.commit()
        flash(f'Measurement log was created with name: {form.name.data}!', 'success')
        return redirect(url_for('session', session_id=form.session.data, sort=desc))
    elif form.name.data == None:
        log = Log.query.filter_by(session_id=session_id).order_by(desc('date')).first()
        session = Session.query.filter_by(id=session_id).first()
        form.project.data = session.project
        form.session.data = session
        if log:
            form.name.data = log.name
            form.project.data = log.project
            form.session.data = log.session
            form.setup.data = log.used_setup
            form.sample.data = log.sample
            form.structure.data = log.structure
            form.desc.data = log.comment
            coops = [(g.user_id) for g in log.cooperators]
            form.cooperator.data = coops
        form.hid.data = 'addToSession'
        return render_template("addoccasion.html", title="Add measurement log", form=form)
    else:   
        log = Log.query.filter_by(session_id=session_id).order_by(desc('date')).first()
        form.project.data = log.project
        form.session.data = log.session
        form.hid.data = 'addToSession'
        return render_template("addoccasion.html", title="Add measurement log", form=form)


# Tools
@app.route("/tools")
@login_required
def tools():
    return render_template("tools.html", title="Tools")

@app.route("/dispersion")
@login_required
def dispersion():
    form = Dispersion()
    return render_template("dispersion.html", title="Tools", form=form)

@app.route("/dispersionWaveguide")
@login_required
def dispersionWaveguide():
    form = DispersionWaveguide()
    return render_template("dispersionWaveguide.html", title="Tools", form=form)

def slavinDisp(kxi, theta, phi, n, d, w0, wM, A):
    # Quantization of k for z (out of plane)
    k = np.sqrt(np.power(kxi,2) + np.power(n*np.pi/d,2)) 
    Pnn = np.power(kxi,2)/np.power(k,2) - np.power(kxi,2)/np.power(k,2)*(1 - np.exp(-k*d))/(k*d)
    Pnn[0] = 0
    Fnn = Pnn + np.power(np.sin(theta),2)*(1-Pnn*(1+np.power(np.cos(phi),2)) + wM*(Pnn*(1 - Pnn)*np.power(np.sin(phi),2))/(w0 + A*wM*np.power(k,2)))
    f = np.sqrt((w0 + A*wM*np.power(k,2))*(w0 + A*wM*np.power(k,2) + wM*Fnn))

    return f

def slavinDispWaveguide(kxi, theta, phi, n, d, w0, wM, A, weff, nT, boundaryCond):
    # Quantization of k for z (out of plane)
    k = np.sqrt(np.power(kxi,2) + np.power(n*np.pi/d,2) + np.power(nT*np.pi/weff,2))
    # Totally unpinned boundary condition
    if boundaryCond == 1:
        if n == 0:
            Pnn = (kxi**2)/(k**2) - (kxi**4)/(k**4)*(1/2)*(2/(kxi*d)*(1-np.exp(-kxi*d)))
        else:
            Pnn = (kxi**2)/(k**2) - (kxi**4)/(k**4)*(2/(kxi*d)*(1-np.exp(-kxi*d)))
    # Totally pinned boundary condition
    else:
        Pnn = (kxi**2)/(k**2) - (kxi**2)/(k**2)*(1 - np.exp(-k*d))/(k*d);
    # Deprecated
        # Pnn = np.power(kxi,2)/np.power(k,2) - np.power(kxi,2)/np.power(k,2)*(1 - np.exp(-k*d))/(k*d)
    # Pnn[0] = 0
    Fnn = Pnn + np.power(np.sin(theta),2)*(1-Pnn*(1+np.power(np.cos(phi),2)) + wM*(Pnn*(1 - Pnn)*np.power(np.sin(phi),2))/(w0 + A*wM*np.power(k,2)))
    f = np.sqrt((w0 + A*wM*np.power(k,2))*(w0 + A*wM*np.power(k,2) + wM*Fnn))

    return f


@app.route("/_dispersion", methods=['GET', 'POST'])
@login_required
def _dispersion():

    gamma = float(request.values.get('gamma'))*1e9
    mu0 = 4*np.pi*1e-7
    if int(request.values.get('MsatUnits')) == 0:
        Msat = float(request.values.get('Msat'))
    elif int(request.values.get('MsatUnits')) == 1:
        Msat = float(request.values.get('Msat'))/mu0
    elif int(request.values.get('MsatUnits')) == 2:
        Msat = float(request.values.get('Msat'))*1e3
    # Conversion of field
    if int(request.values.get('extFieldUnits')) == 0:
        H0 = float(request.values.get('extField'))*1e-3/mu0
    elif int(request.values.get('extFieldUnits')) == 1:
        H0 = float(request.values.get('extField'))/mu0
    elif int(request.values.get('extFieldUnits')) == 2:
        H0 = float(request.values.get('extField'))*1e-4/mu0
    elif int(request.values.get('extFieldUnits')) == 3:
        H0 = float(request.values.get('extField'))*79.57747154594
    elif int(request.values.get('extFieldUnits')) == 4:
        H0 = float(request.values.get('extField'))
    # Conversion of exchange
    if int(request.values.get('exchangeUnits')) == 0:
        A = float(request.values.get('exchange'))*2/(np.power(Msat,2)*mu0)
    elif int(request.values.get('exchangeUnits')) == 1:
        A = float(request.values.get('exchange'))
    d = float(request.values.get('thickness'))*1e-9
    phi = np.deg2rad(float(request.values.get('phi')))
    phiDeg = float(request.values.get('phi'))
    theta = np.deg2rad(float(request.values.get('theta')))
    thetaDeg = int(request.values.get('theta'))
    n = int(request.values.get('n'))

    w0 = gamma*mu0*H0
    wM = gamma*mu0*Msat


    kxi = np.linspace(start=0, stop=50e6, num=100)
    # Damon-Eshbach - 00
    fDE =  slavinDisp(kxi=kxi, theta=theta, phi=np.pi/2, n=0, d=d, w0=w0, wM=wM, A=A) 
    # Backward volume - 00
    fBV =  slavinDisp(kxi=kxi, theta=theta, phi=0, n=0, d=d, w0=w0, wM=wM, A=A)
    # Custom
    fc =  slavinDisp(kxi=kxi, theta=theta, phi=phi, n=n, d=d, w0=w0, wM=wM, A=A) 

    # fDEKlas = np.sqrt(w0*(wM + w0) + np.power(wM,2)/4*(1 - np.exp(-2*kxi*d)))

    # k = np.sqrt(np.power(kxi,2) + np.power(0*np.pi/d,2))
    # P00 = 1 + (2*(1-np.exp(-k*d)))/(k*d)
    # F00 = P00 + np.power(np.sin(np.pi/2),2)*(1-P00*(1+np.power(np.cos(np.pi/2),2)) + wM*(P00*(1 - P00)*np.power(np.sin(np.pi/2),2))/(w0 + A*wM*np.power(k,2)))
    # fPIN = np.sqrt((w0 + A*wM*np.power(k,2))*(w0 + A*wM*np.power(k,2) + wM*F00))
    TOOLTIPS = [
    ("k:", "$x rad/um"),
    ("f:", "$y GHz")
    ]
    p = figure(title="Dispersion relation - theta = " + str(thetaDeg) + "°", x_axis_label='k (rad/um)', y_axis_label='Frequency (GHz)', tooltips=TOOLTIPS)
    p.line(kxi, fDE, legend="Damon-Eshbach - n = 0", line_width=3)
    p.line(kxi, fBV, legend="Backward volume - n = 0", line_width=3, line_color="red")
    p.line(kxi, fc, legend="Phi = " + str(phiDeg) + " - n = "+ str(n) + "", line_width=3, line_color="black")
    # p.line(kxi, fPIN, legend="Pinned", line_width=3, line_color="green")
    # p.line(kxi, fDEKlas, legend="Klasika", line_width=3, line_color="brown")
    p.legend.location = "top_left"

    script, div = components(p)

    return render_template("bokehgraph.html", script=script, div=div)


@app.route("/_dispersionWaveguide", methods=['GET', 'POST'])
@login_required
def _dispersionWaveguide():

    gamma = float(request.values.get('gamma'))*1e9*2*np.pi
    mu0 = 4*np.pi*1e-7
    if int(request.values.get('MsatUnits')) == 0:
        Msat = float(request.values.get('Msat'))
    elif int(request.values.get('MsatUnits')) == 1:
        Msat = float(request.values.get('Msat'))/mu0
    elif int(request.values.get('MsatUnits')) == 2:
        Msat = float(request.values.get('Msat'))*1e3
    # Conversion of field
    if int(request.values.get('extFieldUnits')) == 0:
        H0 = float(request.values.get('extField'))*1e-3/mu0
    elif int(request.values.get('extFieldUnits')) == 1:
        H0 = float(request.values.get('extField'))/mu0
    elif int(request.values.get('extFieldUnits')) == 2:
        H0 = float(request.values.get('extField'))*1e-4/mu0
    elif int(request.values.get('extFieldUnits')) == 3:
        H0 = float(request.values.get('extField'))*79.57747154594
    elif int(request.values.get('extFieldUnits')) == 4:
        H0 = float(request.values.get('extField'))
    if int(request.values.get('exchangeUnits')) == 0:
        A = float(request.values.get('exchange'))
        # A = float(request.values.get('exchange'))*Msat/2
    elif int(request.values.get('exchangeUnits')) == 1:
        A = float(request.values.get('exchange'))
    d = float(request.values.get('thickness'))*1e-9
    weff = float(request.values.get('weff'))
    phi = np.deg2rad(float(request.values.get('phi')))
    phiDeg = float(request.values.get('phi'))
    theta = np.deg2rad(float(request.values.get('theta')))
    thetaDeg = int(request.values.get('theta'))
    n = int(request.values.get('n'))
    nT = int(request.values.get('nT'))
    boundaryCond = int(request.values.get('boundaryCond'))
    kxiStart = float(request.values.get('kxiStart'))*1e6
    kxiStop = float(request.values.get('kxiStop'))*1e6
    kxiPoints = float(request.values.get('kxiPoints'))
    print(d)
    w0 = -gamma*mu0*H0
    wM = -gamma*mu0*Msat

    kxi = np.linspace(start=kxiStart, stop=kxiStop, num=kxiPoints)
    
    material = SWT.Material(Aex = A, Ms = Msat, gamma = gamma*2*np.pi*1e9, alpha = 5e-3)
    DispObjDE = SWT.DispersionCharacteristic(kxi = kxi, theta = theta, phi = np.deg2rad(90), d = d, boundaryCond = 1, dp = 1e6, Bext = H0/mu0, material = material)
    DispObjBV = SWT.DispersionCharacteristic(kxi = kxi, theta = theta, phi = 0, d = d, boundaryCond = 1, dp = 1e6, Bext = H0/mu0, material = material)
    DispObjC = SWT.DispersionCharacteristic(kxi = kxi, theta = theta, phi = phi, d = d, boundaryCond = 1, dp = 1e6, Bext = H0/mu0, material = material)

    # Damon-Eshbach - 00
    fDE =  DispObjDE.GetDispersion(n=0)*1e-9/(2*np.pi) 
    # Backward volume - 00
    fBV =  DispObjBV.GetDispersion(n=0)*1e-9/(2*np.pi) 
    # Custom
    fc =  DispObjC.GetDispersion(n=0)*1e-9/(2*np.pi) 

    # fklas = np.sqrt(w0*(wM + w0) + np.power(wM,2)/4*(1 - np.exp(-2*kxi*d)))/np.pi/2

    TOOLTIPS = [
    ("k:", "$x rad/um"),
    ("f:", "$y GHz")
    ]
    p = figure(title="Dispersion relation - theta = " + str(thetaDeg) + "°", x_axis_label='k (rad/um)', y_axis_label='Frequency (GHz)', tooltips=TOOLTIPS)
    p.line(kxi/1e6, fDE/1e9, legend="Damon-Eshbach - n = 0", line_width=3)
    p.line(kxi/1e6, fBV/1e9, legend="Backward volume - n = 0", line_width=3, line_color="red")
    p.line(kxi/1e6, fc/1e9, legend="Phi = " + str(phiDeg) + " - n = "+ str(n) + "", line_width=3, line_color="black")
    # p.line(kxi, fPIN, legend="Pinned", line_width=3, line_color="green")
    # p.line(kxi, fDEKlas, legend="Klasika", line_width=3, line_color="brown")
    p.legend.location = "top_left"
    p.extra_y_ranges['Energy'] = Range1d(0, 100)
    p.add_layout(LinearAxis(y_range_name="Energy", axis_label='Energy (eV)'), 'right')

    ticksWavelength = [2*np.pi/(i+0.00000000000000000000000001) for i in kxi]
    p.extra_x_ranges['Wavelength'] = Range1d(0, max(kxi))
    p.add_layout(LinearAxis(x_range_name="Wavelength", axis_label='Wavelength (μm)'), 'above')
    p.xaxis[0].ticker    = FixedTicker(ticks=ticksWavelength)
    p.xaxis[0].ticker    = AdaptiveTicker(min_interval=0.5)

    script, div = components(p)

    return render_template("bokehgraph.html", script=script, div=div, kxis=kxi, fcs=fc)

@app.route("/labSensor/", methods=['GET', 'POST'])
@login_required
def labSensor():
    form = LabSensorDay()
    if form.validate_on_submit() and os.path.exists('M:\\Henry setup\\Arduino_Thermometer\\' + form.day.data.strftime('%#m-%#d-%Y') + '.txt'):
            with open('M:\\Henry setup\\Arduino_Thermometer\\' + form.day.data.strftime('%#m-%#d-%Y') + '.txt', newline = '') as sensorDataRaw:                                                                                          
                sensorDataDF = pd.read_csv(sensorDataRaw,parse_dates=[0])
                source = ColumnDataSource(sensorDataDF)
    elif not form.validate_on_submit() and os.path.exists('M:\\Henry setup\\Arduino_Thermometer\\' + datetime.today().strftime('%#m-%#d-%Y') + '.txt'):
        with open('M:\\Henry setup\\Arduino_Thermometer\\' + datetime.today().strftime('%#m-%#d-%Y') + '.txt', newline = '') as sensorDataRaw:                                                                                          
            sensorDataDF = pd.read_csv(sensorDataRaw,parse_dates=[0])
            source = ColumnDataSource(sensorDataDF)
    else:
        script, div = ['','']
        flash(f'This day is not measured!', 'warning')
        return render_template("labsensor.html", title="Tools - lab sensors", script=script, div=div, form=form)

    pt = figure(x_axis_type='datetime',title=' Temperature', x_axis_label='Time', y_axis_label='Temperature (°C)')
    hover = HoverTool()
    hover.tooltips=[
    (' Temperature', '@Temperature'),
    (' Humidity', '@Humidity'),
    (' Dust density ', '@{Dust density}'),
    ]

    pt.add_tools(hover)
    pt.line(x='Time', y='Temperature',source=source, line_width=3, legend=" Temperature", color='black')



    ph = figure(x_axis_type='datetime',title=' Humidity', x_axis_label='Time', y_axis_label='Humidity (°C)')
    hover = HoverTool()
    hover.tooltips=[
    (' Temperature', '@Temperature'),
    (' Humidity', '@Humidity'),
    (' Dust density ', '@{Dust density}'),
    ]

    ph.add_tools(hover)
    ph.line(x='Time', y='Humidity',source=source, line_width=3, legend=" Humidity", color='black')

    pdd = figure(x_axis_type='datetime',title=' Dust density', x_axis_label='Time', y_axis_label='Dust density (0-1024)')
    hover = HoverTool()
    hover.tooltips=[
    (' Temperature', '@Temperature'),
    (' Humidity', '@Humidity'),
    (' Dust density ', '@{Dust density}'),
    ]

    pdd.add_tools(hover)
    pdd.line(x='Time', y='Dust density',source=source, line_width=3, legend=" Dust density", color='black')

    p = column(pt, ph, pdd)

    script, div = components(p)


    return render_template("labsensor.html", title="Tools - lab sensors", script=script, div=div, form=form)

@app.route("/manualBasics")
def manualBasics():
    return render_template("manualBasics.html", title="Basics of LABhub")