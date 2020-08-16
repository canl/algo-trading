# init.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()
basedir = os.path.abspath(os.path.dirname(__file__))


def create_app():
    app = Flask(__name__, static_url_path='', static_folder='static', template_folder='templates')

    app.config['SECRET_KEY'] = '9OLWxND4o83j4K4iuopO'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir + "/../db", 'db.sqlite')

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from src.web.models import User

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))

    # blueprint for auth routes in our app
    from src.web.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from src.web.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from src.web.api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    return app


if __name__ == '__main__':
    from src.web import db, create_app

    app = create_app()
    db.create_all(app=app)
