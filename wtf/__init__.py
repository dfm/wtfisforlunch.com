import flask

# from .views.yelp import yelp
from .login import create_login, login_handler


def create_app():
    app = flask.Flask(__name__)
    app.config.from_object("wtf.config_defaults.WTFConfig")

    # app.register_blueprint(yelp)

    # Attach routes.
    app.add_url_rule("/login", "login", login_handler)

    # Set up logins.
    oid, login_manager = create_login()
    oid.init_app(app)
    login_manager.setup_app(app)

    return app
