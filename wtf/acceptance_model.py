import numpy as np


class AcceptanceModel(object):

    def __init__(self, *args):
        self.set_pars(args)

    def set_pars(self, vector):
        sigmad2, sigmar2, muc, sigmac2 = vector
        self._sd2 = sigmad2
        self._sr2 = sigmar2
        self._muc = muc
        self._sc2 = sigmac2

        self._rmarg = None
        self._cmarg = None

    @property
    def pars(self):
        return np.array([self._sd2, self._sr2, self._muc, self._sc2])

    def predict(self, dn, rn, cn):
        ll = self.lnlike(dn, rn=rn, cn=cn, an=True)
        return np.exp(ll)

    # def update(self, dn, rn, cn, an, eta=0.01):
    #     v = self.pars
    #     v -= eta * self.grad(dn, rn, cn, an)

    #     eps = 0.1
    #     v[v < eps] = eps

    #     # Constraints on cost mean.
    #     v[2] = min(4, v[2])

    #     self.set_pars(v)

    def _rating_prior(self, r):
        # Z = sqrt(pi * sig^2 / 2) * (erf((10 - r0) / sqrt(2 * sig^2))
        #                             + erf(r0 / sqrt(2 * sig^2)))
        r0, s2 = 8.5, 2.0 * 2.0
        lnZ = 1.3550776261638171
        return -0.5 * (r - r0) ** 2 / s2 - lnZ

    def _log_sum_exp(self, pr):
        pr0 = np.max(pr)
        return pr0 + np.log(np.sum(np.exp(pr - pr0))) - np.log(len(pr))

    @property
    def rmarg(self):
        # Marginalize over rating.
        if self._rmarg is None:
            r = 10 * np.random.rand(1000)
            pr = self._rating_prior(r) - 0.5 * (r - 10) ** 2 / self._sr2
            self._rmarg = self._log_sum_exp(pr)
        return self._rmarg

    @property
    def cmarg(self):
        # Marginalize over cost.
        if self._cmarg is None:
            c = np.arange(1, 5)
            pr = -0.5 * (c - self._muc) ** 2 / self._sc2
            self._cmarg = self._log_sum_exp(pr)
        return self._cmarg

    def lnlike(self, dn, rn=None, cn=None, an=True):
        dn2 = dn * dn
        E = -0.5 * dn2 / self._sd2

        if rn is not None:
            rn2 = (rn - 10) ** 2
            E -= 0.5 * rn2 / self._sr2
        else:
            E += self.rmarg

        if cn is not None:
            cn2 = (cn - self._muc) ** 2
            E -= 0.5 * cn2 / self._sc2
        else:
            E += self.cmarg

        if an:
            return E

        assert 0
        return -np.log(1.0 - np.exp(-E))

    # def grad(self, dn, rn, cn, an):
    #     dn2 = dn * dn

    #     dldsd2 = 0.5 / self._sd2 - 0.5 * dn2 / self._sd2 / self._sd2

    #     if rn is not None:
    #         rn2 = (rn - 10) ** 2
    #         dldsr2 = 0.5 / self._sr2 - 0.5 * rn2 / self._sr2 / self._sr2
    #     else:
    #         dldsr2 = 0.0

    #     if cn is not None:
    #         cn2 = (cn - self._muc) ** 2
    #         dldmuc = (self._muc - cn) / self._sc2
    #         dldsc2 = 0.5 / self._sc2 - 0.5 * cn2 / self._sc2 / self._sc2
    #     else:
    #         dldmuc = 0.0
    #         dldsc2 = 0.0

    #     if an:
    #         return np.array([dldsd2, dldsr2, dldmuc, dldsc2])

    #     loss = self.loss(dn, rn, cn, True)
    #     return np.array([dldsd2, dldsr2, dldmuc, dldsc2]) \
    #            / (1.0 - np.exp(loss))


if __name__ == "__main__":
    eps = 1.25e-8
    v0 = np.array([0.3, 8.0, 1.0, 4.0])

    for n, data in enumerate([[0.0, 10.0, 1.0, True],
                              [0.2, 8.6, 0.5, True],
                              [0.01, 1.5, 1.2, True],
                              [0.16, 8.6, None, False],
                              [0.01, 2.5, 0.9, False]]):
        model = AcceptanceModel(*v0)
        print(model.predict(*(data[:-1])))
        l0 = model.loss(*data)
        g0 = model.grad(*data)
        g1 = np.empty(len(v0))

        for i in range(len(v0)):
            v = np.array(v0)
            v[i] += eps
            model.set_pars(v)
            lp1 = model.loss(*data)

            v[i] -= 2 * eps
            model.set_pars(v)
            lm1 = model.loss(*data)

            g1[i] = 0.5 * (lp1 - lm1) / eps

        assert np.sum((g0 - g1) ** 2) < eps, u"Failed test {0}".format(n + 1)
        print(u"Passed test {0}".format(n + 1))
