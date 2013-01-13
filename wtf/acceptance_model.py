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

    @property
    def pars(self):
        return np.array([self._sd2, self._sr2, self._muc, self._sc2])

    def predict(self, dn, rn, cn):
        return np.exp(-self.loss(dn, rn, cn, True))

    def update(self, dn, rn, cn, an, eta=0.01):
        v = self.pars
        v -= eta * self.grad(dn, rn, cn, an)

        eps = 0.1
        v[v < eps] = eps

        # Constraints on cost mean.
        v[2] = min(4, v[2])

        self.set_pars(v)

    def loss(self, dn, rn, cn, an):
        dn2 = dn * dn
        E = 0.5 * (dn2 / self._sd2 + np.log(self._sd2))

        if rn is not None:
            rn2 = (rn - 10) ** 2
            E += 0.5 * (rn2 / self._sr2 + np.log(self._sr2))

        if cn is not None:
            cn2 = (cn - self._muc) ** 2
            E += 0.5 * (cn2 / self._sc2 + np.log(self._sc2))

        E = max(E, 0.0)
        if an:
            return E
        return -np.log(1.0 - np.exp(-E))

    def grad(self, dn, rn, cn, an):
        dn2 = dn * dn

        dldsd2 = 0.5 / self._sd2 - 0.5 * dn2 / self._sd2 / self._sd2

        if rn is not None:
            rn2 = (rn - 10) ** 2
            dldsr2 = 0.5 / self._sr2 - 0.5 * rn2 / self._sr2 / self._sr2
        else:
            dldsr2 = 0.0

        if cn is not None:
            cn2 = (cn - self._muc) ** 2
            dldmuc = (self._muc - cn) / self._sc2
            dldsc2 = 0.5 / self._sc2 - 0.5 * cn2 / self._sc2 / self._sc2
        else:
            dldmuc = 0.0
            dldsc2 = 0.0

        if an:
            return np.array([dldsd2, dldsr2, dldmuc, dldsc2])

        loss = self.loss(dn, rn, cn, True)
        return np.array([dldsd2, dldsr2, dldmuc, dldsc2]) \
               / (1.0 - np.exp(loss))


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
