# Flask stuff.
DEBUG = False
TESTING = False
SECRET_KEY = "development key"
AES_KEY = "super secret encryption key"

# Database stuff.
SQLALCHEMY_DATABASE_URI = "postgresql://localhost/wtf"
REDIS_PORT = 6379
REDIS_PREFIX = "wtf"

# Foursquare API.
FOURSQUARE_ID = None
FOURSQUARE_SECRET = None
