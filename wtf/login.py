#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["login", "login_manager"]

import urllib
import requests

import flask
from flask.ext.login import (LoginManager, login_user, logout_user,
                             login_required)

from .utils import api_url
from .database import db
from .models import User

login = flask.Blueprint("login", __name__)

login_manager = LoginManager()
login_manager.login_view = "login.index"

auth_url = "https://foursquare.com/oauth2/authenticate"
token_url = "https://foursquare.com/oauth2/access_token"


@login_manager.user_loader
def load_user(userid):
    return User.query.filter_by(id=userid).first()


@login.route("/auth")
def authcallback():
    code = flask.request.args.get("code", None)
    if code is None:
        flask.flash("Shit! Couldn't log you in.", "error")
        return flask.redirect(flask.url_for("frontend.index"))

    # Get an OAuth token.
    params = dict(
        client_id=flask.current_app.config["FOURSQUARE_ID"],
        client_secret=flask.current_app.config["FOURSQUARE_SECRET"],
        grant_type="authorization_code",
        redirect_uri=flask.url_for(".authcallback", _external=True),
        code=code,
        v="20131113",
    )
    r = requests.post(token_url, data=params)
    if r.status_code != requests.codes.ok:
        flask.flash("Shit! Couldn't log you in.", "error")
        return flask.redirect(flask.url_for("frontend.index"))

    # Parse the response.
    data = r.json()
    token = data.get("access_token")

    # Get the user information.
    r = requests.get(api_url("users/self"),
                     params={
                         "oauth_token": token,
                         "v": "20131113",
                     })
    if r.status_code != requests.codes.ok:
        flask.flash("Shit! Couldn't log you in.", "error")
        return flask.redirect(flask.url_for("frontend.index"))

    data = r.json().get("response", {}).get("user", None)
    if data is None:
        flask.flash("Shit! Couldn't log you in.", "error")
        return flask.redirect(flask.url_for("frontend.index"))

    foursquare_id = data.get("id")
    first_name = data.get("firstName")
    last_name = data.get("lastName")
    email = data.get("contact", {}).get("email")

    if foursquare_id is None:
        flask.flash("Shit! Couldn't log you in.", "error")
        return flask.redirect(flask.url_for("frontend.index"))

    # Find the user entry if it already exists.
    user = User.query.filter_by(foursquare_id=foursquare_id).first()
    if user is None:
        user = User(foursquare_id, first_name, last_name, token, email=email)

    elif token is not None:
        user.token = token

    db.session.add(user)
    db.session.commit()

    login_user(user)

    return flask.redirect(flask.url_for("frontend.index"))


@login.route("/login")
def index():
    params = dict(
        client_id=flask.current_app.config["FOURSQUARE_ID"],
        response_type="code",
        redirect_uri=flask.url_for(".authcallback", _external=True),
        v="20131113",
    )
    return flask.redirect(auth_url + "?{0}".format(urllib.urlencode(params)))


@login.route("/logout")
@login_required
def logout():
    logout_user()
    return flask.redirect(flask.url_for("frontend.index"))
