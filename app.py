import os
import json

import flask
from flask.ext.openid import OpenID, COMMON_PROVIDERS
import flask.ext.login as login_ext

import requests
from requests.auth import OAuth1

import pymongo
from bson.objectid import ObjectId

import numpy as np

from user import User


app = flask.Flask(__name__)
app.secret_key = os.environ.get("SECRET", "development secret key")

yelp_api_url = u"http://api.yelp.com/v2/search"
yelp_api_auth = OAuth1(unicode(os.environ["API_CKEY"]),
                       unicode(os.environ["API_CSEC"]),
                       unicode(os.environ["API_TOKEN"]),
                       unicode(os.environ["API_TSEC"]))


# ==========================================================================
#                                                                USER LOGINS
# ==========================================================================

oid = OpenID()
oid_provider = COMMON_PROVIDERS["google"]
login_manager = login_ext.LoginManager()
login_manager.login_view = ".login"


@login_manager.user_loader
def load_user(_id):
    c = flask.g.db.users
    u = c.find_one({"_id": ObjectId(_id)})
    if u is None:
        return None
    return User(u)


@login_manager.token_loader
def load_user_token(token):
    c = flask.g.db.users
    u = c.find_one({"token": token})
    if u is None:
        return None
    return User(u)


@app.route("/login")
@oid.loginhandler
def login():
    err = oid.fetch_error()
    if err is not None:
        return flask.redirect(flask.url_for(".index", error=err))
    if login_ext.current_user is not None \
            and login_ext.current_user.is_authenticated():
        return flask.redirect(oid.get_next_url())
    return oid.try_login(oid_provider, ask_for=["email", "fullname"])


@oid.after_login
def after_login(resp):
    c = flask.g.db.users
    u = c.find_one({"openid": resp.identity_url})
    if u is None:
        # Create a new user account.
        user = User.new(**{"email": resp.email,
                           "fullname": resp.fullname,
                           "token": login_ext.make_secure_token(os.urandom(4),
                                                                resp.email,
                                                                os.urandom(4)),
                           "openid": resp.identity_url})
    else:
        user = User(u)
    login_ext.login_user(user)
    return flask.redirect(oid.get_next_url())


@app.route("/logout")
@login_ext.login_required
def logout():
    login_ext.logout_user()
    return flask.redirect(flask.url_for(".index"))


# ==========================================================================
#                                                           PRE/POST REQUEST
# ==========================================================================

@app.before_request
def before_request():
    uri = os.environ.get("MONGOLAB_URI", "mongodb://localhost/wtflunch")
    flask.g.dbc = pymongo.Connection(host=uri)
    dbname = pymongo.uri_parser.parse_uri(uri).get("database", "wtflunch")
    flask.g.db = flask.g.dbc[dbname]


@app.teardown_request
def teardown_request(exception):
    flask.g.dbc.close()


# Crazy as it sounds, this MUST be **here**. :-|
login_manager.setup_app(app)


# ==========================================================================
#                                                                 APP ROUTES
# ==========================================================================

@app.route("/")
def index():
    return flask.render_template("over.html")

    u = login_ext.current_user
    if u.is_authenticated() and not u.is_anonymous():
        return flask.render_template("lunch.html", user=u,
                    google_api_key=os.environ.get("GOOGLE_API_KEY", ""))
    return flask.render_template("splash.html")


@app.route("/about")
def about():
    return flask.render_template("about.html")


# ==========================================================================
#                                                                    THE API
# ==========================================================================

@app.route("/api")
@login_ext.login_required
def api():
    payload = {"sort_mode": 2}

    # First, parse the location.
    a = flask.request.args
    if "longitude" in a and "latitude" in a:
        payload["ll"] = "{0},{1}".format(a.get("latitude"), a.get("longitude"))
        if "accuracy" in a:
            payload["ll"] += ",{0}".format(a.get("accuracy"))
    elif "named" in a:
        payload["location"] = a.get("named")
    else:
        return json.dumps({"code": 1,
                           "message": "You must provide a location."})

    # Load the categories.
    with app.open_resource("static/cats.json") as f:
        cats = json.load(f)

    # Try to make sure that we actually get some restaurants!
    for i in range(5):
        cat = cats[np.random.randint(len(cats))]
        payload["category_filter"] = cat[1]
        r = requests.get(yelp_api_url, params=payload, auth=yelp_api_auth)
        if r.status_code != requests.codes.ok:
            return json.dumps({"code": 2,
                               "message": "Yelp's API seems to be dead."})

        data = r.json
        if "error" in data:
            return json.dumps({"code": 2,
                               "message": "Yelp responded with: '{0}'."
                                                    .format(data["text"])})

        if int(data["total"]) > 1:
            break

    # Fail 'gracefully' if we don't find any restaurants.
    if int(data["total"]) < 1:
        return json.dumps({"code": 1,
                           "message": "Where are all the restaurants?"})

    # Get the distance, etc. for all the restaurants.
    dist, rating, count = zip(*[(r.get("distance", 0), r.get("rating", 0),
                                 r.get("review_count", 0))
                                            for r in data["businesses"]])

    choice = data["businesses"][np.random.randint(len(count))]
    return json.dumps({"category": cat[0],
            "name": u"<a href=\"{url}\" target=\"_blank\">{name}</a>"
                                                        .format(**choice)})


if __name__ == "__main__":
    app.debug = True
    app.run()
