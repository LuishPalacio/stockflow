"""Autenticação: login local (e-mail/senha) e controle de acesso por sessão."""
from functools import wraps

from flask import redirect, request, session, url_for

from db import get_db


def _usuario_ainda_valido():
    """Confirma no banco que o usuário da sessão ainda existe e atualiza o
    is_admin na hora - assim, se um admin excluir ou rebaixar alguém, isso
    vale imediatamente, sem esperar a pessoa sair e entrar de novo."""
    db = get_db()
    user = db.execute(
        "SELECT is_admin FROM users WHERE id = %s", (session["user_id"],)
    ).fetchone()
    db.close()
    if user is None:
        return False
    session["is_admin"] = bool(user["is_admin"])
    return True


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        if not _usuario_ainda_valido():
            session.clear()
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        if not _usuario_ainda_valido():
            session.clear()
            return redirect(url_for("login", next=request.path))
        if not session.get("is_admin"):
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped
