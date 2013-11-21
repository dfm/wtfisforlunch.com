#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="wtf",
    version="2.0.0",
    author="Daniel Foreman-Mackey",
    author_email="danfm@nyu.edu",
    url="http://wtfisforlunch.com",
    packages=["wtf"],
    package_data={"wtf": ["templates/*", "static/*"]},
    include_package_data=True,
)
