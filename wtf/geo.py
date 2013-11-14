__all__ = ["propose_position"]

from random import random
from math import radians, degrees, cos, sin, atan2, sqrt, pi

_re = 6378.1  # km


def lnglat2xyz(lat, lng):
    lng, lat = radians(lng), radians(lat)
    clat = cos(lat)
    return (_re*clat*cos(lng), _re*clat*sin(lng), _re*sin(lat))


def xyz2lnglat(xyz):
    return (degrees(atan2(xyz[2], sqrt(xyz[0]*xyz[0]+xyz[1]*xyz[1]))),
            degrees(atan2(xyz[1], xyz[0])))


def propose_position(lat, lng, sigma):
    r = sigma * random()
    th = 2 * pi * random()
    phi = 2 * pi * (0.5 - random())
    x = lnglat2xyz(lat, lng)
    return xyz2lnglat((
        x[0] + r*cos(phi)*cos(th),
        x[1] + r*cos(phi)*sin(th),
        x[2] + r*sin(phi)
    ))
