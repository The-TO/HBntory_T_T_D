"""Point d'entrée du Backoffice : python3 app.py"""
from flask import Flask, redirect, render_template, request, url_for

import auth
import config
import permissions
from db import db_session
from stock_routes import stock_bp

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.register_blueprint(stock_bp)

    @app.route("/")
    def home():
        """Page d'accueil : réservée aux utilisateurs connectés."""
        user = permissions.require_login()
        # TODO Task 3 : envoyer l'admin vers la gestion des utilisateurs
        # et les utilisateurs communs vers la page du stock.
        if user.role == "common":
            return redirect(url_for("stock.index"))
        return "Connected as %s (%s)" % (user.username, user.role)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """GET : affiche le formulaire. POST : vérifie et crée la session."""
        if request.method == "GET":
            return render_template("login.html")

        try:
            token = auth.login(request.form.get("username"),
                               request.form.get("password"))
        except auth.InvalidCredentials as error:
            return render_template("login.html", error=str(error)), 401

        # Le jeton est rangé dans le cookie que lit permissions.py.
        response = redirect(url_for("home"))
        response.set_cookie(
            permissions.SESSION_COOKIE,
            token,
            max_age=int(auth.SESSION_DURATION.total_seconds()),
            httponly=True,   # JavaScript ne peut pas lire le cookie
            samesite="Lax",  # pas envoyé depuis un formulaire d'un autre site
        )
        return response

    @app.route("/logout", methods=["POST"])
    def logout():
        """Supprime la session en base, puis le cookie du navigateur."""
        auth.logout(request.cookies.get(permissions.SESSION_COOKIE))
        response = redirect(url_for("login"))
        response.delete_cookie(permissions.SESSION_COOKIE)
        return response

    @app.errorhandler(401)
    def unauthorized(error):
        """Personne n'est connecté : on renvoie vers le formulaire."""
        return redirect(url_for("login"))

    @app.errorhandler(403)
    def forbidden(error):
        """Connecté, mais le rôle ne permet pas cette action."""
        return "Forbidden: you do not have permission to do this.", 403

    @app.teardown_appcontext
    def close_session(exception=None):
        """Rend la session de base de données à la fin de la requête."""
        db_session.remove()

    return app


if __name__ == "__main__":
    create_app().run(port=5002, debug=True)
