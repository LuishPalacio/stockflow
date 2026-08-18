"""Popula o banco com dados fictícios (usuários, equipamentos e histórico) só
para demonstração/portfólio. Nenhum dado aqui corresponde a pessoas, empresas
ou aparelhos reais - tudo é gerado aleatoriamente a partir de listas genéricas.

Uso:
    python seed_demo.py
"""
import random
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from db import ensure_schema, get_db

random.seed(7)

NOMES = [
    "Ana", "Bruno", "Carla", "Diego", "Elaine", "Fábio", "Gabriela", "Henrique",
    "Isabela", "João", "Larissa", "Marcos", "Natália", "Otávio", "Patrícia",
    "Rafael", "Sabrina", "Thiago", "Vanessa", "William", "Camila", "Eduardo",
]
SOBRENOMES = [
    "Silva", "Souza", "Oliveira", "Santos", "Pereira", "Costa", "Rodrigues",
    "Almeida", "Nascimento", "Carvalho", "Gomes", "Martins", "Araújo", "Melo",
    "Barbosa", "Ribeiro", "Teixeira",
]
SETORES = [
    "TI", "Financeiro", "RH", "Comercial", "Marketing", "Operações",
    "Jurídico", "Logística", "Atendimento", "Diretoria",
]

MODELOS_POR_TIPO = {
    "Notebook": [
        ("Dell", "Latitude 5420"), ("Dell", "Vostro 3400"),
        ("Lenovo", "ThinkPad E14"), ("Lenovo", "IdeaPad 3"),
        ("HP", "ProBook 440 G8"), ("Apple", "MacBook Air M1"),
        ("Acer", "Aspire 5"),
    ],
    "Desktop": [
        ("Dell", "OptiPlex 3080"), ("Lenovo", "ThinkCentre M70s"),
        ("HP", "EliteDesk 800 G6"), ("Positivo", "Master D160"),
    ],
    "Monitor": [
        ("LG", "24MK430H"), ("Samsung", "LS24R350FHL"),
        ("AOC", "24B2XH"), ("Dell", "P2422H"),
    ],
    "Celular": [
        ("Samsung", "Galaxy A54"), ("Motorola", "Moto G84"),
        ("Apple", "iPhone 12"), ("Xiaomi", "Redmi Note 12"),
    ],
    "Tablet": [
        ("Samsung", "Galaxy Tab A8"), ("Apple", "iPad 9ª geração"),
    ],
    "Impressora": [
        ("HP", "LaserJet M107w"), ("Epson", "EcoTank L3250"),
        ("Brother", "HL-L2350DW"),
    ],
    "Nobreak": [
        ("SMS", "Manager III 1200VA"), ("APC", "Back-UPS 600VA"),
    ],
}

FAIXA_VALOR = {
    "Notebook": (2500, 6500), "Desktop": (1800, 4500), "Monitor": (600, 1800),
    "Celular": (900, 3500), "Tablet": (800, 2800), "Impressora": (400, 1400),
    "Nobreak": (300, 900),
}

ESTADOS = ["Em uso"] * 6 + ["Em estoque"] * 2 + ["Manutenção"] + ["Descartado"]
SO_NOTEBOOK_DESKTOP = ["Windows 11 Pro", "Windows 10 Pro", "Ubuntu 22.04"]
PROCESSADORES = [
    "Intel Core i5-1135G7", "Intel Core i7-1165G7", "AMD Ryzen 5 5500U",
    "Intel Core i3-10110U", "Apple M1",
]
RAMS = ["8GB", "16GB", "32GB"]
ARMAZENAMENTOS = ["256GB SSD", "512GB SSD", "1TB HDD", "1TB SSD"]
RESOLUCOES = ["1920x1080", "2560x1440"]
TAXAS = ["60Hz", "75Hz", "144Hz"]
PAINEIS = ["IPS", "VA", "TN"]


def nome_funcionario():
    return f"{random.choice(NOMES)} {random.choice(SOBRENOMES)}"


def mac_falso():
    return ":".join(f"{random.randint(0, 255):02X}" for _ in range(6))


def serial_falso(prefixo, tamanho=8):
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789"
    return prefixo + "".join(random.choice(chars) for _ in range(tamanho))


def imei_falso():
    return "".join(str(random.randint(0, 9)) for _ in range(15))


def data_entrega_aleatoria():
    dias_atras = random.randint(15, 3 * 365)
    return (date.today() - timedelta(days=dias_atras)).isoformat()


def gerar_equipamento(indice, tipo):
    fabricante, modelo = random.choice(MODELOS_POR_TIPO[tipo])
    estado = random.choice(ESTADOS)
    minimo, maximo = FAIXA_VALOR[tipo]

    row = {
        "codigo": f"AT-{indice:04d}",
        "tipo": tipo,
        "fabricante": fabricante,
        "nome": f"{tipo} {fabricante} {modelo}",
        "modelo": modelo,
        "valor": round(random.uniform(minimo, maximo), 2),
        "estado": estado,
        "funcionario": None if estado in ("Em estoque", "Descartado") else nome_funcionario(),
        "data_entrega": None if estado == "Em estoque" else data_entrega_aleatoria(),
        "setor": None if estado == "Em estoque" else random.choice(SETORES),
        "sn": serial_falso("SN"),
        "pn": serial_falso("PN", 6),
        "so": None, "processador": None, "ram": None, "armazenamento": None,
        "carregador": None, "sn_carregador": None,
        "mac_rede": None, "mac_wifi": None,
        "imei1": None, "imei2": None,
        "resolucao": None, "proporcao": None, "taxa_atualizacao": None,
        "tipo_painel": None, "fonte": None, "saidas": None,
        "obs": None,
    }

    if tipo in ("Notebook", "Desktop"):
        row.update({
            "so": random.choice(SO_NOTEBOOK_DESKTOP),
            "processador": random.choice(PROCESSADORES),
            "ram": random.choice(RAMS),
            "armazenamento": random.choice(ARMAZENAMENTOS),
            "mac_rede": mac_falso(),
            "mac_wifi": mac_falso(),
        })
    elif tipo == "Celular":
        row.update({
            "imei1": imei_falso(),
            "imei2": imei_falso(),
            "carregador": random.choice(["Sim", "Não"]),
            "sn_carregador": serial_falso("CG", 6) if random.random() > 0.5 else None,
            "mac_wifi": mac_falso(),
        })
    elif tipo == "Tablet":
        row.update({
            "mac_wifi": mac_falso(),
            "armazenamento": random.choice(["64GB", "128GB", "256GB"]),
        })
    elif tipo == "Monitor":
        row.update({
            "resolucao": random.choice(RESOLUCOES),
            "proporcao": "16:9",
            "taxa_atualizacao": random.choice(TAXAS),
            "tipo_painel": random.choice(PAINEIS),
            "fonte": "Bivolt",
            "saidas": random.choice(["HDMI, VGA", "HDMI, DisplayPort"]),
        })

    if random.random() < 0.15:
        row["obs"] = random.choice([
            "Equipamento revisado no último inventário.",
            "Acompanha maleta de transporte.",
            "Tela com pequeno risco no canto, sem impacto no uso.",
            "Reservado para novo colaborador.",
        ])

    return row


def montar_equipamentos():
    quantidades = {
        "Notebook": 20, "Desktop": 10, "Monitor": 12, "Celular": 10,
        "Tablet": 4, "Impressora": 4, "Nobreak": 3,
    }
    equipamentos = []
    indice = 1
    for tipo, qtd in quantidades.items():
        for _ in range(qtd):
            equipamentos.append(gerar_equipamento(indice, tipo))
            indice += 1
    random.shuffle(equipamentos)
    return equipamentos


def semear_usuarios(db):
    usuarios_demo = [
        ("admin@demo.local", "Administrador Demo", "Demo@12345", 1),
        ("operador@demo.local", "Operador Demo", "Operador@123", 0),
    ]
    for email, nome, senha, is_admin in usuarios_demo:
        existente = db.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()
        if existente:
            continue
        db.execute(
            "INSERT INTO users (email, password_hash, nome, auth_provider, is_admin) "
            "VALUES (%s, %s, %s, 'local', %s)",
            (email, generate_password_hash(senha), nome, is_admin),
        )
    print("Usuários demo prontos:")
    print("  admin@demo.local     / Demo@12345   (administrador)")
    print("  operador@demo.local  / Operador@123 (usuário comum)")


def semear_equipamentos(db):
    db.execute("DELETE FROM equipamento_historico")
    db.execute("DELETE FROM equipamentos")

    colunas = list(gerar_equipamento(1, "Notebook").keys())
    placeholders = ", ".join("%s" for _ in colunas)
    columns_sql = ", ".join(colunas)

    ids = []
    for row in montar_equipamentos():
        valores = [row[c] for c in colunas]
        cur = db.execute(
            f"INSERT INTO equipamentos ({columns_sql}) VALUES ({placeholders}) RETURNING id, codigo, nome",
            valores,
        )
        inserido = cur.fetchone()
        ids.append(inserido)
        db.execute(
            "INSERT INTO equipamento_historico "
            "(equipamento_id, equipamento_label, acao, usuario) VALUES (%s, %s, 'criado', %s)",
            (inserido["id"], f"{inserido['codigo']} - {inserido['nome']}", "Administrador Demo"),
        )

    # Alguns registros extras de histórico para ilustrar edições de exemplo.
    exemplos_edicao = random.sample(ids, k=min(6, len(ids)))
    for item in exemplos_edicao:
        label = f"{item['codigo']} - {item['nome']}"
        db.execute(
            "INSERT INTO equipamento_historico "
            "(equipamento_id, equipamento_label, acao, campo, valor_anterior, valor_novo, usuario) "
            "VALUES (%s, %s, 'editado', %s, %s, %s, %s)",
            (item["id"], label, "Estado", "Em estoque", "Em uso", "Operador Demo"),
        )

    print(f"{len(ids)} equipamentos fictícios cadastrados.")


def main():
    ensure_schema()
    db = get_db()
    semear_usuarios(db)
    semear_equipamentos(db)
    db.commit()
    db.close()
    print("Base de demonstração pronta.")


if __name__ == "__main__":
    main()
