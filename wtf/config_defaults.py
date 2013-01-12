from __future__ import print_function, absolute_import, unicode_literals

import os


class WTFConfig(object):

    # Flask stuff.
    SERVER_NAME = None
    SECRET_KEY = unicode(os.environ.get("SECRET", "development secret key")) \
                    .encode("utf-8")

    # Email stuff.
    ADMIN_EMAILS = ["robot@wtfisforlunch.com", ]
    EMAIL_CREDENTIALS = (os.environ["MAIL_USERNAME"],
                         os.environ["MAIL_PASSWORD"])

    # API stuff.
    # Google.
    GOOGLE_WEB_KEY = os.environ.get("GOOGLE_WEB_KEY", "")

    # Yelp.
    YELP_API_CKEY = unicode(os.environ["API_CKEY"])
    YELP_API_CSEC = unicode(os.environ["API_CSEC"])
    YELP_API_TOKEN = unicode(os.environ["API_TOKEN"])
    YELP_API_TSEC = unicode(os.environ["API_TSEC"])

    # Foursquare.
    FOURSQUARE_ID = unicode(os.environ["FOURSQUARE_ID"])
    FOURSQUARE_SECRET = unicode(os.environ["FOURSQUARE_SECRET"])
