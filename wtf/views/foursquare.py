from __future__ import print_function, absolute_import, unicode_literals

import flask
import json
import urllib

import numpy as np
import requests

from wtf.geo import propose_position, lnglat2xyz, rearth
from wtf.login import current_user
from wtf.models import Proposal, FoursquareListing
from wtf.email_utils import send_msg
from wtf.acceptance_model import AcceptanceModel


api = flask.Blueprint("api", __name__)

api_url = "https://api.foursquare.com/v2/venues/explore"

google_directions_url = "http://maps.googleapis.com/maps/api/directions/json"


def get_listings(loc, sigma2):
    c = flask.current_app.config
    payload = {"client_id": c["FOURSQUARE_ID"],
               "client_secret": c["FOURSQUARE_SECRET"],
               "v": "20130111",
               "section": "food",
               "limit": 50}

    ntries = 3
    for i in range(ntries):
        # Propose a new position.
        new_pos = propose_position(loc, np.sqrt(sigma2))
        payload["ll"] = "{1},{0}".format(*new_pos)

        # Submit the search on Yelp.
        r = requests.get(api_url, params=payload)
        if r.status_code != requests.codes.ok:
            try:
                send_msg(",".join(flask.current_app.config["ADMIN_EMAILS"]),
                         flask.request.url + "\n\n"
                            + json.dumps(r.json(), indent=2),
                         "4sq API request failed.")
            except:
                pass

            return []

        data = r.json()
        if "response" not in data or "groups" not in data["response"]:
            return []

        data = data["response"]["groups"]
        listings = []
        for l in data:
            listings += [FoursquareListing(d["venue"]) for d in l["items"]]

        if len(listings) > 0:
            break

    return listings


@api.route("/")
@api.route("/reject/<rejectid>")
@api.route("/blacklist/<blackid>")
def main(rejectid=None, blackid=None):
    # Get the currently logged in user.
    user = current_user()

    # Get the acceptance model.
    # try:
    #     model = AcceptanceModel(*(user["model"]))
    # except (TypeError, KeyError):
    model = AcceptanceModel(0.2, 8.0, 1.0, 3.0)

    # Blacklist the proposal forever.
    if blackid is not None:
        if user is not None:
            proposal = Proposal.from_id(blackid)
            if proposal is not None:
                user.blacklist(proposal["id"])
                proposal.update_response(-2)

                # model.update(proposal.distance, proposal.rating,
                #              proposal.price, False, eta=0.02)
                # user.update_model(model.pars)
        else:
            rejectid = blackid

    # Reject the proposal for today.
    rediskey = "blacklist:"
    if user is None:
        h = flask.request.headers
        rediskey += h.get("X-Forwarded-For",
                          unicode(flask.request.remote_addr))
    else:
        rediskey += unicode(user._id)
    if rejectid is not None:
        proposal = Proposal.from_id(rejectid)
        if proposal is not None:
            # Update the model.
            # if user is not None:
            #     model.update(proposal.distance, proposal.rating,
            #                  proposal.price, False, eta=0.01)
            #     user.update_model(model.pars)

            # Cache the rejection.
            pipe = flask.g.redis.pipeline()
            pipe.sadd(rediskey, proposal["id"])
            pipe.expire(rediskey, 12 * 60 * 60)
            pipe.execute()

            if user is None:
                proposal.remove()
            else:
                proposal.update_response(0)

    print("model", model.pars)

    # Parse the location coordinates.
    a = flask.request.args
    if "longitude" in a and "latitude" in a:
        loc = np.array((a.get("longitude"), a.get("latitude")), dtype=float)
    else:
        return json.dumps({"code": 1,
                        "message": "You need to provide coordinates."}), 400

    # Find some yelp restaurant.
    data = get_listings(loc, model._sd2)

    if len(data) == 0:
        # We really couldn't find any results at all.
        return (json.dumps({"message":
            "We couldn't find any results. Maybe you should just stay home."}),
            404)

    # Loop over the list of suggestions and accept or reject stochastically.
    inds = np.arange(len(data))
    np.random.shuffle(inds)
    best = (0, None, None)
    for ind in inds:
        choice = data[ind]

        # Check the user blacklist.
        if user is not None:
            bl = user._doc.get("blacklist", [])
            if choice.id in bl:
                continue

        # Check the cached temporary blacklist.
        if flask.g.redis.sismember(rediskey, choice.id) != 0:
            continue

        # Get the aggregate user rating.
        n0, r0 = 5, choice.rating
        if r0 is not None:
            nratings = choice.review_count
            rating = nratings * r0 / (n0 + nratings)
        else:
            rating = None

        # Compute the distance.
        cloc = choice.location
        x1 = lnglat2xyz(cloc["longitude"], cloc["latitude"])
        x2 = lnglat2xyz(*loc)
        dist = np.sqrt(2 * (rearth * rearth - np.dot(x1, x2)))

        # Compute the predictive acceptance probability.
        prob = model.predict(dist, rating, choice.price)
        print(dist, rating, choice.price, prob)
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
    # l = choice.location
    # params = {
    #             "mode": "walking",
    #             "sensor": "false",
    #             "origin": "{1},{0}".format(*loc),
    #             "destination": "{latitude},{longitude}".format(**l)
    #         }
    # r = requests.get(google_directions_url, params=params)
    # resp = r.json()

    # Build the static map URL.
    map_params = {
            "size": "640x200",
            "zoom": 15,
            "scale": 2,
            "sensor": "false",
            "markers": "label:B|{latitude},{longitude}"
                       .format(**choice.location)
            }
    map_url = "http://maps.googleapis.com/maps/api/staticmap?" + \
              urllib.urlencode(map_params)

    result = {
        "id": choice.id,
        "name": choice.name,
        "address": choice.address,
        "url": choice.url,
        "rating": choice.rating,
        "price": choice.price,
        "categories": choice.categories,
        "probability": best[0],
        "distance": best[2],
        "map_url": map_url,
        "map_link": "http://maps.google.com/?q="
                    + urllib.quote(choice.address.encode("utf-8"))
    }

    # Save the proposal.
    if user is None:
        prop = Proposal.new(None, **result)
    else:
        prop = Proposal.new(user._id, **result)

    result["accept_url"] = flask.url_for(".accept", acceptid=prop._id)
    result["reject_url"] = flask.url_for(".main", rejectid=prop._id)
    result["blacklist_url"] = flask.url_for(".main", blackid=prop._id)

    return json.dumps(result)


@api.route("/accept/<acceptid>")
def accept(acceptid):
    # Get the current user.
    user = current_user()

    # Try to find the proposal.
    prop = Proposal.from_id(acceptid)
    if prop is None:
        return json.dumps({"message": "Unknown proposal."})

    # If not logged in, remove the proposal.
    if prop.user_id is None or user is None:
        prop.remove()
        return json.dumps({"message": "No user."})

    # Update the proposal for posterity.
    prop.update_response(1)

    # Send the email.
    text = """Hey {0.fullname},

It looks like you're heading to {1.name} at {1.address}.

For more info about this restaurant: {1.url}

Here's a goddamn map: {1.map_link}

Fucking enjoy it.

Sincerely,
The Lunch Robot
robot@wtfisforlunch.com

""".format(user, prop)

    html = """<p>Hey {0.fullname},</p>

<p>Looks like you're heading to <a href="{1.url}">{1.name}</a> for lunch
today.</p>

<p style="text-align: center;"><strong>{1.name}</strong><br>
{1.address}</p>

<p style="text-align: center;">
<a href="{1.map_link}"><img src="{1.map_url}" style="width: 640px;"></a></p>

<p>Fucking enjoy it.</p>

<p>Sincerely,<br>
The Lunch Robot<br>
<a href="mailto:robot@wtfisforlunch.com">robot@wtfisforlunch.com</a></p>

""".format(user, prop)

    try:
        send_msg("{0.fullname} <{0.email}>".format(user), text,
                 "Lunch at {0}".format(prop.name), html=html)
    except Exception as e:
        print("EMAIL ERROR: ", e)
        return json.dumps({"message": "Better luck next time."})

    return json.dumps({"message": "You got it."})


@api.route("/report/<pid>/<int:value>")
def report(pid, value):
    # Get the current user.
    user = current_user()

    # Try to find the proposal.
    prop = Proposal.from_id(pid)
    if prop is None:
        return json.dumps({"message": "Unknown proposal."})

    # If not logged in, remove the proposal.
    if prop.user_id is None or user is None:
        prop.remove()
        return json.dumps({"message": "No user."})

    url = prop.report(value)
    if url is not None:
        url = flask.url_for("share", short_url=url)

    return json.dumps({"message": "You got it.",
                       "url": url})
