from __future__ import print_function, absolute_import, unicode_literals

import flask
import json

import numpy as np
import requests
from requests_oauthlib import OAuth1


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
    inds = np.random.randint(len(categories), size=10)
    cat_filter = ",".join([categories[i] for i in inds])
    print(cat_filter)
    payload = {
            "category_filter": cat_filter,
            "sort_mode": 2,
            "ll": ",".join([str(l) for l in loc[::-1]])
        }

    # Submit the search on Yelp.
    r = requests.get(api_url, params=payload, auth=auth)
    if r.status_code != requests.codes.ok:
        print(r.json())
        return json.dumps({"message":
                    "The fucking request to Yelp's servers failed."}), 404
    data = r.json()

    # Choose a restaurant.

    return json.dumps(data)
