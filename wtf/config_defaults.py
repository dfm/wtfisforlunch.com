from __future__ import print_function, absolute_import, unicode_literals

import os


class WTFConfig(object):

    SECRET_KEY = unicode(os.environ.get("SECRET", "development secret key")) \
                    .encode("utf-8")
