#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ["db", "get_redis", "format_key"]

import flask
import redis
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def get_redis():
    port = int(flask.current_app.config["REDIS_PORT"])
    return redis.Redis(port=port)


def format_key(key):
    return "{0}:{1}".format(flask.current_app.config["REDIS_PREFIX"], key)
