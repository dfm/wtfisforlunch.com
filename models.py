__all__ = ["Resto", "User"]


import os
from datetime import datetime

import flask
from flask.ext.login import UserMixin
from SimpleAES import SimpleAES
from bson.objectid import ObjectId


class Resto(object):
    def __init__(self, kwargs):
        assert kwargs is not None
        self._doc = kwargs

    def __getitem__(self, k):
        return self._doc[k]

    def __getattr__(self, k):
        return self._doc[k]

    @staticmethod
    def c():
        return flask.g.db.restos

    @classmethod
    def from_id(cls, _id):
        u = cls.c().find_one({"_id": _id})
        if u is None:
            return None
        return cls(u)

    @classmethod
    def from_gid(cls, gid):
        u = cls.c().find_one({"id": gid})
        if u is None:
            return None
        return cls(u)

    @classmethod
    def new(cls, **kwargs):
        kwargs["_id"] = kwargs.pop("id")
        cls.c().update({"_id": kwargs["_id"]}, kwargs, upsert=True, safe=True)
        return cls(kwargs)


class User(UserMixin):
    def __init__(self, kwargs):
        assert kwargs is not None
        self._doc = kwargs
        self.fullname = kwargs["fullname"]

    @staticmethod
    def c():
        return flask.g.db.users

    def get_id(self):
        return unicode(self._doc["_id"])

    def get_auth_token(self):
        return self._doc["token"]

    @classmethod
    def from_id(cls, _id):
        u = cls.c().find_one({"_id": ObjectId(_id)})
        if u is None:
            return None
        return cls(u)

    @classmethod
    def from_token(cls, token):
        u = cls.c().find_one({"token": token})
        if u is None:
            return None
        return cls(u)

    @classmethod
    def from_openid(cls, oid):
        u = cls.c().find_one({"openid": oid})
        if u is None:
            return None
        return cls(u)

    @classmethod
    def new(cls, **kwargs):
        aes = SimpleAES(os.environ.get("AES_SECRET", "aes secret key"))
        kwargs["email"] = aes.encrypt(kwargs["email"])
        kwargs["_id"] = cls.c().insert(kwargs, safe=True)
        return cls(kwargs)

    def propose_visit(self, resto):
        self.c().update({"_id": self._doc["_id"]},
            {"$push": {"proposed_visits": {"restoid": resto._id,
                                           "date": datetime.now()}}})
