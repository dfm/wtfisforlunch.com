__all__ = ["Proposal", "User"]


import os
# from datetime import datetime

import flask
from flask.ext.login import UserMixin
from SimpleAES import SimpleAES

# import pymongo
from bson.objectid import ObjectId


class Proposal(object):

    def __init__(self, doc):
        self._doc = dict(doc)

    @classmethod
    def new(cls, uid, **doc):
        doc = dict(doc)
        doc["user_id"] = uid
        doc["_id"] = cls.c().insert(doc)
        return cls(doc)

    def __getitem__(self, k):
        return self._doc[k]

    def __getattr__(self, k):
        return self._doc[k]

    @staticmethod
    def c():
        return flask.g.db.proposals

    @classmethod
    def from_id(cls, _id):
        u = cls.c().find_one({"_id": ObjectId(_id)})
        if u is None:
            return None
        return cls(u)

    @property
    def user(self):
        uid = self._doc["user_id"]
        if uid is None:
            return None
        return User.from_id(uid)

    @staticmethod
    def get_counter():
        """
        Crazy shit for generating short urls.

        """
        c = flask.g.db.counters
        tag = None
        while tag is None or tag in ["about", "me", "magic", "yelp", "google",
                                     "lunch"]:
            o = c.find_and_modify({"_id": "visit_id"}, {"$inc": {"count": 1}},
                                  new=True, upsert=True)

            chars = [chr(c) for c in range(ord('0'), ord('9') + 1)
                                  + range(ord('a'), ord('z') + 1)
                                  + range(ord('A'), ord('Z') + 1)]

            def counter(i):
                c = chars[i % len(chars)]
                if i - len(chars) >= 0:
                    c = counter(i // len(chars)) + c
                return c

            tag = counter(o["count"])

        return tag


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

    def blacklist(self, rid):
        self.c().update({"_id": self._id},
                        {"$addToSet": {"blacklist": rid}})
        bl = self._doc.get("blacklist", [])
        if rid not in bl:
            bl.append(rid)
        self._doc["blacklist"] = bl

    # def find_recent(self):
    #     v = list(Proposal.c().find({"uid": self._id, "proposed": True,
    #                                               "followed_up": False})
    #                       .sort([("date", pymongo.DESCENDING)]).limit(1))
    #     if len(v) == 0:
    #         return None
    #     return Visit(v[0])
