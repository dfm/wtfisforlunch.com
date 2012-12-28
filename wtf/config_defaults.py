from __future__ import print_function, absolute_import, unicode_literals

import os


class WTFConfig(object):

    SERVER_NAME = None

    SECRET_KEY = unicode(os.environ.get("SECRET", "development secret key")) \
                    .encode("utf-8")

    ADMIN_EMAILS = ["robot@wtfisforlunch.com", ]
    EMAIL_CREDENTIALS = (os.environ["MAIL_USERNAME"],
                         os.environ["MAIL_PASSWORD"])
