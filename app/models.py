from flask_login import UserMixin

from app import app, db, ma, login_manager
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from passlib.apps import custom_app_context as pwd_context
from sqlalchemy_utils.functions import database_exists

@login_manager.user_loader
def load_user(userid):
    if userid is not None:
        return User.query.get(int(userid))


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))
    firstname = db.Column(db.String(80))
    lastname = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True)
    disabled = db.Column(db.Integer)
    admin = db.Column(db.Integer)
    token = db.Column(db.String(1000))

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def hash_password(self, password):
        self.password = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password)

    def __init__(self, username=None, password=None, firstname=None, lastname=None, email=None, admin=0, disabled=0,
                 token=None):
        self.username = username
        self.password = password
        self.email = email
        self.firstname = firstname
        self.lastname = lastname
        self.admin = admin
        self.disabled = disabled
        self.token = token

    def __repr__(self):
        return f"User('{self.id}', '{self.username}', '{self.email}')"


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        include_relationships = True
        load_instance = True

    id = ma.auto_field()
    username = ma.auto_field()
    password = ma.auto_field()
    firstname = ma.auto_field()
    lastname = ma.auto_field()
    email = ma.auto_field()
    disabled = ma.auto_field()
    admin = ma.auto_field()
    token = ma.auto_field()


class Notifications(db.Model):
    """
    Defines the table structure for 'notifications'. Feel free to add other columns to make the notifications more
    customizable. Just remember to update the form, template and schema to reflect the ones you add.
    """
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    channel_url = db.Column(db.String, unique=True)
    enabled = db.Column(db.Integer)
    created = db.Column(db.String)
    updated = db.Column(db.String)


class NotificationsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Notifications
        include_relationships = True
        load_instance = True

    id = ma.auto_field()
    name = ma.auto_field()
    channel_url = ma.auto_field()
    enabled = ma.auto_field()
    created = ma.auto_field()
    updated = ma.auto_field()


if not database_exists(app.config["SQLALCHEMY_DATABASE_URI"]):
    db.create_all()
    db.session.commit()
