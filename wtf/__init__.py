from __future__ import print_function, absolute_import, unicode_literals

__all__ = ["create_app"]

import flask

import logging

from .views.yelp import yelp
from .login import create_login, login_handler, logout_handler
from .error_handlers import TLSSMTPHandler


def index_view():
    return flask.render_template("index.html",
                    google_api_key=flask.current_app.config["GOOGLE_WEB_KEY"])


def create_app():
    app = flask.Flask(__name__)
    app.config.from_object("wtf.config_defaults.WTFConfig")

    # Add the blueprint(s).
    app.register_blueprint(yelp, url_prefix="/api")

    # Attach routes.
    app.add_url_rule("/", "index", index_view)
    app.add_url_rule("/login", "login", login_handler)
    app.add_url_rule("/logout", "logout", logout_handler)

    # Set up logins.
    oid, login_manager = create_login()
    oid.init_app(app)
    login_manager.setup_app(app)

    # Set up email logging.
    mail_handler = TLSSMTPHandler(("smtp.gmail.com", 587),
                                  "Lunch Robot <robot@wtfisforlunch.com>",
                                  app.config["ADMIN_EMAILS"],
                                  "WTF Failed")
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

    return app
