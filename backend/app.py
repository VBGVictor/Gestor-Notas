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
from flask import request, render_template, jsonify
from datetime import datetime, timedelta
from models import Transacao  
from sqlalchemy import extract

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
                nome=f"{p.nome}",
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
            nome=f"{p.nome}",
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
    periodo = request.args.get('periodo', '') 
    ordenar_por = request.args.get('ordenar_por', 'data_criacao')
    ordem = request.args.get('ordem', 'desc')

    hoje = datetime.today()
    receitas_query = Transacao.query.filter_by(tipo='receita')
    despesas_query = Transacao.query.filter_by(tipo='despesa')

    if periodo == 'hoje':
        receitas_query = receitas_query.filter(
            extract('day', Transacao.data_criacao) == hoje.day,
            extract('month', Transacao.data_criacao) == hoje.month,
            extract('year', Transacao.data_criacao) == hoje.year)
        despesas_query = despesas_query.filter(
            extract('day', Transacao.data_criacao) == hoje.day,
            extract('month', Transacao.data_criacao) == hoje.month,
            extract('year', Transacao.data_criacao) == hoje.year)
    elif periodo == 'semana':
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        receitas_query = receitas_query.filter(Transacao.data_criacao >= inicio_semana)
        despesas_query = despesas_query.filter(Transacao.data_criacao >= inicio_semana)
    elif periodo == 'mes':
        receitas_query = receitas_query.filter(
            extract('month', Transacao.data_criacao) == hoje.month,
            extract('year', Transacao.data_criacao) == hoje.year)
        despesas_query = despesas_query.filter(
            extract('month', Transacao.data_criacao) == hoje.month,
            extract('year', Transacao.data_criacao) == hoje.year)
    elif periodo == '30':
        inicio = hoje - timedelta(days=30)
        receitas_query = receitas_query.filter(Transacao.data_criacao >= inicio)
        despesas_query = despesas_query.filter(Transacao.data_criacao >= inicio)
    elif periodo == '60':
        inicio = hoje - timedelta(days=60)
        receitas_query = receitas_query.filter(Transacao.data_criacao >= inicio)
        despesas_query = despesas_query.filter(Transacao.data_criacao >= inicio)

    colunas_validas = {'nome', 'observacao', 'data_criacao', 'valor'}
    if ordenar_por not in colunas_validas:
        ordenar_por = 'data_criacao'

    ordenar_campo = getattr(Transacao, ordenar_por)
    if ordem == 'asc':
        receitas_query = receitas_query.order_by(ordenar_campo.asc())
        despesas_query = despesas_query.order_by(ordenar_campo.asc())
    else:
        receitas_query = receitas_query.order_by(ordenar_campo.desc())
        despesas_query = despesas_query.order_by(ordenar_campo.desc())

    receitas = receitas_query.all()
    despesas = despesas_query.all()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('partials/tabela_transacoes.html',
                               receitas=receitas,
                               despesas=despesas,
                               ordenar_por=ordenar_por,
                               ordem=ordem)
    else:
     return render_template(
        'transacoes.html',
        receitas=receitas,
        despesas=despesas,
        filtro_periodo=periodo,
        ordenar_por=ordenar_por,
        ordem=ordem
     )

@app.route('/transacoes/novo', methods=['GET', 'POST'])
@login_required
def novo_transacao():
    if request.method == 'POST':
        nome = request.form.get('nome')
        observacao = request.form.get('observacao')
        valor = request.form.get('valor')
        tipo = request.form.get('tipo')  

        if not nome or not valor or not tipo:
            flash('Nome, valor e tipo são obrigatórios.', 'danger')
            return redirect(url_for('novo_transacao'))

        try:
            valor = float(valor.replace(',', '.'))
        except ValueError:
            flash('Valor inválido.', 'danger')
            return redirect(url_for('novo_transacao'))

        nova = Transacao(nome=nome, observacao=observacao, valor=valor, tipo=tipo, data_criacao=datetime.now())

        flash('Transação criada com sucesso!', 'success')
        return redirect(url_for('transacoes'))

    return render_template('novo_transacao.html')

@app.route('/transacoes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_transacao(id):
    t = Transacao.query.get_or_404(id)

    if request.method == 'POST':
        nome       = request.form.get('nome')
        tipo       = request.form.get('tipo')
        observacao = request.form.get('observacao')
        valor      = request.form.get('valor')
        data_str   = request.form.get('data') 

        if not (nome and tipo and valor and data_str):
            flash('Nome, tipo, valor e data são obrigatórios.', 'warning')
        else:
            t.nome = nome
            t.tipo = tipo
            t.observacao = observacao or None
            t.valor = float(valor)

            try:
                data_nova = datetime.strptime(data_str, '%Y-%m-%d')
               
                hora =  0
                minuto =  0

                t.data_criacao = datetime(
                    data_nova.year,
                    data_nova.month,
                    data_nova.day,
                    hora,
                    minuto
                )
            except ValueError:
                flash('Data inválida.', 'warning')
                return render_template('editar_transacao.html', transacao=t)

            db.session.commit()
            flash('Transação atualizada com sucesso!', 'success')
            return redirect(url_for('transacoes'))

    return render_template('editar_transacao.html', transacao=t)


@app.route('/transacoes/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_transacao(id):
    t = Transacao.query.get_or_404(id)
    db.session.delete(t)
    db.session.commit()
    flash('Transação excluída com sucesso!', 'success')
    return redirect(url_for('transacoes'))

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
