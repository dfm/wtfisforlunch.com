import flask


def create_app():
    app = flask.Flask(__name__)

    from .views.yelp import yelp
    app.register_blueprint(yelp)

    return app
