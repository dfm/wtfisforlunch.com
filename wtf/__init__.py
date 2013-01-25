from __future__ import print_function, absolute_import, unicode_literals

__all__ = ["create_app"]

import flask
import flask.ext.login as login_ext
from flaskext.babel import Babel

import os
import logging

import redis
import pymongo

from wtf.views.foursquare import api
from wtf.login import create_login, login_handler, logout_handler
from wtf.error_handlers import TLSSMTPHandler
from wtf.models import User, Proposal


babel = Babel()


def javascript_view():
    return flask.render_template("wtf.js")


def index_view():
    user = login_ext.current_user
    if not user.is_authenticated():
        user = None
        proposal = None
    else:
        proposal = user.find_recent()
    return flask.render_template("index.html",
                    google_api_key=flask.current_app.config["GOOGLE_WEB_KEY"],
                    user=user, proposal=proposal)


def about_view():
    user = login_ext.current_user
    if not user.is_authenticated():
        user = None
    return flask.render_template("about.html")


def share_view(short_url):
    prop = Proposal.c().find_one({"short_url": short_url})
    if prop is not None:
        return flask.render_template("share.html", proposal=Proposal(prop))
    return flask.redirect(flask.url_for("index"))


def before_request():
    uri = os.environ.get("MONGOLAB_URI", "mongodb://localhost/wtflunch")
    flask.g.dbc = pymongo.Connection(host=uri)
    dbname = pymongo.uri_parser.parse_uri(uri).get("database", "wtflunch")
    flask.g.db = flask.g.dbc[dbname]

    # Indexing.
    c = User.c()
    c.ensure_index("token")
    c.ensure_index("open_id")

    c = Proposal.c()
    c.ensure_index("accepted")
    c.ensure_index("date")
    c.ensure_index("user_id")
    c.ensure_index("short_url")

    # Redis database.
    flask.g.redis = redis.StrictRedis.from_url(
            os.environ.get("REDISTOGO_URL", "redis://localhost:6379"))


def teardown_request(exception):
    flask.g.dbc.close()


def create_app():
    app = flask.Flask(__name__)
    app.config.from_object("wtf.config_defaults.WTFConfig")
    babel.init_app(app)

    # Add the blueprint(s).
    app.register_blueprint(api, url_prefix="/api")

    # Attach routes.
    app.add_url_rule("/", "index", index_view)
    app.add_url_rule("/wtf.js", "javascript", javascript_view)
    app.add_url_rule("/about", "about", about_view)
    app.add_url_rule("/login", "login", login_handler)
    app.add_url_rule("/logout", "logout", logout_handler)

    # Share urls.
    app.add_url_rule("/share/<short_url>", "share", share_view)
    app.add_url_rule("/<short_url>", "share", share_view)

    # Pre- and post-request hooks.
    app.before_request(before_request)
    app.teardown_request(teardown_request)

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
