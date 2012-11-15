You'll need the following environment variables:

```
export GOOGLE_API_KEY=WHATEVER_KEY
export GOOGLE_WEB_KEY=WHATEVER_KEY
export MAIL_USERNAME=DUDE
export MAIL_PASSWORD=PASSWWWWWWWOOOOORRRRRD
```

The Model
---------

The acceptance probability of a suggestion as a function of distance (`d`)
and rating (`r`) is given by:

```
p_{acc} (r, d) = (r - a)^b / ((r - a)^b + c)
```

where each of `a`, `b` and `c` are linear functions of distance.
Qualitatively:

* `a` is the smallest rating accepted at a particular distance,
* `b` describes the width of the transition region from low to high
  probability, and
* `c` does ...

A good starting point for the functions is:

```
a(d) = 0.5 * d
b(d) = 6 + d
c(d) = 100 + 450 * d
```
