#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["User"]

import flask
from SimpleAES import SimpleAES
from sqlalchemy import (Column, Integer, String, Decimal,
                        ForeignKey, Table)
from sqlalchemy.orm import relationship

from .database import db


def encrypt_email(email):
    """
    The default encryption function for storing emails in the database. This
    uses AES and the encryption key defined in the applications configuration.

    :param email:
        The email address.

    """
    aes = SimpleAES(flask.current_app.config["AES_KEY"])
    return aes.encrypt(email)


def decrypt_email(enc_email):
    """
    The inverse of :func:`encrypt_email`.

    :param enc_email:
        The encrypted email address.

    """
    aes = SimpleAES(flask.current_app.config["AES_KEY"])
    return aes.decrypt(enc_email)


venue_categories = Table("venue_categories", db.Model.metadata,
                         Column("venue_id", Integer, ForeignKey("venues.id")),
                         Column("category_id", Integer,
                                ForeignKey("categories.id")))

blacklist = Table("blacklist", db.Model.metadata,
                  Column("user_id", Integer, ForeignKey("users.id")),
                  Column("venue_id", Integer, ForeignKey("venues.id")))


# Data models.
class User(db.Model):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    foursquare_id = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    token = Column(String)

    blacklist = relationship("Venue", secondary=blacklist,
                             backref="blacklisters")

    def __init__(self, foursquare_id, first_name, last_name, token,
                 email=None):
        self.foursquare_id = foursquare_id
        self.first_name = first_name
        self.last_name = last_name
        self.token = token
        if email is not None:
            self.email = encrypt_email(email)

    def __repr__(self):
        return "<User(\"{0}\")>".format(self.foursuqare_id)

    def get_email(self):
        if self.email is None:
            return None
        return decrypt_email(self.email)

    def get_id(self):
        return self.id

    def is_authenticated(self):
        return self.token is not None

    def is_active(self):
        return self.token is not None

    def is_anonymous(self):
        return False


class Venue(db.Model):

    __tablename__ = "venues"

    id = Column(Integer, primary_key=True)
    foursquare_id = Column(String)
    name = Column(String)
    short_url = Column(String)
    lat = Column(Decimal)
    lng = Column(Decimal)
    address = Column(String)
    cross_street = Column(String)
    city = Column(String)
    state = Column(String)
    country = Column(String)
    postal_code = Column(String)
    price = Column(Integer)
    rating = Column(Decimal)

    categories = relationship("Category", secondary=venue_categories,
                              backref="venues")

    def __init__(self, foursquare_id, name, short_url, lat, lng, address,
                 cross_street, city, state, country, postal_code, price,
                 rating, categories):
        self.foursquare_id = foursquare_id
        self.name = name
        self.short_url = short_url
        self.lat = lat
        self.lng = lng
        self.address = address
        self.cross_street = cross_street
        self.city = city
        self.state = state
        self.country = country
        self.postal_code = postal_code
        self.price = price
        self.rating = rating
        self.categories = categories

    def __repr__(self):
        return "<Venue(\"{0}\")>".format(self.foursuqare_id)


class Category(db.Model):

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    foursquare_id = Column(String)
    name = Column(String)
    plural_name = Column(String)
    short_name = Column(String)

    def __repr__(self):
        return "<Category(\"{0}\")>".format(self.foursuqare_id)
