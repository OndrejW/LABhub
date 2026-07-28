#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import secrets
import base64
import urllib.parse
import csv
from sqlalchemy import desc, asc, or_, func
from io import BytesIO, StringIO
from PIL import Image
from copy import copy
from flask import render_template, redirect, url_for, request, flash, jsonify, g
from flask_paginate import Pagination
from flask_login import login_user, logout_user, login_required, current_user
from flask_googlecharts import PieChart
from datetime import datetime, timedelta


from labhub import app, db, bcrypt, whooshee, charts

from labhub.lib.forms import LoginForm, AddMeasurementLog, RegistrationForm, UpdateAccountForm, AddSetup, AddSample, AddProject, Attribute, AddStructure, AddSession, FilterSession, AddOccasion, LimitOccs, AddLocationSample, FilterLogs, addRemarkToLog, AddDrawer, FilterSamples, AddAnalysis, LimitLogsUser
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

@app.route("/reindex/")
@login_required
def reindex():
    whooshee.reindex()
    form = FilterLogs()
    flash('The whooshee.reindex() was called successfully', 'success')
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
    form = LimitLogsUser()
    image_file = url_for('static', filename='profile_pics/' + user.image_file)
    # Pie chart of used setups and Projects
    involvement = or_(Log.user_id == user.id, LogCooperators.user_id == user.id)
    usedSetupsbyUser = db.session.query(Setup.name, db.func.count(db.distinct(Log.id))).join(Log, Setup.id == Log.setup_id).outerjoin(LogCooperators, LogCooperators.log_id == Log.id).filter(involvement).group_by(Setup.name).all()
    if usedSetupsbyUser:
        setupsUsedByUserChart = PieChart("setupsUsedByUserChart", options={"width": '100%', "height": 500})
        setupsUsedByUserChart.add_column("string", "Setups")
        setupsUsedByUserChart.add_column("number", "Number of measurements")
        setupsUsedByUserChart.add_rows(usedSetupsbyUser)
        charts.register(setupsUsedByUserChart)

    ProjectFromUser = db.session.query(Project.name, db.func.count(db.distinct(Log.id))).join(Log, Project.id == Log.project_id).outerjoin(LogCooperators, LogCooperators.log_id == Log.id).filter(involvement).group_by(Project.name).all()
    if ProjectFromUser:
        ProjectFromUserChart = PieChart("ProjectFromUserChart", options={"width": '100%', "height": 500})
        ProjectFromUserChart.add_column("string", "Projects")
        ProjectFromUserChart.add_column("number", "Number of records")
        ProjectFromUserChart.add_rows(ProjectFromUser)
        charts.register(ProjectFromUserChart)

    return render_template('userinfo.html', title='User info', image_file=image_file, user=user, form=form, used_setups=usedSetupsbyUser, projects=ProjectFromUser)

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
    elif log.typeOfOcc == 4:
        form=AddAnalysis()
    else:
        form = AddMeasurementLog()
    users = [(g.id, g.username) for g in User.query.order_by('username').filter(User.id != current_user.id).all()]
    form.cooperator.choices = users
    if form.validate_on_submit():
        if log.typeOfOcc != 4:
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
            log.session_id = form.session.data
            log.sample = form.sample.data
            log.used_setup = form.setup.data
            log.structure = structure
            for entry in form.attr.entries:
                attributes = attributes + entry.data['attrName'] + ',' + entry.data['attrValue'] + '\n'
                log.attribute = attributes
        elif log.typeOfOcc == 4:
            log.name = form.name.data
            log.comment = form.findings.data
            log.idea = form.idea.data
            log.path = form.path.data
        else:
            log.name = form.nameOfMeasurement.data
            log.comment = form.comment.data
            log.path = form.path.data
            log.idea = form.idea.data
            log.session_id = form.session.data
            log.sample = form.sample.data
            log.used_setup = form.setup.data
            log.structure = structure
            attributes = ''
            for entry in form.attr.entries:
                attributes = attributes + entry.data['attrName'] + ',' + entry.data['attrValue'] + '\n'
                log.attribute = attributes
        log.project = form.project.data
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
            form.hid.data = log.id
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
        elif log.typeOfOcc == 4:
            form.name.data = log.name
            form.findings.data = log.comment
            form.idea.data = log.idea
            form.path.data = log.path
        else:
            form.nameOfMeasurement.data = log.name
            form.comment.data = log.comment
            form.path.data = log.path
            form.idea.data = log.idea
            form.hid.data = log.id
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
        form.project.data = log.project
    if log.typeOfOcc == 1 or log.typeOfOcc == 2 or log.typeOfOcc == 3:
        return render_template('addoccasion.html', title='Update log', form=form, log=log, legend='Update log')
    elif log.typeOfOcc == 4:
        return render_template('addanalysis.html', title='Update analysis', form=form, log=log, legend='Update analysis')
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
    lastXdays = request.values.get('lastXdays', type=int)
    idUsr = request.values.get('idUsr')
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
    if lastXdays and lastXdays != '__None':
        X_days_ago = datetime.today() - timedelta(days = lastXdays)
        query = query.filter(Log.date >= X_days_ago)
    if idUsr and idUsr != '__None':
        query = query.filter_by(user_id=idUsr)
    query = query.order_by(desc(Log.date), desc(Log.id))
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
    form = FilterSamples()
    return render_template("listsample.html", title="List of samples", form=form)

@app.route('/_listSamplesFiltered', methods=['GET', 'POST'])
def _listSamplesFiltered():
    idProject = request.values.get('idProject')
    ftSearch = request.values.get('ftSearch')
    print(ftSearch)
    query = Sample.query
    # if idProject and idProject != '__None':
    #     query = query.filter_by(project_id=idProject)
    if ftSearch and ftSearch != '__None':
        query = query.whooshee_search(ftSearch, match_substrings=True)
    else:
        query = query.order_by(desc('date'))

    samples = query.all()
    if samples:
        return render_template("listsamplesfiltered.html", title="Filtered samples list", samples=samples)
    else:
        return 'There are not any samples yet!'

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
    # Analysis done within the project
    analyses = Log.query.order_by(desc('date')).filter_by(project_id=project.id, typeOfOcc=4)
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

    return render_template('project.html', title=project.name, project=project, sessions=sessions, samples=samplesInProj, analyses=analyses)

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
##################
# Analysis
##################
@app.route("/addAnalysis/", methods=['GET', 'POST'])
@login_required
def addAnalysis():
    form = AddAnalysis()
    users = [(g.id, g.username) for g in User.query.order_by('username').filter(User.id != current_user.id).all()]
    form.cooperator.choices = users
    if form.validate_on_submit():
        log = Log(name=form.name.data, comment=form.findings.data, operator=current_user, project=form.project.data, path=form.path.data, idea=form.idea.data, typeOfOcc=4)
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
        flash(f'Analysis was created with name: {form.name.data}!', 'success')
        return redirect(url_for('index'))
    return render_template("addanalysis.html", title="Add analysis", form=form)



@app.route("/manualBasics")
def manualBasics():
    return render_template("manualBasics.html", title="Basics of LABhub")


