import os
import secrets
from urllib.parse import urlparse

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from werkzeug.security import check_password_hash, generate_password_hash

from auth import admin_required, login_required
from db import ensure_schema, get_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR") or BASE_DIR
INSTANCE_DIR = os.path.join(DATA_DIR, "instance")
SECRET_KEY_PATH = os.path.join(INSTANCE_DIR, "secret_key.txt")


def carregar_secret_key():
    env_key = os.environ.get("FLASK_SECRET_KEY")
    if env_key:
        return env_key
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    if os.path.exists(SECRET_KEY_PATH):
        with open(SECRET_KEY_PATH, "r") as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(SECRET_KEY_PATH, "w") as f:
        f.write(key)
    return key


app = Flask(__name__)
app.secret_key = carregar_secret_key()
ensure_schema()

csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")


def _next_seguro(destino):
    """Só aceita caminhos relativos dentro do próprio site - nunca uma URL
    completa apontando pra outro domínio (evita redirecionamento aberto)."""
    if not destino or not destino.startswith("/") or destino.startswith("//"):
        return False
    partes = urlparse(destino)
    return not partes.netloc and not partes.scheme


def _mesma_origem(url):
    """Confirma que a URL aponta pro próprio site antes de usar como redirect."""
    if not url:
        return False
    return urlparse(url).netloc == request.host


@app.errorhandler(CSRFError)
def csrf_erro(e):
    flash("Sua sessão expirou ou a página ficou aberta por muito tempo. Tente novamente.", "error")
    destino = request.referrer if _mesma_origem(request.referrer) else url_for("login")
    return redirect(destino)


@app.errorhandler(429)
def limite_excedido(e):
    flash("Muitas tentativas em pouco tempo. Aguarde um minuto e tente novamente.", "error")
    return redirect(url_for("login")), 429


PER_PAGE = 50
SENHA_MIN_LEN = 8

# Campos do formulário, agrupados em seções por tipo de informação.
FORM_SECTIONS = [
    ("Identificação", [
        ("codigo", "Código", "text"),
        ("tipo", "Tipo", "text"),
        ("fabricante", "Fabricante", "text"),
        ("nome", "Nome", "text"),
        ("modelo", "Modelo", "text"),
        ("valor", "Valor (R$)", "number"),
        ("estado", "Estado", "text"),
    ]),
    ("Alocação", [
        ("funcionario", "Funcionário", "text"),
        ("setor", "Setor", "text"),
        ("data_entrega", "Data de entrega", "date"),
    ]),
    ("Identificação física", [
        ("sn", "S/N", "text"),
        ("pn", "P/N", "text"),
        ("mac_rede", "MAC Rede", "text"),
        ("mac_wifi", "MAC Wifi", "text"),
    ]),
    ("Configuração (notebook/desktop)", [
        ("so", "SO", "text"),
        ("processador", "Processador", "text"),
        ("ram", "Ram", "text"),
        ("armazenamento", "Armazenamento", "text"),
    ]),
    ("Celular", [
        ("imei1", "IMEI 1", "text"),
        ("imei2", "IMEI 2", "text"),
        ("carregador", "Carregador", "text"),
        ("sn_carregador", "S/N Carregador", "text"),
    ]),
    ("Monitor / TV", [
        ("resolucao", "Resolução", "text"),
        ("proporcao", "Proporção", "text"),
        ("taxa_atualizacao", "Taxa de atualização", "text"),
        ("tipo_painel", "Tipo de painel", "text"),
        ("fonte", "Fonte", "text"),
        ("saidas", "Saídas", "text"),
    ]),
    ("Observações", [
        ("obs", "OBS", "textarea"),
    ]),
]

ALL_FIELDS = [name for _, fields in FORM_SECTIONS for name, _, _ in fields]
FIELD_LABELS = {name: label for _, fields in FORM_SECTIONS for name, label, _ in fields}


def normalizar_valor(bruto):
    """Converte o campo Valor (R$) para float. Retorna (valor, erro)."""
    if not bruto:
        return None, None
    try:
        return float(bruto.replace(",", ".")), None
    except ValueError:
        return None, "O campo Valor (R$) precisa ser um número (ex.: 1500.00)."


def rotulo_equipamento(row):
    codigo = row["codigo"] if row["codigo"] else None
    nome = row["nome"] if row["nome"] else None
    if codigo and nome:
        return f"{codigo} - {nome}"
    return codigo or nome or f"#{row['id']}"


def registrar_historico(db, equipamento_id, label, acao, campo=None, valor_anterior=None, valor_novo=None):
    usuario = session.get("user_nome") or session.get("user_email") or "-"
    db.execute(
        "INSERT INTO equipamento_historico "
        "(equipamento_id, equipamento_label, acao, campo, valor_anterior, valor_novo, usuario) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (equipamento_id, label, acao, campo, valor_anterior, valor_novo, usuario),
    )


LIST_COLUMNS = [
    ("id", "ID"),
    ("codigo", "Código"),
    ("nome", "Nome"),
    ("tipo", "Tipo"),
    ("fabricante", "Fabricante"),
    ("funcionario", "Funcionário"),
    ("setor", "Setor"),
    ("estado", "Estado"),
    ("data_entrega", "Data de entrega"),
    ("valor", "Valor"),
]


@app.route("/healthz")
def healthz():
    return "ok", 200


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    erro = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()
        db.close()

        if user and user["password_hash"] and check_password_hash(user["password_hash"], senha):
            session.clear()
            session["user_id"] = user["id"]
            session["user_email"] = user["email"]
            session["user_nome"] = user["nome"] or user["email"]
            session["is_admin"] = bool(user["is_admin"])
            next_destino = request.args.get("next")
            destino = next_destino if _next_seguro(next_destino) else url_for("dashboard")
            return redirect(destino)

        erro = "E-mail ou senha inválidos."

    return render_template("login.html", erro=erro)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/login/redefinir")
def redefinir_senha():
    return render_template(
        "login.html",
        info="Para redefinir sua senha ou desbloquear seu acesso, entre em contato com o administrador do sistema.",
    )


@app.route("/")
@login_required
def dashboard():
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS n FROM equipamentos").fetchone()["n"]
    por_tipo = db.execute(
        "SELECT tipo, COUNT(*) AS n FROM equipamentos GROUP BY tipo ORDER BY n DESC"
    ).fetchall()
    por_estado = db.execute(
        "SELECT estado, COUNT(*) AS n FROM equipamentos GROUP BY estado ORDER BY n DESC"
    ).fetchall()
    valor_total = db.execute(
        "SELECT COALESCE(SUM(valor), 0) AS soma FROM equipamentos"
    ).fetchone()["soma"]
    db.close()
    return render_template(
        "dashboard.html",
        total=total,
        por_tipo=por_tipo,
        por_estado=por_estado,
        valor_total=valor_total,
    )


@app.route("/equipamentos")
@login_required
def listar_equipamentos():
    db = get_db()

    q = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "").strip()
    setor = request.args.get("setor", "").strip()
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    page = max(page, 1)

    where = []
    params = []
    if q:
        where.append(
            "(nome LIKE %s OR codigo LIKE %s OR funcionario LIKE %s OR sn LIKE %s)"
        )
        params += [f"%{q}%"] * 4
    if tipo:
        where.append("tipo = %s")
        params.append(tipo)
    if setor:
        where.append("setor = %s")
        params.append(setor)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    total = db.execute(
        f"SELECT COUNT(*) AS n FROM equipamentos {where_sql}", params
    ).fetchone()["n"]
    total_pages = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    page = min(page, total_pages)
    offset = (page - 1) * PER_PAGE

    equipamentos = db.execute(
        f"SELECT * FROM equipamentos {where_sql} ORDER BY id DESC LIMIT %s OFFSET %s",
        params + [PER_PAGE, offset],
    ).fetchall()

    tipos = [r["tipo"] for r in db.execute(
        "SELECT DISTINCT tipo FROM equipamentos WHERE tipo IS NOT NULL ORDER BY tipo"
    ).fetchall()]
    setores = [r["setor"] for r in db.execute(
        "SELECT DISTINCT setor FROM equipamentos WHERE setor IS NOT NULL ORDER BY setor"
    ).fetchall()]

    db.close()

    return render_template(
        "equipamentos_list.html",
        equipamentos=equipamentos,
        columns=LIST_COLUMNS,
        q=q,
        tipo=tipo,
        setor=setor,
        tipos=tipos,
        setores=setores,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@app.route("/equipamentos/novo", methods=["GET", "POST"])
@login_required
def novo_equipamento():
    if request.method == "POST":
        values = [request.form.get(f, "").strip() or None for f in ALL_FIELDS]
        idx_valor = ALL_FIELDS.index("valor")
        valor, erro_valor = normalizar_valor(values[idx_valor])
        if erro_valor:
            return render_template(
                "equipamento_form.html",
                sections=FORM_SECTIONS,
                equipamento=request.form,
                titulo="Novo equipamento",
                erro=erro_valor,
            )
        values[idx_valor] = valor

        db = get_db()
        placeholders = ", ".join("%s" for _ in ALL_FIELDS)
        columns_sql = ", ".join(ALL_FIELDS)
        cursor = db.execute(
            f"INSERT INTO equipamentos ({columns_sql}) VALUES ({placeholders}) RETURNING *",
            values,
        )
        novo = cursor.fetchone()
        registrar_historico(db, novo["id"], rotulo_equipamento(novo), "criado")
        db.commit()
        db.close()
        flash("Equipamento adicionado com sucesso.", "success")
        return redirect(url_for("listar_equipamentos"))

    return render_template(
        "equipamento_form.html",
        sections=FORM_SECTIONS,
        equipamento=None,
        titulo="Novo equipamento",
    )


@app.route("/equipamentos/<int:equipamento_id>/editar", methods=["GET", "POST"])
@login_required
def editar_equipamento(equipamento_id):
    db = get_db()

    if request.method == "POST":
        antigo = db.execute(
            "SELECT * FROM equipamentos WHERE id = %s", (equipamento_id,)
        ).fetchone()

        values = [request.form.get(f, "").strip() or None for f in ALL_FIELDS]
        idx_valor = ALL_FIELDS.index("valor")
        valor, erro_valor = normalizar_valor(values[idx_valor])
        if erro_valor:
            db.close()
            return render_template(
                "equipamento_form.html",
                sections=FORM_SECTIONS,
                equipamento=request.form,
                titulo=f"Editar equipamento #{equipamento_id}",
                erro=erro_valor,
            )
        values[idx_valor] = valor

        set_sql = ", ".join(f"{f} = %s" for f in ALL_FIELDS)
        db.execute(
            f"UPDATE equipamentos SET {set_sql} WHERE id = %s",
            values + [equipamento_id],
        )

        if antigo is not None:
            label = rotulo_equipamento(antigo)
            for campo, valor_novo in zip(ALL_FIELDS, values):
                valor_anterior = antigo[campo]
                if (valor_anterior or None) != (valor_novo or None):
                    registrar_historico(
                        db, equipamento_id, label, "editado",
                        campo=FIELD_LABELS[campo],
                        valor_anterior=valor_anterior,
                        valor_novo=valor_novo,
                    )

        db.commit()
        db.close()
        flash("Equipamento atualizado com sucesso.", "success")
        return redirect(url_for("listar_equipamentos"))

    equipamento = db.execute(
        "SELECT * FROM equipamentos WHERE id = %s", (equipamento_id,)
    ).fetchone()
    db.close()

    if equipamento is None:
        return redirect(url_for("listar_equipamentos"))

    return render_template(
        "equipamento_form.html",
        sections=FORM_SECTIONS,
        equipamento=equipamento,
        titulo=f"Editar equipamento #{equipamento_id}",
    )


@app.route("/equipamentos/<int:equipamento_id>/excluir", methods=["POST"])
@login_required
def excluir_equipamento(equipamento_id):
    db = get_db()
    equipamento = db.execute(
        "SELECT * FROM equipamentos WHERE id = %s", (equipamento_id,)
    ).fetchone()
    db.execute("DELETE FROM equipamentos WHERE id = %s", (equipamento_id,))
    if equipamento is not None:
        registrar_historico(db, equipamento_id, rotulo_equipamento(equipamento), "excluido")
    db.commit()
    db.close()
    flash("Equipamento excluído com sucesso.", "success")
    return redirect(url_for("listar_equipamentos"))


@app.route("/equipamentos/<int:equipamento_id>/historico")
@login_required
def historico_equipamento(equipamento_id):
    db = get_db()
    equipamento = db.execute(
        "SELECT * FROM equipamentos WHERE id = %s", (equipamento_id,)
    ).fetchone()
    historico = db.execute(
        "SELECT * FROM equipamento_historico WHERE equipamento_id = %s ORDER BY id DESC",
        (equipamento_id,),
    ).fetchall()
    db.close()

    label = rotulo_equipamento(equipamento) if equipamento else (
        historico[0]["equipamento_label"] if historico else f"#{equipamento_id}"
    )

    return render_template(
        "equipamento_historico.html",
        equipamento_id=equipamento_id,
        label=label,
        historico=historico,
    )


@app.route("/conta/senha", methods=["GET", "POST"])
@login_required
def trocar_senha():
    erro = None

    if request.method == "POST":
        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = %s", (session["user_id"],)).fetchone()

        if not user["password_hash"] or not check_password_hash(user["password_hash"], senha_atual):
            erro = "Senha atual incorreta."
        elif len(nova_senha) < SENHA_MIN_LEN:
            erro = f"A nova senha precisa ter pelo menos {SENHA_MIN_LEN} caracteres."
        elif nova_senha != confirmar_senha:
            erro = "A confirmação não confere com a nova senha."
        else:
            db.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (generate_password_hash(nova_senha), user["id"]),
            )
            db.commit()
            db.close()
            flash("Senha alterada com sucesso.", "success")
            return redirect(url_for("dashboard"))
        db.close()

    return render_template("conta_senha.html", erro=erro)


@app.route("/usuarios")
@admin_required
def listar_usuarios():
    db = get_db()
    usuarios = db.execute("SELECT * FROM users ORDER BY nome, email").fetchall()
    db.close()
    return render_template("usuarios_list.html", usuarios=usuarios)


@app.route("/usuarios/novo", methods=["GET", "POST"])
@admin_required
def novo_usuario():
    erro = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        nome = request.form.get("nome", "").strip()
        senha = request.form.get("senha", "")
        is_admin = 1 if request.form.get("is_admin") else 0

        if not email or not senha:
            erro = "Preencha e-mail e senha."
        elif len(senha) < SENHA_MIN_LEN:
            erro = f"A senha precisa ter pelo menos {SENHA_MIN_LEN} caracteres."
        else:
            db = get_db()
            existente = db.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()
            if existente:
                erro = "Já existe um usuário com esse e-mail."
                db.close()
            else:
                db.execute(
                    "INSERT INTO users (email, password_hash, nome, auth_provider, is_admin) "
                    "VALUES (%s, %s, %s, 'local', %s)",
                    (email, generate_password_hash(senha), nome or email, is_admin),
                )
                db.commit()
                db.close()
                flash("Usuário cadastrado com sucesso.", "success")
                return redirect(url_for("listar_usuarios"))

    return render_template("usuario_form.html", erro=erro)


@app.route("/usuarios/<int:user_id>/senha", methods=["GET", "POST"])
@admin_required
def redefinir_senha_usuario(user_id):
    db = get_db()
    usuario = db.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()
    if usuario is None:
        db.close()
        return redirect(url_for("listar_usuarios"))

    erro = None
    if request.method == "POST":
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if len(nova_senha) < SENHA_MIN_LEN:
            erro = f"A nova senha precisa ter pelo menos {SENHA_MIN_LEN} caracteres."
        elif nova_senha != confirmar_senha:
            erro = "A confirmação não confere com a nova senha."
        else:
            db.execute(
                "UPDATE users SET password_hash = %s, auth_provider = 'local' WHERE id = %s",
                (generate_password_hash(nova_senha), user_id),
            )
            db.commit()
            db.close()
            flash(f"Senha de {usuario['email']} redefinida com sucesso.", "success")
            return redirect(url_for("listar_usuarios"))

    db.close()
    return render_template("usuario_senha.html", usuario=usuario, erro=erro)


@app.route("/usuarios/<int:user_id>/excluir", methods=["POST"])
@admin_required
def excluir_usuario(user_id):
    if user_id == session.get("user_id"):
        flash("Você não pode remover o próprio acesso.", "error")
        return redirect(url_for("listar_usuarios"))
    db = get_db()
    db.execute("DELETE FROM users WHERE id = %s", (user_id,))
    db.commit()
    db.close()
    flash("Usuário removido com sucesso.", "success")
    return redirect(url_for("listar_usuarios"))


if __name__ == "__main__":
    app.run(debug=True)
