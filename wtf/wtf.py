from __future__ import print_function, absolute_import, unicode_literals

import os
import re
import json

import flask
from flask.ext.openid import OpenID, COMMON_PROVIDERS
import flask.ext.login as login_ext

import requests
from requests.auth import OAuth1

import pymongo

import numpy as np

from models import Visit, Resto, User
from model import AcceptanceModel
from email_utils import send_msg


app = flask.Flask(__name__)
app.secret_key = os.environ.get("SECRET", "development secret key")

yelp_api_url = "http://api.yelp.com/v2/search"
yelp_api_auth = OAuth1(unicode(os.environ["API_CKEY"]),
                       unicode(os.environ["API_CSEC"]),
                       unicode(os.environ["API_TOKEN"]),
                       unicode(os.environ["API_TSEC"]))

google_nearby_url = \
        u"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
google_detail_url = \
        u"https://maps.googleapis.com/maps/api/place/details/json"
google_api_key = unicode(os.environ["GOOGLE_API_KEY"])

# Google HTML parser.
price_re = re.compile(r"<span(?:.*?)>(\$+)</span>")
type_re = re.compile(r"<span(?:.*?)><span><span>(.*?)"
                     r"Restaurant(.*?)</span>")


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
    c = User.c()
    c.ensure_index("token")
    c.ensure_index("open_id")

    c = Visit.c()
    c.ensure_index("uid")
    c.ensure_index("rid")
    c.ensure_index("date")
    c.ensure_index("followed_up")
    c.ensure_index("proposed")


@app.teardown_request
def teardown_request(exception):
    flask.g.dbc.close()


# Crazy as it sounds, this MUST be **here**. :-|
login_manager.setup_app(app)


# ==========================================================================
#                                                                     ERRORS
# ==========================================================================

@app.errorhandler(500)
def got_a_500(e):
    import traceback
    tb = traceback.format_exc()
    try:
        send_msg(u"foreman.mackey@gmail.com", u"Got an error:\n\n" + tb,
                 u"WTF is the error?")
    except Exception:
        pass
    return "500", 500


# ==========================================================================
#                                                                 APP ROUTES
# ==========================================================================

@app.route("/")
def index():
    u = login_ext.current_user
    if u.is_authenticated():
        return flask.render_template("lunch.html", user=u,
                    google_api_key=os.environ.get("GOOGLE_WEB_KEY", ""),
                    visit=u.find_recent())
    return flask.render_template("splash.html")


@app.route("/lunch")
def lunch():
    return flask.render_template("lunch.html", user=None,
                google_api_key=os.environ.get("GOOGLE_WEB_KEY", ""),
                visit=None)


@app.route("/about")
def about():
    return flask.render_template("about.html")


@app.route("/magic")
def magic():
    return flask.render_template("magic.html")


@app.route("/<vid>")
def share(vid):
    v = Visit.from_id(vid)
    if v is None:
        flask.abort(404)

    try:
        uid = login_ext.current_user._id
    except AttributeError:
        pass
    else:
        if v.user._id == uid:
            v.add_rating(2)

    return flask.render_template("share.html", visit=v)


# ==========================================================================
#                                                                    THE API
# ==========================================================================

@app.route("/api")
@app.route("/api/<vid>")
def api(vid=None):
    if login_ext.current_user.is_authenticated() and vid is not None:
        v = Visit.from_id(vid)
        v.add_rating(0)
        print(v._doc)
        model = AcceptanceModel(*flask.session.get(u"model", [0.16, 8.0, 3.5]))
        print(model.pars)
        model.update(v[u"distance"], v[u"rating"], False, eta=0.05)
        print(model.pars)
        flask.session[u"model"] = list(model.pars)

    # First, parse the location.
    a = flask.request.args
    if "longitude" in a and "latitude" in a:
        loc = np.array((a.get("longitude"), a.get("latitude")), dtype=float)
    else:
        return json.dumps({"code": 1,
                           "message": "The doesn't sound like a real place."})

    res, v, dist, rating, prob = get_restaurant(loc)
    if res is None:
        return json.dumps({"code": 3,
                           "message": "We couldn't find fuck all for you."})

    return json.dumps({"vid": v._id if v is not None else None,
            "_id": res._id,
            "distance": dist, "rating": rating, "probability": prob,
            "name": u"<a href=\"{0.url}\" target=\"_blank\">{0.name}</a>"
                                                        .format(res)})


@app.route("/api/propose/<vid>")
def propose(vid):
    if not login_ext.current_user.is_authenticated():
        return json.dumps({"code": 1,
                           "message": "Why don't you log in?"})

    u = login_ext.current_user
    v = Visit.from_id(vid)
    if v is None or u._id != v.uid or v.resto is None:
        return json.dumps({"code": 2,
                           "message": "WTF happened?"})
    r = v.resto
    v.set_proposed()

    # Send the directions email.
    text = """Hey {0.fullname},

It looks like you're heading to {1.name} at {1.formatted_address}.

For more info about this restaurant: {1.url}

Fucking enjoy it.

Sincerely,
The Lunch Robot
robot@wtfisforlunch.com

""".format(u, r)

    img_url = "http://maps.googleapis.com/maps/api/staticmap?zoom=15&" \
              "size=400x200&markers={lat},{lng}&scale=2&sensor=false" \
              .format(**r.location)

    html = """<p>Hey {0.fullname},</p>

<p>Looks like you're heading to <a href="{1.url}">{1.name}</a> for lunch
today.</p>

<p style="text-align: center;"><strong>{1.name}</strong><br>
{1.formatted_address}</p>

<p style="text-align: center;"><img src="{2}" style="width: 400px;"></p>

<p>Fucking enjoy it.</p>

<p>Sincerely,<br>
The Lunch Robot<br>
<a href="mailto:robot@wtfisforlunch.com">robot@wtfisforlunch.com</a></p>

""".format(u, r, img_url)

    try:
        send_msg("{0.fullname} <{0.email}>".format(u), text,
                 "Lunch at {0}".format(r.name), html=html)
    except Exception as e:
        print("EMAIL ERROR: {0}".format(e))
        return json.dumps({"code": 2,
                        "message": "I couldn't send you a fucking reminder."})

    return json.dumps({"code": 0})


@app.route("/api/update/<vid>/<int:val>")
@login_ext.login_required
def update_visit(vid, val):
    v = Visit.from_id(vid)
    if v is None or v.uid != login_ext.current_user._id:
        return "Failure"
    v.add_rating(val)
    return "Success"


# ==========================================================================
#                                                                      MAGIC
# ==========================================================================

rearth = 6378.1  # km


def lnglat2xyz(lng, lat):
    lng, lat = np.radians(lng), np.radians(lat)
    clat = np.cos(lat)
    return rearth * np.array([clat * np.cos(lng),
                              clat * np.sin(lng),
                              np.sin(lat)])


def xyz2lnglat(xyz):
    return np.degrees(np.arctan2(xyz[1], xyz[0])), \
           np.degrees(np.arctan2(xyz[2], np.sqrt(np.dot(xyz[:-1], xyz[:-1]))))


def propose_position(ll0, sigma):
    x = lnglat2xyz(*ll0) + sigma * np.random.randn(3)
    return xyz2lnglat(x)


def get_restaurant(loc):
    u = login_ext.current_user
    if not u.is_authenticated():
        u = None

    payload = {"key": google_api_key,
               "sensor": "false",
               "types": "restaurant",
               "rankby": "distance"}

    for i in range(5):
        # Choose a random position.
        payload["location"] = "{1},{0}".format(*propose_position(loc,
                            np.sqrt(flask.session.get(u"model", [0.4])[0])))
        print(np.sqrt(flask.session.get(u"model", [0.4])[0]))

        # Do the search.
        r = requests.get(google_nearby_url, params=payload)
        if r.status_code != requests.codes.ok:
            return None

        data = r.json["results"]
        if len(data) > 0:
            break

    # Fail 'elegantly' if that doesn't work.
    if len(data) == 0:
        return None

    # Accept the proposal depending on the distance and ranking relationship.
    model = AcceptanceModel(*flask.session.get(u"model", [0.16, 8.0, 3.5]))
    thebest = (0.0, None, None)
    inds = np.arange(len(data))
    np.random.shuffle(inds)
    for i, ind in enumerate(inds):
        choice = data[ind]

        # Has the user been there before?
        if u is not None:
            v = Visit.c().find_one({"uid": u._id,
                                    "rid": choice["id"]})

        if u is None or v is None:
            # Compute the distance.
            cloc = choice["geometry"]["location"]
            x1 = lnglat2xyz(cloc["lng"], cloc["lat"])
            x2 = lnglat2xyz(*loc)
            dist = np.sqrt(2 * (rearth * rearth - np.dot(x1, x2)))

            # And the rating.
            rating = choice.get("rating", 0.0)

            # Compute the probability.
            rnd = np.random.rand()
            prob = model.predict(dist, rating)

            if prob > thebest[0]:
                thebest = (prob, choice, dist)

            if rnd <= prob:
                thebest = (0, None, None)
                break
        else:
            prob, choice = 0, None

    # Despite our best efforts we couldn't find anything... have you been too
    # many places?
    if choice is None:
        return None

    # HACK: If nothing was _actually_ accepted choose the one with the
    # highest probability.
    if thebest[1] is not None:
        prob, choice, dist = thebest

    # Is the restaurant cached?
    restaurant = Resto.from_id(choice["id"])

    # If not, fetch the details.
    if restaurant is None:
        pld = {"key": google_api_key, "sensor": "false",
                "reference": choice["reference"]}

        r = requests.get(google_detail_url, params=pld)
        if r.status_code != requests.codes.ok:
            return None

        details = r.json
        if details["status"] != "OK":
            return None

        details = details["result"]

        # Extract the fields.
        fields = ["name", "url", "formatted_address", "rating", "website",
                    "opening_hours", "formatted_phone_number", "id"]
        doc = dict([(k, details.get(k, None)) for k in fields])
        doc["location"] = details.get("geometry", {}).get("location", None)

        restaurant = Resto.new(**doc)

    # Build the new visit proposal.
    visit = None
    if u is not None:
        visit = u.new_suggestion(restaurant, dist,
                                 restaurant.get(u"rating", 0.0), prob)

    return restaurant, visit, dist, rating, prob


if __name__ == "__main__":
    app.debug = True
    app.run()
