import os
import json

import flask
from flask.ext.openid import OpenID, COMMON_PROVIDERS
import flask.ext.login as login_ext

import requests
from requests.auth import OAuth1

import pymongo

import numpy as np

from models import Resto, User


app = flask.Flask(__name__)
app.secret_key = os.environ.get("SECRET", "development secret key")

yelp_api_url = u"http://api.yelp.com/v2/search"
yelp_api_auth = OAuth1(unicode(os.environ["API_CKEY"]),
                       unicode(os.environ["API_CSEC"]),
                       unicode(os.environ["API_TOKEN"]),
                       unicode(os.environ["API_TSEC"]))

google_nearby_url = \
        u"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
google_detail_url = \
        u"https://maps.googleapis.com/maps/api/place/details/json"
google_api_key = unicode(os.environ["GOOGLE_API_KEY"])


# ==========================================================================
#                                                                USER LOGINS
# ==========================================================================

oid = OpenID()
oid_provider = COMMON_PROVIDERS["google"]
login_manager = login_ext.LoginManager()
login_manager.login_view = ".login"


@login_manager.user_loader
def load_user(_id):
    return User.from_id(_id)


@login_manager.token_loader
def load_user_token(token):
    return User.from_token(token)


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

    # Indexing.
    c = flask.g.db.users
    c.ensure_index("token")
    c.ensure_index("open_id")


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
    u = login_ext.current_user
    if u.is_authenticated() and not u.is_anonymous():
        return flask.render_template("lunch.html", user=u,
                    google_api_key=os.environ.get("GOOGLE_WEB_KEY", ""))
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
    # Load the categories.
    with app.open_resource("static/cats.json") as f:
        cats = json.load(f)

    payload = {"key": google_api_key, "sensor": "true", "types": "restaurant",
               "radius": 1500}

    # First, parse the location.
    a = flask.request.args
    print a
    if "longitude" in a and "latitude" in a:
        payload["location"] = "{0},{1}".format(a.get("latitude"),
                                               a.get("longitude"))
    else:
        return json.dumps({"code": 1,
                           "message": "The doesn't sound like a real place."})

    for i in range(5):
        try:
            cat = cats[np.random.randint(len(cats) + 2)]
            payload["keyword"] = cat[0]
        except IndexError:
            cat = None
            payload.pop("keyword", None)

        r = requests.get(google_nearby_url, params=payload)
        if r.status_code != requests.codes.ok:
            return json.dumps({"code": 2,
                            "message": "Google's API seems to be dead."})

        data = r.json

        res = data["results"]
        if len(res) > 0:
            break

    # Fail 'elegantly' if that doesn't work.
    if len(res) == 0:
        return json.dumps({"code": 2,
                           "message": "We couldn't find fuck all for you."})

    choice = res[np.random.randint(len(res))]

    res = Resto.from_id(choice.get("id", None))
    if res is None:
        payload = {"key": google_api_key, "sensor": "true",
                "reference": choice["reference"]}

        r = requests.get(google_detail_url, params=payload)
        if r.status_code != requests.codes.ok:
            return json.dumps({"code": 2,
                            "message": "Google's API seems to be dead."})

        data = r.json
        code = data["status"]
        if data["status"] != "OK":
            return json.dumps({"code": 2,
                        "message": "Google's API said: '{0}'.".format(code)})

        doc = data["result"]
        keys = ["id", "rating", "url", "name", "geometry"]
        res = Resto.new(**dict([(k, doc.get(k, None)) for k in keys]))

    return json.dumps({"category": cat[0] if cat is not None else "that",
            "_id": res._id,
            "name": u"<a href=\"{0.url}\" target=\"_blank\">{0.name}</a>"
                                                        .format(res)})


@app.route("/api/propose/<rid>")
@login_ext.login_required
def propose(rid):
    r = Resto.from_id(rid)
    if r is None:
        return json.dumps({"code": 2,
                           "message": "That place doesn't fucking exist."})
    u = login_ext.current_user
    u.propose_visit(r)
    return json.dumps({"code": 0})


if __name__ == "__main__":
    app.debug = True
    app.run()
