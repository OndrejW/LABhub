#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import IntegerField, TextField, PasswordField, DateTimeField, BooleanField, TextAreaField, SelectField, SubmitField, StringField, MultipleFileField, FieldList, FormField, HiddenField, SelectMultipleField, RadioField, FloatField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.widgets import HiddenInput
from wtforms.validators import NumberRange, DataRequired, Length, Optional, Email, EqualTo, ValidationError, Regexp
from labhub.lib.models import User, Setup, Sample, Project, Structure, Session, Log, Drawer
from flask_login import current_user
from wtforms.fields.html5 import DateField
from datetime import datetime

class NonValidatingSelectField(SelectField):
    def pre_validate(self, form):
        pass

class LrManipulateForm(FlaskForm):
    """
    Class validating all lr operations (adding to/moving in/deleting from queue etc.)
    """
    lr_number = IntegerField("lr_number", [DataRequired(), NumberRange(min=0)], widget=HiddenInput())


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    """
    Class validating register of user.
    """
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

class UpdateAccountForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')

def setup_choices():      
    return Setup.query.all()
def sample_choices():      
    return Sample.query.all()
def structure_choices():      
    return Structure.query.all()
def project_choices():      
    return Project.query.all()
def drawer_choices():      
    return Drawer.query.all()
def user_choices():      
    return User.query.all()


class Attribute(FlaskForm):
    """
    Class validating creation of attributes for Sample
    """    
    attrName = TextField("Name of attribute", validators=[Length(max=80), Regexp(regex=r'^[^,]+$') ])
    attrValue = TextField("Value of attribute", validators=[Length(max=80), Regexp(regex=r'^$|^[^,]+$')])
    # From strange reasons csfr doesn't work for subform
    class Meta:
        csrf = False

class AddMeasurementLog(FlaskForm):
    """
    Class validating creation of new measurement log.
    """    
    nameOfMeasurement = TextField("name of log", validators=[Length(min=2, max=120), DataRequired()])
    project = QuerySelectField("project", query_factory=project_choices, allow_blank=True, blank_text=u"Select project")
    setup = QuerySelectField("setup", validators=[DataRequired()], query_factory=setup_choices)
    sample = QuerySelectField("sample", query_factory=sample_choices, allow_blank=True, blank_text=u"Select sample")
    structure = TextField("structure", validators=[Length(max=120)])
    idea = TextAreaField("idea", validators=[Length(max=10485760)])
    comment = TextAreaField("comment", validators=[Length(max=10485760)])
    path = TextAreaField("path", validators=[Length(max=10485760)])
    attr = FieldList(FormField(Attribute))
    cooperator = SelectMultipleField("Co-operator", choices=[], coerce=int)
    session = NonValidatingSelectField("session", choices=[])
    submit = SubmitField("Submit log")
    hid = HiddenField("hid")

    def validate_session(self, field):
        if hasattr(self.project.data, 'id'):
            session = Session.query.filter_by(project_id = self.project.data.id, id = self.session.data).first()
            if not session and self.session.data != "":
                raise ValidationError("This is not valid session for selected project.")
    # def validate_nameOfMeasurement(self, nameOfMeasurement):
    #     log = Log.query.filter_by(name=nameOfMeasurement.data, session_id=self.session.data, session_id!=).first()
    #     if log and not (self.hid.data != log.id):
    #         raise ValidationError('This name of measurement is already used in this session.')

class addRemarkToLog(FlaskForm):
    """
    Class validating creation of new sample
    """    
    remark = TextAreaField("Remark", validators=[Length(min=2, max=2000), DataRequired()])
    submit = SubmitField("Add remark")

class AddOccasion(FlaskForm):
    """
    Class validating creation of new measurement log.
    """    
    name = TextField("name of note", validators=[Length(min=2, max=120), DataRequired()])
    project = QuerySelectField("project", query_factory=project_choices, allow_blank=True, blank_text=u"Select project")
    setup = QuerySelectField("setup", validators=[DataRequired()], query_factory=setup_choices)
    sample = QuerySelectField("sample", query_factory=sample_choices, allow_blank=True, blank_text=u"Select sample")
    structure = TextField("structure", validators=[Length(max=120)])
    desc = TextAreaField("description", validators=[Length(max=10485760)])
    session = NonValidatingSelectField("session", choices=[])
    attr = FieldList(FormField(Attribute))
    typeOfOcc = RadioField("type",default=1, validators=[DataRequired()], choices=[('1','Info'), ('2','Warning'), ('3','Error')])
    cooperator = SelectMultipleField("Co-operator", choices=[], coerce=int)
    hid = HiddenField("hid")
    submit = SubmitField("submit note")

    def validate_session(self, field):
        if hasattr(self.project.data, 'id'):
            session = Session.query.filter_by(project_id = self.project.data.id, id = self.session.data).first()
            if not session and self.session.data != "":
                raise ValidationError("This is not valid session for selected project.")

class AddSetup(FlaskForm):
    """
    Class validating creation of new measurement log.
    """    
    name = TextField("name of setup", validators=[Length(min=2, max=120), DataRequired()])
    desc = TextAreaField("Description", validators=[Length(max=10485760)])
    attr = FieldList(FormField(Attribute))
    idHid = HiddenField("idS")
    manuals = FileField("Manuals", validators=[FileAllowed(['pdf', 'pptx'])])
    manualsName = TextField("Name of file", validators=[Length(max=120)])
    submit = SubmitField("Add setup")

    def validate_name(self, name):
            setup = Setup.query.filter_by(name=name.data).first()
            if setup and not (self.idHid.data != setup.id):
                raise ValidationError('This setup already exists.')

class AddSample(FlaskForm):
    """
    Class validating creation of new sample
    """    
    name = TextField("name of sample", validators=[Length(min=2, max=42), DataRequired()])
    desc = TextAreaField("Description", validators=[Length(max=10485760)])
    attr = FieldList(FormField(Attribute))
    drawer = QuerySelectField("drawer", query_factory=drawer_choices, allow_blank=True, blank_text=u"Select drawer")
    idHid = HiddenField("idS")
    submit = SubmitField("Submit sample")


    def validate_name(self, name):
            sample = Sample.query.filter_by(name=name.data).first()
            if sample and not (self.idHid.data != sample.id):
                raise ValidationError('Sample with this name already exists.')

class AddLocationSample(FlaskForm):
    """
    Class validating creation of new sample
    """    
    location = TextField("location of sample", validators=[Length(min=2, max=200), DataRequired()])
    submit = SubmitField("Add location of sample")

class AddDrawer(FlaskForm):
    """
    Class validating creation of new sample
    """    
    name = TextField("name of drawer", validators=[Length(min=1, max=42), DataRequired()])
    desc = TextAreaField("Description", validators=[Length(max=10485760)])
    submit = SubmitField("Submit drawer")
    idHid = HiddenField("idD")
    number = IntegerField("number of drawer")


    def validate_name(self, name):
            drawer = Drawer.query.filter_by(name=name.data).first()
            if drawer and not (self.idHid.data != drawer.id):
                raise ValidationError('Drawer with this name already exists.')

class AddStructure(FlaskForm):
    """
    Class validating creation of new sample
    """
    sample = QuerySelectField("sample", validators=[DataRequired()], query_factory=sample_choices)     
    name = TextField("name of structure", validators=[Length(min=2, max=42), DataRequired()])
    desc = TextAreaField("Description", validators=[Length(max=10485760)])
    attr = FieldList(FormField(Attribute))
    idHid = HiddenField("idS")
    submit = SubmitField("Submit structure")


    def validate_name(self, name):
            structure = Structure.query.filter_by(name=name.data, sample_id=self.sample.data.id).first()
            print((self.idHid.data.isdigit() and self.idHid.data != '0'))
            if (structure and not (self.idHid.data != structure.id)) or (not (self.idHid.data.isdigit() and self.idHid.data != '0')  and structure):
                raise ValidationError('Structure with this name already exists.')

class AddProject(FlaskForm):
    """
    Class validating creation of new measurement log.
    """    
    name = TextField("name of project", validators=[Length(min=2, max=42), DataRequired()])
    desc = TextAreaField("Description", validators=[Length(max=10485760)])
    submit = SubmitField("Add project")
    idHid = HiddenField("idS")

    def validate_name(self, name):
        project = Project.query.filter_by(name=name.data).first()
        if project and not (self.idHid.data != project.id):
            raise ValidationError('Project with this name already exists.')

class AddSession(FlaskForm):
    """
    Class validating creation of new measurement log.
    """    
    name = TextField("name of session", validators=[Length(min=2, max=120), DataRequired()])
    idea = TextAreaField("Idea", validators=[Length(max=10485760)])
    comment = TextAreaField("Comment", validators=[Length(max=10485760)])
    findings = TextAreaField("Findings", validators=[Length(max=10485760)])
    project = QuerySelectField("project", validators=[DataRequired()], query_factory=project_choices)
    submit = SubmitField("Submit session")

    def validate_name(self, name):
        project = Project.query.filter_by(name=name.data).first()
        if project:
            raise ValidationError('Project with this name already exists.')

class FilterSession(FlaskForm):
    """
    Class validating creation of new measurement log.
    """    
    project = QuerySelectField("project", validators=[DataRequired()], query_factory=project_choices, allow_blank=True, blank_text=u"Select project")
    setup = QuerySelectField("setup", validators=[DataRequired()], query_factory=setup_choices, allow_blank=True, blank_text=u"Select setup")
    sample = QuerySelectField("sample", validators=[DataRequired()], query_factory=sample_choices, allow_blank=True, blank_text=u"Select sample")

    def validate_name(self, name):
        project = Project.query.filter_by(name=name.data).first()
        if project:
            raise ValidationError('Project with this name already exists.')

class FilterLogs(FlaskForm):
    """
    Class validating creation of new measurement log.
    """    
    project = QuerySelectField("project", validators=[DataRequired()], query_factory=project_choices, allow_blank=True, blank_text=u"Select project")
    setup = QuerySelectField("setup", validators=[DataRequired()], query_factory=setup_choices, allow_blank=True, blank_text=u"Select setup")
    sample = QuerySelectField("sample", validators=[DataRequired()], query_factory=sample_choices, allow_blank=True, blank_text=u"Select sample")
    ftSearch = TextField("full text sreach", validators=[Length(min=3, max=100)])
    session = NonValidatingSelectField("session", choices=[])
    user = QuerySelectField("user", validators=[DataRequired()], query_factory=user_choices, allow_blank=True, blank_text=u"Select user")
    structure = NonValidatingSelectField("session", choices=[])


    def validate_session(self, field):
        session = Session.query.filter_by(project_id = self.project.data.id, id = self.session.data).first()
        if not session and self.session.data != "":
            raise ValidationError("This is not valid session for selected project.")

    def validate_name(self, name):
        project = Project.query.filter_by(name=name.data).first()
        if project:
            raise ValidationError('Project with this name already exists.')

class FilterSamples(FlaskForm):
    """
    Class validating creation of new measurement log.
    """    
    project = QuerySelectField("project", validators=[DataRequired()], query_factory=project_choices, allow_blank=True, blank_text=u"Select project")
    ftSearch = TextField("full text sreach", validators=[Length(min=3, max=100)])

class LimitOccs(FlaskForm):
    """
    Class validating creation of new measurement log.
    """    
    limit = RadioField("type",default=25, validators=[DataRequired()], choices=[('5','5'), ('25','25'), ('100','100')])

class Dispersion(FlaskForm):
    """
    Class validating creation of new measurement log.
    """    
    Msat = FloatField("Saturation magnetization", validators=[DataRequired()], default=170000)
    MsatUnits = SelectField("Saturation field", validators=[DataRequired()], choices=[(0, 'A/m'), (1, 'T'), (2, 'emu/cm3')])
    extField = FloatField("External field", validators=[DataRequired()], default=50)
    extFieldUnits = SelectField("External field", validators=[DataRequired()], choices=[(0, 'mT'), (1, 'T'), (2, 'G'), (3, 'Oe'), (4, 'A/m')])
    thickness = FloatField("Thickness", validators=[DataRequired()], default=10)
    exchange = FloatField("Exchange stiffness/exchange constant", validators=[DataRequired()], default=11e-12)
    exchangeUnits = SelectField("Exchange", validators=[DataRequired()], choices=[(0, 'J/m'), (1, 'JA/m2')])
    gamma = FloatField("Gyromagnetic ratio", validators=[DataRequired()], default=29.15)
    phi = FloatField("Phi (in-plane angle - DE is 90 deg)", validators=[DataRequired()], default=45)
    theta = FloatField("Theta (out-of-plane angle - in plane magnetization is 90 deg)", validators=[DataRequired()], default=90)
    n = FloatField("n", validators=[DataRequired()], default=0)

class DispersionWaveguide(FlaskForm):
    """
    Class validating creation of new measurement log.
    """    
    Msat = FloatField("Saturation magnetization", validators=[DataRequired()], default=170000)
    MsatUnits = SelectField("Saturation field", validators=[DataRequired()], choices=[(0, 'A/m'), (1, 'T'), (2, 'emu/cm3')])
    extField = FloatField("External field", validators=[DataRequired()], default=50)
    extFieldUnits = SelectField("External field", validators=[DataRequired()], choices=[(0, 'mT'), (1, 'T'), (2, 'G'), (3, 'Oe'), (4, 'A/m')])
    thickness = FloatField("Thickness", validators=[DataRequired()], default=10)
    exchange = FloatField("Exchange stiffness/exchange constant", validators=[DataRequired()], default=11e-12)
    exchangeUnits = SelectField("Exchange", validators=[DataRequired()], choices=[(0, 'J/m'), (1, 'JA/m2')])
    gamma = FloatField("Gyromagnetic ratio", validators=[DataRequired()], default=29.15)
    phi = FloatField("Phi (in-plane angle - DE is 90 deg)", validators=[DataRequired()], default=45)
    theta = FloatField("Theta (out-of-plane angle - in plane magnetization is 90 deg)", validators=[DataRequired()], default=90)
    n = FloatField("n", validators=[DataRequired()], default=0)
    weff = FloatField("Effective width of waveguide", validators=[DataRequired()], default=3)
    nT = FloatField("nW (n=0 - thin film)", validators=[DataRequired()], default=0)
    boundaryCond = SelectField("Boundary condition", validators=[DataRequired()], choices=[(0, 'Totally pinned'), (1, 'Totally unpinned')])
    kxiStart = FloatField("Start", validators=[DataRequired()], default=0)
    kxiStop = FloatField("Stop", validators=[DataRequired()], default=25)
    kxiPoints = FloatField("Points", validators=[DataRequired(), NumberRange(max=2000, min=2)], default=500)


class LabSensorDay(FlaskForm):
    """
    Class validating creation of new measurement log.
    """    
    day = DateField("Date", validators=[DataRequired()], default=datetime.today)
    submit = SubmitField("Show")