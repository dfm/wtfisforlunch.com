from __future__ import print_function, absolute_import, unicode_literals

__all__ = ["check_login", "create_login", "login_handler", "logout_handler",
           "current_user"]

import os
import flask
from flask.ext.openid import OpenID, COMMON_PROVIDERS
import flask.ext.login as login_ext

from .models import User


oid = OpenID()


def check_login():
    return (login_ext.current_user is not None
                and login_ext.current_user.is_authenticated())


def current_user():
    if check_login():
        return login_ext.current_user
    return None


def load_user(_id):
    return User.from_id(_id)


def load_user_token(token):
    return User.from_token(token)


@oid.loginhandler
def login_handler():
    err = oid.fetch_error()
    if err is not None:
        return flask.redirect(flask.url_for(".index", error=err))

    if check_login():
        return flask.redirect(oid.get_next_url())

    return oid.try_login(COMMON_PROVIDERS["google"],
                         ask_for=["email", "fullname"])


def logout_handler():
    login_ext.logout_user()
    return flask.redirect(flask.url_for(".index"))


@oid.after_login
def after_login(resp):
    user = User.from_openid(resp.identity_url)
    if user is None:
        # Create a new user account.
        user = User.new(**{"email": resp.email,
                           "fullname": resp.fullname,
                           "token": login_ext.make_secure_token(os.urandom(4),
                                                                resp.email,
                                                                os.urandom(4)),
                           "openid": resp.identity_url})
    login_ext.login_user(user)
    return flask.redirect(oid.get_next_url())


def create_login():
    login_manager = login_ext.LoginManager()
    login_manager.login_view = ".login"
    login_manager.user_loader(load_user)
    login_manager.token_loader(load_user_token)

    return oid, login_manager
