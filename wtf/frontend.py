#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["frontend"]

import flask

import requests
from math import exp
from random import random

from .database import db
from .utils import api_url
from .geo import propose_position
from .models import Venue, Category
from .acceptance import AcceptanceModel

frontend = flask.Blueprint("frontend", __name__)


@frontend.route("/")
def index():
    return flask.render_template("index.html")


@frontend.route("/new")
def new():
    # Parse the latitude and longitude.
    lat, lng = flask.request.args.get("lat"), flask.request.args.get("lng")
    if lat is None or lng is None:
        return flask.redirect(flask.url_for(".index"))

    # Cast the latitude and longitude as floats.
    try:
        lat, lng = float(lat), float(lng)
    except ValueError:
        return flask.redirect(flask.url_for(".index"))

    # Get some proposed coordinates.
    new_lat, new_lng = propose_position(lat, lng, 0.5)

    # Get some recommendations.
    params = dict(
        ll="{0},{1}".format(new_lat, new_lng),
        section="food",
        v="20131113",
        openNow=1,
        results=50,
    )
    if flask.g.user is not None:
        params["oauth_token"] = flask.g.user.token
    else:
        params["client_id"] = flask.current_app.config["FOURSQUARE_ID"]
        params["client_secret"] = flask.current_app.config["FOURSQUARE_SECRET"]
    r = requests.get(api_url("venues/explore"), params=params)
    if r.status_code != requests.codes.ok:
        flask.flash("Foursquare is always down. Fuck.", "error")
        return flask.redirect(flask.url_for(".index"))

    # Get the currently rejected venues.
    rejected = flask.request.cookies.get("rejected", "").split()
    rej = flask.request.args.get("reject")
    if rej is not None and rej not in rejected:
        rejected.append(rej)

    # Get the blacklisted venues.
    blacklisted = []
    if flask.g.user is not None:
        blacklisted = [v.foursquare_id for v in flask.g.user.blacklist]
        bl = flask.request.args.get("blacklist")
        if bl is not None and bl not in blacklisted:
            blacklisted.append(bl)
            v = Venue.query.filter_by(foursquare_id=bl).first()
            if v is not None:
                flask.g.user.blacklist.append(v)
                db.session.add(flask.g.user)
                db.session.commit()

    # Parse the venues.
    data = r.json()
    full_reject = set(blacklisted + rejected)
    venues = [i.get("venue") for group in data["response"]["groups"]
              for i in group["items"]
              if i["venue"]["id"] not in full_reject]
    if not len(venues):
        resp = flask.make_response(flask.render_template("noresults.html"))
        if len(rejected):
            resp.set_cookie("rejected", " ".join(rejected))
        return resp

    # Compute the acceptance probabilities of the venues.
    model = AcceptanceModel(0.5, 2.0, 1.0, 2.0)
    probabilities = []
    for venue in venues:
        price = venue.get("price", {}).get("tier")
        rating = venue.get("rating")
        loc = venue["location"]
        distance = loc["distance"] / 1000
        probabilities.append(exp(model.lnlike(distance, rating, price)))

    # Select a venue by simulating a multinomial distribution.
    norm = sum(probabilities)
    cumsum = 0
    r = random()
    for i, p in enumerate(probabilities):
        cumsum += p / norm
        if cumsum > r:
            break
    venue_dict = venues[i]
    distance = venue_dict["location"]["distance"]

    # Add the venue to the database.
    venue = Venue.query.filter_by(foursquare_id=venue_dict["id"]).first()
    if venue is None:
        # Get the full listing.
        [params.pop(k) for k in ["ll", "section", "openNow", "results"]]
        r = requests.get(api_url("venues/"+venue_dict["id"]), params=params)
        if r.status_code != requests.codes.ok:
            flask.flash("Foursquare is always down. Fuck.", "error")
            return flask.redirect(flask.url_for(".index"))
        venue_dict = r.json()["response"]["venue"]

        # Parse the categories.
        categories = []
        for c in venue_dict["categories"]:
            cat = Category.query.filter_by(foursquare_id=c["id"]).first()
            if cat is None:
                cat = Category(c["id"], c["name"], c["pluralName"],
                               c["shortName"])
            categories.append(cat)

        # Set up the database entry.
        loc = venue_dict["location"]
        venue = Venue(
            venue_dict["id"],
            venue_dict["name"],
            venue_dict["shortUrl"],
            loc.get("lat"),
            loc.get("lng"),
            loc.get("address"),
            loc.get("crossStreet"),
            loc.get("city"),
            loc.get("state"),
            loc.get("country"),
            loc.get("postalCode"),
            venue_dict.get("price", {}).get("tier"),
            venue_dict.get("rating"),
            categories
        )
        db.session.add(venue)
        db.session.commit()

    resp = flask.make_response(
        flask.render_template("recommend.html",
                              venue=venue, lat=lat, lng=lng,
                              distance="about {0:.1f} miles"
                              .format(distance*0.000621371)))

    # Save the rejection cookie.
    if len(rejected):
        resp.set_cookie("rejected", " ".join(rejected))

    return resp
