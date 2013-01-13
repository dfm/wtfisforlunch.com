__all__ = ["Proposal", "User"]


import os
from datetime import datetime
import numpy as np

import flask
from flask.ext.login import UserMixin
from SimpleAES import SimpleAES

import pymongo
from bson.objectid import ObjectId


class Proposal(object):

    def __init__(self, doc):
        self._doc = dict(doc)

    @classmethod
    def new(cls, uid, **doc):
        doc = dict(doc)
        doc["user_id"] = uid
        doc["_id"] = cls.c().insert(doc)
        doc["date"] = datetime.now()
        return cls(doc)

    def __getitem__(self, k):
        return self._doc[k]

    def __getattr__(self, k):
        return self._doc[k]

    def remove(self):
        self.c().remove({"_id": ObjectId(self._doc["_id"])}, safe=True)

    def update_response(self, accepted):
        self.c().update({"_id": ObjectId(self._doc["_id"])},
                        {"$set": {"accepted": accepted,
                                  "date": datetime.now()}})

    def report(self, value):
        if value == 2:
            url = self.get_counter()
            self.c().update({"_id": ObjectId(self._doc["_id"])},
                            {"$set": {"accepted": 2,
                                      "date": datetime.now(),
                                      "short_url": url}})
            return url
        elif value == 1:
            self.c().update({"_id": ObjectId(self._doc["_id"])},
                            {"$set": {"accepted": -1,
                                      "date": datetime.now()}})
        else:
            self.remove()

        return None

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
                                     "lunch", "login", "logout"]:
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


class Listing(object):

    pass


class YelpListing(Listing):

    def __init__(self, doc):
        self.id = doc["id"]
        self.name = doc["name"]
        self.location = doc["location"]["coordinate"]
        self.url = doc["url"]
        self.address = ", ".join(doc["location"]["display_address"]),

        l = doc["location"]
        self.search_address = doc["name"] \
                + ", " + ", ".join(l["address"]) \
                + ", " + ", ".join([l[k] for k in ["city", "state_code",
                                                   "country_code",
                                                   "postal_code"]])

        self.categories = ", ".join([c[0] for c in doc["categories"]]),
        self.short_categories = [c[1] for c in doc["categories"]],
        self.rating = doc.get("rating", 0.0)
        self.rating_img_url = doc["rating_img_url"]
        self.review_count = doc.get("review_count", 0)


class FoursquareListing(Listing):

    def __init__(self, doc):
        self.id = doc["id"]
        self.name = doc["name"]
        self.url = doc["canonicalUrl"]
        self.categories = ", ".join([c["name"]
                                    for c in doc.get("categories", [])])

        l = doc["location"]
        self.location = {"latitude": l["lat"], "longitude": l["lng"]}

        a = [l[k] for k in ["address", "city", "state", "country",
                            "postalCode"] if k in l]
        self.address = ", ".join(a)

        # Count the number of checkins, etc.
        s = doc.get("stats", {})
        total = [s[k] for k in ["checkinsCount", "usersCount", "tipCount"]]

        # HACK MAGIC!!!!
        self.rating = doc.get("rating", None)
        self.review_count = sum(total)

        self.price = doc.get("price", {}).get("tier", None)


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

    def find_recent(self):
        v = list(Proposal.c().find({"user_id": self._id, "accepted": 1})
                             .sort([("date", pymongo.DESCENDING)]).limit(1))

        if len(v) == 0:
            return None

        return Proposal(v[0])

    def update_model(self, model_pars):
        self.c().update({"_id": self._id},
                        {"$set": {"model": list(model_pars)}})
        self._doc["model"] = list(model_pars)
