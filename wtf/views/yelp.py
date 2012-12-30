from __future__ import print_function, absolute_import, unicode_literals

import flask
import json

import numpy as np
import requests
from requests_oauthlib import OAuth1

from wtf.geo import propose_position, lnglat2xyz, rearth
from wtf.email_utils import send_msg
from wtf.acceptance_model import AcceptanceModel


yelp = flask.Blueprint("yelp", __name__)

api_url = "http://api.yelp.com/v2/search"

google_directions_url = "http://maps.googleapis.com/maps/api/directions/json"


def get_categories():
    cats = json.load(flask.current_app
                          .open_resource("static/yelp_categories.json"))
    return [c.get("shortname") for c in cats]


@yelp.route("/")
@yelp.route("/reject/<rejectid>")
def main(rejectid=None):
    if rejectid is not None:
        pass

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
    ncategories = 5
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
        new_pos = propose_position(loc, np.sqrt(0.16))
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

    # Choose one of the restaurants.
    model = AcceptanceModel(0.16, 8.0, 3.5)

    # Loop over the list of suggestions and accept or reject stochastically.
    inds = np.arange(len(data))
    np.random.shuffle(inds)
    best = (0, None, None)
    for ind in inds:
        choice = data[ind]

        # Get the aggregate user rating.
        n0, r0 = 5, choice.get("rating", 0.0)
        nratings = choice.get("review_count", 0)
        rating = nratings * r0 / (n0 + nratings)

        # Compute the distance.
        cloc = choice["location"]["coordinate"]
        x1 = lnglat2xyz(cloc["longitude"], cloc["latitude"])
        x2 = lnglat2xyz(*loc)
        dist = np.sqrt(2 * (rearth * rearth - np.dot(x1, x2)))

        # Compute the predictive acceptance probability.
        prob = model.predict(dist, rating)
        if prob > best[0]:
            best = (prob, ind, dist)

        # Accept stochastically.
        if np.random.rand() <= prob:
            best = (prob, ind, dist)
            break

    if best[1] is None:
        # None of the restaurants had non-zero acceptance probability.
        return (json.dumps({"message":
            "We couldn't find any results. Maybe you should just stay home."}),
            404)

    choice = data[best[1]]

    # Try and get the directions.
    params = {
            "mode": "walking",
            "sensor": "false",
            "origin": "{1},{0}".format(*loc),
            "destination": "{latitude},{longitude}".format(
                                **(choice["location"]["coordinate"]))
            }
    r = requests.get(google_directions_url, params=params)
    resp = r.json()
    map_url = "http://maps.googleapis.com/maps/api/staticmap" \
                "?zoom=15&size=400x200&scale=2&sensor=false" \
                + "&markers={latitude},{longitude}" \
                    .format(**choice["location"]["coordinate"])
                # "&key=" + flask.current_app.config["GOOGLE_WEB_KEY"] \
    if r.status_code == requests.codes.ok and resp["status"] == "OK":
        # Loop over the route and build up the path to be displayed on the
        # map.
        route = resp["routes"][0]["legs"]
        path = ["{1},{0}".format(*loc)]
        for leg in route:
            path += ["{lat},{lng}".format(**(leg["start_location"]))]
            for step in leg["steps"]:
                path += ["{lat},{lng}".format(**(step["start_location"])),
                         "{lat},{lng}".format(**(step["end_location"]))]
            path += ["{lat},{lng}".format(**(leg["end_location"]))]
        path += ["{latitude},{longitude}"
                    .format(**choice["location"]["coordinate"])]

        # Build the map URL.
        map_url += "&markers=color:green|{1},{0}".format(*loc) \
                 + "&path=color:0x0000ff|weight:5|" + "|".join(path)

    return json.dumps({
            "id": choice["id"],
            "name": choice["name"],
            "categories": ", ".join([c[0] for c in choice["categories"]]),
            "reject_url": flask.url_for(".main", rejectid=choice["id"]),
            "accept_url": flask.url_for(".accept", acceptid=choice["id"]),
            "url": choice["url"],
            "rating": choice.get("rating", 0.0),
            "rating_image": choice["rating_img_url"],
            "review_count": choice["review_count"],
            "distance": best[2],
            "probability": best[0],
            "map_url": map_url
        })


@yelp.route("/accept/<acceptid>")
def accept(acceptid):
    return "Success."
