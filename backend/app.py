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
from flask_migrate import Migrate
from flask import abort
from models import Transacao

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
migrate = Migrate(app, db)

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
@login_required
def register():
    # opcional: verificar se o usuário é admin
    usuario_logado = Usuario.query.get(session['user_id'])
    if not usuario_logado.email == 'admin@admin.com':
        flash('Apenas o administrador pode registrar novos usuários.', 'danger')
        return redirect(url_for('dashboard'))

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
            flash('Usuário registrado com sucesso.', 'success')
            return redirect(url_for('dashboard'))
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
    # Pacientes ativos
    ativos = Paciente.query.filter_by(active=True).all()
    total_pacientes    = len(ativos)
    soma_sessoes       = sum(p.valor_sessao or 0.0 for p in ativos)
    valor_medio_sessao = (soma_sessoes / total_pacientes) if total_pacientes else 0.0

    total_notas = Nota.query.count()

    from models import Transacao
    receita_total = db.session.query(db.func.sum(Transacao.valor)).filter_by(tipo='receita').scalar() or 0.0
    despesa_total = db.session.query(db.func.sum(Transacao.valor)).filter_by(tipo='despesa').scalar() or 0.0
    lucro = receita_total - despesa_total

    return render_template('dashboard.html',
        total_pacientes=total_pacientes,
        valor_medio_sessao=f"{valor_medio_sessao:.2f}",
        total_notas=total_notas,
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

@app.route('/pacientes/novo', methods=['GET', 'POST'])
@login_required
def novo_paciente():
    if request.method == 'POST':
        nome      = request.form.get('nome')
        cpf       = request.form.get('cpf')
        profissao = request.form.get('profissao')
        cep       = request.form.get('cep')
        endereco  = request.form.get('endereco')
        idade     = request.form.get('idade')
        valor_sessao = request.form.get('valor_sessao')

        if not (nome and cpf and cep and valor_sessao):
            flash('Nome, CPF, CEP e Valor da Sessão são obrigatórios.', 'warning')
        else:
            # cria paciente
            p = Paciente(
                nome=nome, cpf=cpf, profissao=profissao or None,
                cep=cep, endereco=endereco or None,
                idade=int(idade) if idade else None,
                valor_sessao=float(valor_sessao)
            )
            db.session.add(p)
            db.session.commit()

            # registra receita única inicial
            t = Transacao(
                nome=f"Receita inicial — {p.nome}",
                tipo='receita',
                observacao='Receita única ao cadastrar paciente',
                valor=float(valor_sessao)
            )
            db.session.add(t)
            db.session.commit()

            flash('Paciente e receita inicial cadastrados com sucesso!', 'success')
            return redirect(url_for('listar_pacientes'))
    return render_template('novo_paciente.html')

@app.route('/pacientes')
@login_required
def listar_pacientes():
    pacientes = Paciente.query.all()
    return render_template('pacientes.html', pacientes=pacientes)

# Mostrar formulário de edição
@app.route('/pacientes/<int:paciente_id>/edit', methods=['GET'])
@login_required
def editar_paciente(paciente_id):
    p = Paciente.query.get_or_404(paciente_id)
    return render_template('editar_paciente.html', paciente=p)

# Processar edição
@app.route('/pacientes/<int:paciente_id>/edit', methods=['POST'])
@login_required
def atualizar_paciente(paciente_id):
    p = Paciente.query.get_or_404(paciente_id)
    # captura os dados do form
    nome         = request.form.get('nome')
    cpf          = request.form.get('cpf')
    profissao    = request.form.get('profissao')
    cep          = request.form.get('cep')
    endereco     = request.form.get('endereco')
    idade        = request.form.get('idade')
    valor_sessao = request.form.get('valor_sessao')

    # valida obrigatórios
    if not (nome and cpf and cep):
        flash('Nome, CPF e CEP são obrigatórios.', 'warning')
        return redirect(url_for('editar_paciente', paciente_id=p.id))

    # atualiza campos
    p.nome         = nome
    p.cpf          = cpf
    p.profissao    = profissao or None
    p.cep          = cep
    p.endereco     = endereco or None
    p.idade        = int(idade) if idade else None
    p.valor_sessao = float(valor_sessao) if valor_sessao else None

    db.session.commit()
    flash('Paciente atualizado com sucesso!', 'success')
    return redirect(url_for('listar_pacientes'))

@app.route('/pacientes/<int:paciente_id>/sessao', methods=['POST'])
@login_required
def registrar_sessao(paciente_id):
    p = Paciente.query.get_or_404(paciente_id)
    if not p.active:
        flash('Não é possível registrar sessão para paciente inativo.', 'warning')
    else:
        t = Transacao(
            nome=f"Sessão — {p.nome}",
            tipo='receita',
            observacao='Sessão avulsa registrada manualmente',
            valor=p.valor_sessao or 0.0
        )
        db.session.add(t)
        db.session.commit()
        flash('Sessão registrada como receita.', 'success')
    return redirect(url_for('listar_pacientes'))

@app.route('/pacientes/<int:paciente_id>/toggle', methods=['POST'])
@login_required
def toggle_paciente(paciente_id):
    p = Paciente.query.get_or_404(paciente_id)
    p.active = not p.active
    db.session.commit()
    status = 'ativado' if p.active else 'desativado'
    flash(f'Paciente {status} com sucesso.', 'info')
    return redirect(url_for('listar_pacientes'))

@app.route('/transacoes')
@login_required
def transacoes():
    
    receitas = Transacao.query.filter_by(tipo='receita')\
                  .order_by(Transacao.id.desc()).all()
    despesas = Transacao.query.filter_by(tipo='despesa')\
                  .order_by(Transacao.id.desc()).all()
    return render_template('transacoes.html',
                           receitas=receitas,
                           despesas=despesas)



@app.route('/transacoes/novo', methods=['GET', 'POST'])
@login_required
def novo_transacao():
    if request.method == 'POST':
        nome       = request.form.get('nome')
        tipo       = request.form.get('tipo')
        observacao = request.form.get('observacao')
        valor      = request.form.get('valor')

        if not (nome and tipo and valor):
            flash('Nome, tipo e valor são obrigatórios.', 'warning')
        else:
            t = Transacao(
                nome=nome,
                tipo=tipo,
                observacao=observacao or None,
                valor=float(valor)
            )
            db.session.add(t)
            db.session.commit()
            flash('Transação registrada com sucesso!', 'success')
            return redirect(url_for('listar_transacoes'))
    return render_template('novo_transacao.html')

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
