from __future__ import print_function, absolute_import, unicode_literals

import flask


yelp = flask.Blueprint("yelp", __name__)


@yelp.route("/")
def index():
    return "SUP"
