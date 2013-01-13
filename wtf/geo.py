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
    r = sigma * np.random.rand()
    th = 2 * np.pi * np.random.rand()
    phi = 2 * np.pi * (0.5 - np.random.rand())
    x = lnglat2xyz(*ll0) + r * np.array([np.cos(phi) * np.cos(th),
                                         np.cos(phi) * np.sin(th),
                                         np.sin(phi)])
    return xyz2lnglat(x)


if __name__ == "__main__":
    import matplotlib.pyplot as pl

    for i in range(1000):
        pos = propose_position([0, 0], 0.5)
        pl.plot(pos[0], pos[1], ".k")
    pl.savefig("geo.png")
