#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__all__ = ["create_app"]

import flask
from flask.ext.login import current_user

from .login import login_manager
from .database import db


def before_request():
    if current_user is not None and not current_user.is_anonymous():
        flask.g.user = current_user
    else:
        flask.g.user = None


def create_app(config_filename=None):
    app = flask.Flask(__name__)
    app.config.from_object("wtf.default_settings")
    if config_filename is not None:
        app.config.from_pyfile(config_filename)

    # Setup database.
    db.init_app(app)

    # Setup Login.
    login_manager.init_app(app)

    # Before request.
    app.before_request(before_request)

    # Bind the blueprints.
    from .frontend import frontend
    app.register_blueprint(frontend)

    from .login import login
    app.register_blueprint(login)

    return app
