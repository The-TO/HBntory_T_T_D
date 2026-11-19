"""pages de gestion des utilisateurs (admin uniquement)"""

from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for)


import user_service
from permissions import require_role
from db import db_session
from models import Branch, ROLE_ADMIN


bp = Blueprint("admin", __name__, url_prefix="/admin") #permet d'ecrire les route flask dans un autre fichier qu'app.py

def all_branches():
    """Toutes les succursales, triées par nom (pour la liste déroulante)."""
    return db_session.query(Branch).order_by(Branch.name).all()

@bp.route("/users")
def users():
    require_role(ROLE_ADMIN)
    return render_template("admin_users.html",
                           users=user_service.list_users())

@bp.route("/users/new", methods=["GET", "POST"])
def new_user():
    require_role(ROLE_ADMIN)
    if request.method == "POST":
        try:
            user = user_service.create_user(
                request.form.get("username"),
                request.form.get("password"),
                request.form.get("branch_id"),
            )
            flash("User %s created." %user.username, "success")
            return redirect(url_for("admin.users"))
        except user_service.UserError as exc:
            flash(str(exc), "error")
    return render_template("admin_user_form.html", user=None,
                           branches=all_branches())


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):
    require_role(ROLE_ADMIN)
    try:
        user = user_service.get_common_user(user_id)
        if request.method == "POST":
            user_service.update_user(
                user_id,
                request.form.get("branch_id"),
                request.form.get("password", "")
            )
            flash("User %s updated." % user.username, "success")
            return redirect(url_for("admin.users"))
    except user_service.UserError as exc:
        flash(str(exc), "error")
        if request.method == "GET":
            return redirect(url_for("admin.users"))
    return render_template("admin_user_form.html", user=user,
                           branches=all_branches())


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    require_role(ROLE_ADMIN)
    try:
        user = user_service.soft_delete_user(user_id)
        flash("User %s deleted (soft delete)." % user.username, "success")
    except user_service.UserError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin.users"))
