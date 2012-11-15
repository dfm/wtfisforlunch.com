__all__ = ["Visit", "Resto", "User"]


import os
from datetime import datetime

import flask
from flask.ext.login import UserMixin
from SimpleAES import SimpleAES

import pymongo
from bson.objectid import ObjectId


class Visit(object):
    def __init__(self, kwargs):
        assert kwargs is not None
        self._doc = kwargs
        self._resto = None

    def __getitem__(self, k):
        return self._doc[k]

    def __getattr__(self, k):
        return self._doc[k]

    @property
    def resto(self):
        if self._resto is None:
            self._resto = Resto.from_id(self.rid)
        return self._resto

    @staticmethod
    def c():
        return flask.g.db.visits

    @classmethod
    def from_id(cls, _id):
        if not isinstance(_id, ObjectId):
            _id = ObjectId(_id)
        u = cls.c().find_one({"_id": _id})
        if u is None:
            return None
        return cls(u)

    @classmethod
    def from_uid(cls, uid):
        u = cls.c().find_one({"uid": uid})
        if u is None:
            return None
        return cls(u)

    @classmethod
    def from_rid(cls, rid):
        u = cls.c().find_one({"rid": rid})
        if u is None:
            return None
        return cls(u)

    @classmethod
    def new(cls, user, resto, dist, prob):
        doc = {"rid": resto._id, "uid": user._id, "date": datetime.now(),
               "distance": dist, "probability": prob,
               "proposed": False, "followed_up": False}
        doc["_id"] = cls.c().insert(doc)
        return cls(doc)

    def add_rating(self, val):
        if val == 0:
            self.c().remove({"_id": self._id})
        self.c().update({"_id": self._id}, {"$set": {"followed_up": True,
                                            "rating": 1 if val == 2 else -1}})

    def set_proposed(self, val):
        if val == 0:
            self.c().update({"_id": self._id}, {"$set": {"proposed": True,
                                                         "followed_up": True,
                                                         "rating": 0}})
        self.c().update({"_id": self._id}, {"$set": {"proposed": True}})


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
        cls.c().update({"_id": kwargs["_id"]}, kwargs, upsert=True)
        return cls(kwargs)


class User(UserMixin):
    def __init__(self, kwargs):
        assert kwargs is not None
        self._doc = kwargs

    def __getitem__(self, k):
        return self._doc[k]

    def __getattr__(self, k):
        return self._doc[k]

    @property
    def email(self):
        aes = SimpleAES(os.environ.get("AES_SECRET", "aes secret key"))
        return aes.decrypt(self._doc["email"])

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
        kwargs["_id"] = cls.c().insert(kwargs)
        return cls(kwargs)

    def new_suggestion(self, resto, dist, prob):
        return Visit.new(self, resto, dist, prob)

    def find_recent(self):
        v = list(Visit.c().find({"uid": self._id, "proposed": True,
                                                  "followed_up": False})
                          .sort([("date", pymongo.DESCENDING)]).limit(1))
        if len(v) == 0:
            return None
        return Visit(v[0])
