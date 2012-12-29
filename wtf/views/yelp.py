from __future__ import print_function, absolute_import, unicode_literals

import flask
import json

import numpy as np
import requests
from requests_oauthlib import OAuth1

from wtf.geo import propose_position
from wtf.email_utils import send_msg


yelp = flask.Blueprint("yelp", __name__)

api_url = "http://api.yelp.com/v2/search"


def get_categories():
    cats = json.load(flask.current_app
                          .open_resource("static/yelp_categories.json"))
    return [c.get("shortname") for c in cats]


@yelp.route("/")
def main():
    # Parse the location coordinates.
    a = flask.request.args
    if "longitude" in a and "latitude" in a:
        loc = np.array((a.get("longitude"), a.get("latitude")), dtype=float)
    else:
        return json.dumps({"code": 1,
                        "message": "You need to provide coordinates."}), 400

    # The Yelp API authentication credentials.
    c = flask.current_app.config
    auth = OAuth1(c["YELP_API_CKEY"],
                  client_secret=c["YELP_API_CSEC"],
                  resource_owner_key=c["YELP_API_TOKEN"],
                  resource_owner_secret=c["YELP_API_TSEC"])

    # Build the Yelp search.
    categories = get_categories()
    payload = {
            "sort_mode": 2,
        }

    ntries = 3
    ncategories = 10
    for i in range(ntries):
        if i < ntries - 1:
            # Randomly select some categories.
            inds = np.random.randint(len(categories), size=ncategories)
            cat_filter = ",".join([categories[ind] for ind in inds])
            payload["category_filter"] = cat_filter
        else:
            # We've tried too many times. Just search all restaurants.
            payload["category_filter"] = "restaurants"

        # Propose a new position.
        new_pos = propose_position(loc, np.sqrt(0.4))
        payload["ll"] = "{1},{0}".format(*new_pos)

        # Submit the search on Yelp.
        r = requests.get(api_url, params=payload, auth=auth)
        if r.status_code != requests.codes.ok:
            try:
                send_msg(",".join(flask.current_app.config["ADMIN_EMAILS"]),
                         flask.request.url + "\n\n"
                            + json.dumps(r.json(), indent=2),
                         "Yelp API request failed.")
            except:
                pass

            return json.dumps({"message":
                    "We couldn't find any results. "
                    "Maybe you should just stay home."}), 404

        data = r.json()["businesses"]

        if len(data) > 0:
            break

    if len(data) == 0:
        # We really couldn't find any results at all.
        return (json.dumps({"message":
            "We couldn't find any results. Maybe you should just stay home."}),
            404)

    return json.dumps(data)
