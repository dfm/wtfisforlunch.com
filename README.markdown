The Algorithm
-------------

To choose a restaurant, start from the user's latitude (`lat`) and longitude
(`long`) and convert into a 3-vector:

```
    / x \   / R cos(long) cos(lat) \
v = | y | = | R cos(long) sin(lat) |
    \ z /   \     R sin(long)      /
```

where `R` is the radius of the Earth (`6378.1 km`). Then, draw a random
displacement vector:

```
dv = ( dx, dy, dz )
```

where `dx`, `dy` and `dz` are normally distributed random numbers with
standard deviation `sigma` (in kilometers). `sigma` will be different for
each user but it should start with something reasonable like `1`. Then,
project `v + dv` back onto the surface of the earth

```
 R  / xf \    R  / R cos(long) cos(lat) + dx \
--- | yf | = --- | R cos(long) sin(lat) + dy |
 N  \ zf /    N  \     R sin(long) + dz      /
```

where `N = Sqrt[xf^2 + yf^2 + zf^2]`. Then, the resulting `lat` and `long`
are given by:

```
longf = yf / xf
latf  = zf / Sqrt[xf^2 + z^2]
```


