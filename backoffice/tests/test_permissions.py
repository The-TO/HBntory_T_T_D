from types import SimpleNamespace

import pytest
from flask import Flask

import permissions
from permissions import current_branch_id, require_role


@pytest.fixture
def client():
    app = Flask(__name__)

    @app.route("/admin/users")
    def users():
        require_role("admin")
        return "ok"

    @app.route("/stock/branch")
    def branch():
        return str(current_branch_id())

    return app.test_client()


def log_in_as(monkeypatch, role, branch_id=None):
    user = SimpleNamespace(role=role, branch_id=branch_id)
    monkeypatch.setattr(permissions, "get_current_user", lambda: user)


def test_anonymous_is_refused_everywhere(client, monkeypatch):
    monkeypatch.setattr(permissions, "get_current_user", lambda: None)
    assert client.get("/admin/users").status_code == 401
    assert client.get("/stock/branch").status_code == 401


def test_common_user_cannot_use_admin_route(client, monkeypatch):
    log_in_as(monkeypatch, "common", branch_id=1)
    assert client.get("/admin/users").status_code == 403


def test_admin_cannot_use_stock_route(client, monkeypatch):
    log_in_as(monkeypatch, "admin")
    assert client.get("/stock/branch").status_code == 403


def test_admin_can_use_admin_route(client, monkeypatch):
    log_in_as(monkeypatch, "admin")
    assert client.get("/admin/users").status_code == 200


def test_common_user_works_on_own_branch(client, monkeypatch):
    log_in_as(monkeypatch, "common", branch_id=2)
    response = client.get("/stock/branch")
    assert response.status_code == 200
    assert response.data == b"2"
