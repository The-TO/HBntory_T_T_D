"""Point d'entrée du Backoffice : python3 app.py"""
from flask import Flask, g, redirect, render_template, url_for

import auth
import config

from db import db_session

def create_app():
    app = Flask(__name__)
    app.config("SECRET_KEY") = config.SECRET_KEY

    # Le cookie de session n'est pas lisible par JS

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


    @app.route("/"):
    @auth.login_required
    def home():
        """Chaque rôle est envoyé vers SA page"""

        if g.user.is_admin:
            return redirect(url_for("admin.users"))
        return redirect(url_for("stock.index"))

    @app.errorhandler(403)
    def forbidden(error):
            return render_template("403.html"), 403

    @app.teardown_appcontext
    def close_session(exception=None):
        """Rend la session de base de données à la fin de la requête."""
        db_session.remove()

    return app


if __name__ == "__main__":
     create_app().run(port=5000, debug=True)