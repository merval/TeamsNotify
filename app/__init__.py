from datetime import timedelta

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_httpauth import HTTPBasicAuth
from flask_login import LoginManager
from flask_mail import Mail


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database/db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "your_super_secret_key"
app.config['MAIL_SERVER'] = 'mailserver'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_TLS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)


db = SQLAlchemy(app)
migrate = Migrate(app, db, render_as_batch=True)
ma = Marshmallow(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
mail = Mail(app)
authorize = HTTPBasicAuth()



from app import routes
