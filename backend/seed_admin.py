# backend/seed_admin.py

import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from flask import Flask
from models import db, Usuario

# 1) Carrega variáveis de ambiente (force o encoding se necessário)
load_dotenv(encoding='utf-8')  # substitua por 'latin-1' se precisar

# 2) Replica a lógica de parsing de DATABASE_URL do app.py
db_url = os.getenv('DATABASE_URL')
if not db_url:
    raise RuntimeError("A variável de ambiente DATABASE_URL não está configurada.")

# Se for postgresql://, escapa credenciais
if db_url.startswith("postgresql://"):
    prefix, rest = db_url.split("://", 1)
    creds, host_part = rest.split("@", 1)
    parsed_user, parsed_pw = creds.split(":", 1) # Parses user and pw
    encoded_user = quote_plus(parsed_user) # Uses parsed user
    encoded_pw   = quote_plus(parsed_pw)   # Uses parsed pw
    db_url = f"postgresql://{encoded_user}:{encoded_pw}@{host_part}"

# 3) Prepara app Flask apenas para rodar o seed
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']        = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 4) Inicializa o DB e cria as tabelas (caso ainda não existam)
db.init_app(app)
with app.app_context():
    db.create_all()

    # 5) Insere o admin, se não existir
    admin_email = 'admin@admin.com'
    if not Usuario.query.filter_by(email=admin_email).first():
        admin = Usuario(nome='Administrador', email=admin_email)
        admin.set_senha('admin123')  # ALTERE ESSA SENHA APÓS O PRIMEIRO LOGIN
        db.session.add(admin)
        db.session.commit()
        print("🛡️  Usuário administrador criado: admin@admin.com / admin123")
    else:
        print("ℹ️  Usuário administrador já existe.")
