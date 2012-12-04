import numpy as np


class AcceptanceModel(object):

    def __init__(self, *args):
        self.set_pars(args)

    def set_pars(self, vector):
        sigmad2, sigma02, alpha = vector
        self._sd2 = sigmad2
        self._s02 = sigma02
        self._alpha = alpha

    def loss(self, dn, rn, an):
        dn2, rn2 = dn * dn, (rn - 5) * (rn - 5)
        sr2 = self._s02 * (dn + 1) ** -self._alpha
        E = 0.5 * (dn2 / self._sd2 + np.log(2 * np.pi * self._sd2) + rn2 / sr2)
        if an:
            return E
        return -np.log(1.0 - np.exp(-E))

    def grad(self, dn, rn, an):
        dn2, rn2 = dn * dn, (rn - 5) * (rn - 5)
        sr2 = self._s02 / (dn + 1) ** self._alpha

        dldsd2 = 0.5 / self._sd2 - 0.5 * dn2 / self._sd2 / self._sd2

        dldsr2 = -0.5 * rn2 / sr2 / sr2

        dp1a = (dn + 1) ** self._alpha
        dlds02 = dldsr2 / dp1a
        dlda = -dldsr2 * self._s02 * np.log(dn + 1) / dp1a

        if an:
            return np.array([dldsd2, dlds02, dlda])

        loss = self.loss(dn, rn, True)
        return np.array([dldsd2, dlds02, dlda]) / (1.0 - np.exp(loss))


if __name__ == "__main__":
    eps = 1.25e-8
    v0 = np.array([0.16, 10.0, 3.5])

    for n, data in enumerate([[0.5, 3.6, True],
                              [0.01, 1.5, True],
                              [0.5, 3.6, False],
                              [0.01, 1.5, False]]):
        model = AcceptanceModel(*v0)
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
