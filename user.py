__all__ = ["User"]


import os

import flask
from flask.ext.login import UserMixin
from SimpleAES import SimpleAES


class User(UserMixin):
    def __init__(self, kwargs):
        assert kwargs is not None
        self._doc = kwargs
        self.fullname = kwargs["fullname"]

    def get_id(self):
        return unicode(self._doc["_id"])

    def get_auth_token(self):
        return self._doc["token"]

    @classmethod
    def new(cls, **kwargs):
        c = flask.g.db.users
        aes = SimpleAES(os.environ.get("AES_SECRET", "aes secret key"))
        kwargs["email"] = aes.encrypt(kwargs["email"])
        kwargs["_id"] = c.insert(kwargs, safe=True)
        return cls(kwargs)
