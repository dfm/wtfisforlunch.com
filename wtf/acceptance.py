#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division

__all__ = ["AcceptanceModel"]

from math import erf, exp, sqrt, pi, log


class AcceptanceModel(object):

    def __init__(self, sigmad, sigmar, muc, sigmac):
        self.sigmad2 = sigmad*sigmad
        self.sigmar2 = sigmar*sigmar
        self.muc = muc
        self.sigmac2 = sigmac*sigmac

        self._marg_rating = None
        self._marg_cost = None

    @property
    def marg_rating(self):
        if self._marg_rating is None:
            s = self.sigmac2
            sp4 = s+4
            self._marg_rating = 0.5*log(2*pi*s/sp4)*exp(-9/(8*sp4))
            self._marg_rating += log(erf(0.75*sqrt(0.5*s/sp4))
                                     - erf(-0.25*(17*s+80)/sqrt(2*s*sp4)))
        return self._marg_rating

    @property
    def marg_cost(self):
        if self._marg_cost is None:
            is2 = -0.5 / self.sigmac2
            mu = self.muc
            self._marg_cost = log(sum([exp(is2*(c-mu)**2)
                                       for c in range(1, 5)]))
        return self._marg_cost

    def lnlike(self, dn, rn, cn):
        ll = -0.5*dn*dn/self.sigmad2

        if rn is None:
            ll += self.marg_rating
        else:
            ll -= 0.5*(rn-10)**2/self.sigmar2

        if cn is None:
            ll += self.marg_cost
        else:
            ll -= 0.5*(cn-self.muc)**2/self.sigmac2

        return ll
