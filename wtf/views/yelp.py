from __future__ import print_function, absolute_import, unicode_literals

import flask
import json

import numpy as np
import requests
from requests_oauthlib import OAuth1


yelp = flask.Blueprint("yelp", __name__)

api_url = "http://api.yelp.com/v2/search"


@yelp.route("/")
def main():
    # Parse the location coordinates.
    a = flask.request.args
    if "longitude" in a and "latitude" in a:
        loc = np.array((a.get("longitude"), a.get("latitude")), dtype=float)
    else:
        return json.dumps({"code": 1,
                           "message": "You need to provide coordinates."})

    # The Yelp API authentication credentials.
    c = flask.current_app.config
    auth = OAuth1(c["YELP_API_CKEY"],
                  client_secret=c["YELP_API_CSEC"],
                  resource_owner_key=c["YELP_API_TOKEN"],
                  resource_owner_secret=c["YELP_API_TSEC"])

    # Build the Yelp search.
    payload = {
            "categories": "restaurants",
            "sort": 1,
            "ll": ",".join([str(l) for l in loc])
        }

    # Submit the search on Yelp.
    r = requests.get(api_url, params=payload, auth=auth)
    print(r.status_code)
    if r.status_code != requests.codes.ok:
        print(r.json())
        return json.dumps({"message":
                    "The fucking request to Yelp's servers failed."}), 404

    data = r.json()

    return json.dumps(data)
