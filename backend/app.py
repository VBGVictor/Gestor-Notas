# backend/app.py

import os
from flask import (
    Flask, render_template, redirect, url_for,
    session, request, flash, abort
)
from functools import wraps
from urllib.parse import quote_plus
from models import db, Usuario, Paciente, Nota
from dotenv import load_dotenv

load_dotenv()

# ————————————————————————————————————————————————
# Helper decorator para proteger rotas que exigem login
# ————————————————————————————————————————————————
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ————————————————————————————————————————————————
# Configuração do Flask e caminhos de templates/estáticos
# ————————————————————————————————————————————————
BASE_DIR     = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'frontend', 'templates')
STATIC_DIR   = os.path.join(BASE_DIR, '..', 'frontend', 'static')

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR
)
app.secret_key = os.getenv('SECRET_KEY', 'muda_isso_para_algo_secreto')

# ————————————————————————————————————————————————
# Configuração do Banco de Dados (APENAS PostgreSQL)
# ————————————————————————————————————————————————
db_url = os.getenv('DATABASE_URL')
if not db_url:
    # Se não definiu DATABASE_URL, encerra o app com erro
    raise RuntimeError("A variável de ambiente DATABASE_URL não está configurada.")

# Escapa usuário e senha caso contenham caracteres especiais
if db_url.startswith("postgresql://"):
    # Ex.: postgresql://user:pass@host:port/dbname
    prefix, rest = db_url.split("://", 1)
    creds, host_part = rest.split("@", 1)
    user, pw = creds.split(":", 1)
    user = quote_plus('postgres')
    pw   = quote_plus('123456')
    db_url = f"postgresql://{user}:{pw}@{host_part}"

app.config['SQLALCHEMY_DATABASE_URI']        = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ————————————————————————————————————————————————
# Inicializa o SQLAlchemy e cria as tabelas
# ————————————————————————————————————————————————
db.init_app(app)
with app.app_context():
    db.create_all()

# ————————————————————————————————————————————————
# Rotas
# ————————————————————————————————————————————————

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.check_senha(senha):
            session['user_id'] = usuario.id
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome  = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        if not (nome and email and senha):
            flash('Preencha todos os campos.', 'warning')
        elif Usuario.query.filter_by(email=email).first():
            flash('E-mail já cadastrado.', 'danger')
        else:
            novo = Usuario(nome=nome, email=email)
            novo.set_senha(senha)
            db.session.add(novo)
            db.session.commit()
            flash('Registro realizado! Faça login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_notas  = Nota.query.count()
    soma_valores = db.session.query(db.func.sum(Nota.valor)).scalar() or 0.0
    receita_total = soma_valores
    despesa_total = 0.0  # ajuste quando tiver campo de tipo
    lucro         = receita_total - despesa_total
    return render_template(
        'dashboard.html',
        total_notas=f"{total_notas}",
        receita_total=f"{receita_total:.2f}",
        despesa_total=f"{despesa_total:.2f}",
        lucro=f"{lucro:.2f}"
    )

@app.route('/notas')
@login_required
def notas():
    notas_list = Nota.query.order_by(Nota.data.desc()).all()
    return render_template('notas.html', notas=notas_list)

@app.route('/notas/<int:nota_id>')
@login_required
def nota_detalhe(nota_id):
    nota = Nota.query.get_or_404(nota_id)
    return render_template('nota_detalhe.html', nota=nota)

@app.route('/importar', methods=['GET', 'POST'])
@login_required
def importar():
    sucesso = False
    if request.method == 'POST':
        # lógica de upload/importação...
        sucesso = True
        flash('Importação executada.', 'success')
    return render_template('importar.html', sucesso=sucesso)

# Executa o servidor
if __name__ == '__main__':
    app.run(debug=True)
