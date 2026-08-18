"""Cria ou atualiza um usuário de login local (e-mail/senha).

Uso:
    python create_user.py usuario@exemplo.com "Nome Completo" [--admin]

Use --admin para dar a esse usuário permissão de cadastrar outros usuários
(necessário para criar o primeiro administrador do sistema).
A senha é pedida de forma oculta no terminal.
"""
import getpass
import sys

from werkzeug.security import generate_password_hash

from db import ensure_schema, get_db


def main():
    if len(sys.argv) < 2:
        print("Uso: python create_user.py email@exemplo.com \"Nome Completo\" [--admin]")
        sys.exit(1)

    args = [a for a in sys.argv[1:] if a != "--admin"]
    is_admin = "--admin" in sys.argv[1:]

    email = args[0].strip().lower()
    nome = args[1] if len(args) > 1 else email

    senha = getpass.getpass("Senha: ")
    senha2 = getpass.getpass("Confirme a senha: ")
    if senha != senha2:
        print("As senhas não coincidem.")
        sys.exit(1)
    if len(senha) < 8:
        print("Use uma senha com pelo menos 8 caracteres.")
        sys.exit(1)

    ensure_schema()
    db = get_db()
    existente = db.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()
    password_hash = generate_password_hash(senha)

    if existente:
        db.execute(
            "UPDATE users SET password_hash = %s, nome = %s, auth_provider = 'local', is_admin = %s WHERE email = %s",
            (password_hash, nome, int(is_admin), email),
        )
        print(f"Senha atualizada para {email}." + (" (administrador)" if is_admin else ""))
    else:
        db.execute(
            "INSERT INTO users (email, password_hash, nome, auth_provider, is_admin) VALUES (%s, %s, %s, 'local', %s)",
            (email, password_hash, nome, int(is_admin)),
        )
        print(f"Usuário {email} criado." + (" (administrador)" if is_admin else ""))

    db.commit()
    db.close()


if __name__ == "__main__":
    main()
