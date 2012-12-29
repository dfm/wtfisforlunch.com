__all__ = ["propose_position"]

import numpy as np


rearth = 6378.1  # km


def lnglat2xyz(lng, lat):
    lng, lat = np.radians(lng), np.radians(lat)
    clat = np.cos(lat)
    return rearth * np.array([clat * np.cos(lng),
                              clat * np.sin(lng),
                              np.sin(lat)])


def xyz2lnglat(xyz):
    return np.degrees(np.arctan2(xyz[1], xyz[0])), \
           np.degrees(np.arctan2(xyz[2], np.sqrt(np.dot(xyz[:-1], xyz[:-1]))))


def propose_position(ll0, sigma):
    x = lnglat2xyz(*ll0) + sigma * np.random.randn(3)
    return xyz2lnglat(x)
