# -*- coding: utf-8 -*-

from __future__ import division, print_function

__all__ = ["propose_position", "compute_distance"]

import numpy as np
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
    r = sigma * np.random.randn()
    th = 2 * pi * np.random.rand()
    phi = 2 * pi * (0.5 - np.random.rand())
    x = lnglat2xyz(lat, lng)
    return xyz2lnglat((
        x[0] + r*cos(phi)*cos(th),
        x[1] + r*cos(phi)*sin(th),
        x[2] + r*sin(phi)
    ))


def compute_distance(lat1, lng1, lat2, lng2):
    x1 = lnglat2xyz(lat1, lng1)
    x2 = lnglat2xyz(lat2, lng2)
    ang = np.arccos(np.dot(x1, x2)/sqrt(np.dot(x1, x1))/sqrt(np.dot(x2, x2)))
    return _re * ang
