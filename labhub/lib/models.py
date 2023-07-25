from datetime import datetime
from labhub import db, login_manager, whooshee
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    ceitec_guide = db.Column(db.String(60), nullable=True)
    log = db.relationship('Log', backref='operator', lazy=True)
    logRemark = db.relationship('LogRemark', backref='remarker', lazy=True)

    def __repr__(self):
        return f"{self.username}"

@whooshee.register_model('name', 'attribute', 'idea', 'comment', 'path')
class Log(db.Model):
    # __searchable = ['name', 'path', 'idea', 'comment', 'attribute']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    path = db.Column(db.Text)
    idea = db.Column(db.Text)
    comment = db.Column(db.Text)
    attribute  = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    setup_id = db.Column(db.Integer, db.ForeignKey('setup.id'), nullable=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('sample.id'), nullable=True)
    structure_id = db.Column(db.Integer, db.ForeignKey('structure.id'), nullable=True, default='')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=True)
    # Types ~~~~ 0 - normal log, 1 - info, 2 - warning, 3 - error, 4 - analysis ~~~~~
    typeOfOcc = db.Column(db.Integer, nullable=True) 

    def __repr__(self):
        return f"Log('{self.name}', '{self.date}')"


class LogImages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey('log.id'), nullable=False)
    title = db.Column(db.String(120))
    path = db.Column(db.Text)
    log = db.relationship('Log', backref='images', lazy=True)


    def __repr__(self):
        return f"LogImages('{self.path}', '{self.title}')"

class LogCooperators(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey('log.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    log = db.relationship('Log', backref='cooperators', lazy=True)
    user = db.relationship('Log', backref='cooperate', lazy=True)

    def __repr__(self):
        return f"{self.user_id}"

class LogRemark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey('log.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    remark = db.Column(db.Text)
    log = db.relationship('Log', backref='remarks', lazy=True)
    user = db.relationship('Log', backref='remarked', lazy=True)
    def __repr__(self):
        return f"LogRemark('{self.remark}', '{self.log_id}')"

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(130), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    idea = db.Column(db.Text)
    comment = db.Column(db.Text)
    findings = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    log = db.relationship('Log', backref='session', lazy=True)

    def __repr__(self):
        return f"Session('{self.name}', '{self.date}')"

@whooshee.register_model('name', 'desc')
class Setup(db.Model):
    # __searchable = ['name', 'desc']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(130), unique=True, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    desc = db.Column(db.Text)
    log = db.relationship('Log', backref='used_setup', lazy=True)
    attribute  = db.Column(db.Text)

    def __repr__(self):
        return f"{self.name}"

class SetupImages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setup_id = db.Column(db.Integer, db.ForeignKey('setup.id'), nullable=False)
    title = db.Column(db.String(120))
    path = db.Column(db.Text)
    setup = db.relationship('Setup', backref='images', lazy=True)


    def __repr__(self):
        return f"SetupImages('{self.path}', '{self.title}')"

class SetupFiles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setup_id = db.Column(db.Integer, db.ForeignKey('setup.id'), nullable=False)
    title = db.Column(db.String(120))
    path = db.Column(db.Text)
    setup = db.relationship('Setup', backref='files', lazy=True)


    def __repr__(self):
        return f"SetupFiles('{self.path}', '{self.title}')"

@whooshee.register_model('name', 'desc', 'attribute')
class Sample(db.Model):
    # __searchable = ['name', 'desc', 'attribute']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    desc = db.Column(db.Text)
    attribute = db.Column(db.Text)
    log = db.relationship('Log', backref='sample', lazy=True)
    structure = db.relationship('Structure', backref='sample', lazy=True)
    drawer_id = db.Column(db.Integer, db.ForeignKey('drawer.id'), nullable=True, default='')

    def __repr__(self):
        return f"{self.name}"

class SampleImages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('sample.id'), nullable=False)
    title = db.Column(db.String(120))
    path = db.Column(db.Text)
    sample = db.relationship('Sample', backref='images', lazy=True)


    def __repr__(self):
        return f"SampleImages('{self.path}', '{self.title}')"

class SampleLocations(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    sample_id = db.Column(db.Integer, db.ForeignKey('sample.id'), nullable=False)
    location = db.Column(db.String(200))
    sample = db.relationship('Sample', backref='location', lazy=True)


    def __repr__(self):
        return f"SampleLocations('{self.location}')"


class Drawer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    desc = db.Column(db.Text)
    sample = db.relationship('Sample', backref='drawer', lazy=True)
    number = db.Column(db.Integer)

    def __repr__(self):
        return f"{self.number}: {self.name}"
        

class Structure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    desc = db.Column(db.Text)
    attribute = db.Column(db.Text)
    sample_id = db.Column(db.Integer, db.ForeignKey('sample.id'), nullable=False)
    log = db.relationship('Log', backref='structure', lazy=True)
    __table_args__ = (db.UniqueConstraint('name', 'sample_id', name='unique_structure_sample'),)

    def __repr__(self):
        return f"{self.name}"

class StructureImages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    structure_id = db.Column(db.Integer, db.ForeignKey('structure.id'), nullable=False)
    title = db.Column(db.String(120))
    path = db.Column(db.Text)
    structure = db.relationship('Structure', backref='images', lazy=True)


    def __repr__(self):
        return f"StructureImages('{self.path}', '{self.title}')"

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    desc = db.Column(db.Text)
    log = db.relationship('Log', backref='project', lazy=True)
    session = db.relationship('Session', backref='project', lazy=True)

    def __repr__(self):
        return f"{self.name}"