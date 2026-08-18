# StockFlow

Sistema web de controle de ativos de TI (notebooks, desktops, monitores, celulares, tablets, impressoras, nobreaks) desenvolvido com **Flask** e **PostgreSQL**.

> Projeto de portfólio com dados 100% fictícios.

## Funcionalidades

- **Autenticação local** com sessão, hash de senha (Werkzeug) e proteção CSRF em todos os formulários
- **Rate limiting** no login (10 tentativas/minuto) contra força bruta
- **Cadastro de equipamentos** com campos organizados por seção (identificação, alocação, configuração de notebook/desktop, celular, monitor)
- **Busca e filtros** por nome, código, funcionário, S/N, tipo e setor, com paginação
- **Histórico de alterações** por equipamento (auditoria de criação, edição campo a campo e exclusão)
- **Painel com indicadores**: total de equipamentos, valor total em estoque, distribuição por tipo e por estado
- **Gestão de usuários** com dois níveis de acesso (administrador / usuário comum)
- Pronto para rodar com **Docker Compose** (app + PostgreSQL), com segredos via Docker secrets

## Stack

| Camada     | Tecnologia                          |
|------------|--------------------------------------|
| Backend    | Python, Flask, Flask-WTF, Flask-Limiter |
| Banco      | PostgreSQL                          |
| Servidor   | Waitress (WSGI)                     |
| Frontend   | HTML + Jinja2, CSS puro, JS vanilla |
| Infra      | Docker, Docker Compose              |

## Como rodar localmente

Requer [Docker](https://www.docker.com/) instalado.

```bash
git clone <url-do-repositorio>
cd stockflow

# variáveis de ambiente
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # cole o valor em FLASK_SECRET_KEY no .env

# senha do Postgres (não vai para o .env nem para o git)
mkdir -p secrets
python -c "import secrets; print(secrets.token_hex(24))" > secrets/postgres_password.txt

# sobe o app + banco
docker compose up -d --build

# popula com dados fictícios de demonstração
docker compose exec stockflow python seed_demo.py
```

Acesse **http://localhost:8000**.

### Login de demonstração

| E-mail                | Senha         | Perfil          |
|------------------------|---------------|------------------|
| admin@demo.local       | Demo@12345    | Administrador    |
| operador@demo.local    | Operador@123  | Usuário comum    |

## Estrutura do projeto

```
app.py                 rotas e regras da aplicação
auth.py                autenticação e controle de acesso por sessão
db.py                  conexão com Postgres e criação do schema
seed_demo.py           gera equipamentos e usuários fictícios para demo
create_user.py         cria/atualiza um usuário local via linha de comando
serve.py               sobe o app com Waitress para uso na rede local
templates/             views Jinja2
static/                CSS e JS
docker-compose.yml      app + PostgreSQL, com segredo via Docker secret
```

## Sobre o projeto original

Este repositório é uma recriação para portfólio de um sistema que desenvolvi para controle de ativos de TI em uma empresa. A versão em produção não pode ser publicada por conter dados internos reais; esta versão reproduz a arquitetura e as funcionalidades com um banco populado por dados fictícios, para fins de demonstração.
