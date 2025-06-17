# backend/app.py
import sys
import os

# Adiciona o diretório raiz do projeto (Site) no sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Carrega variáveis de ambiente antes de qualquer coisa
from dotenv import load_dotenv
load_dotenv()

from flask import (
    Flask, render_template, redirect, url_for,
    session, request, flash, abort, jsonify
)
from functools import wraps
from datetime import datetime, timedelta # timedelta já estava, mas é usado aqui
from urllib.parse import quote_plus
from flask_migrate import Migrate
from sqlalchemy import extract

# Import absoluto das models
from backend.models import (
     Usuario, Paciente, Nota,
    Transacao, Simulacao, SimulacaoItem, SimulacaoEvento
)
from backend.db import db


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
    parsed_user, parsed_pw = creds.split(":", 1)
    encoded_user = quote_plus(parsed_user)
    encoded_pw   = quote_plus(parsed_pw)
    db_url = f"postgresql://{encoded_user}:{encoded_pw}@{host_part}"

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

@app.route('/forgot_password', methods=['GET', 'POST'])
def request_reset_token():
    if request.method == 'POST':
        email = request.form.get('email')
        user = Usuario.query.filter_by(email=email).first()
        if user:
            token = user.get_reset_token()
            db.session.commit()
            print(f"DEBUG: Link para redefinir senha para {user.email}: {url_for('reset_token', token=token, _external=True)}") # Linha de DEBUG
            flash('Um e-mail (simulado) foi enviado com instruções para redefinir sua senha.', 'info')
            return redirect(url_for('login'))
        else:
            flash('E-mail não encontrado em nosso sistema.', 'warning')
    return render_template('request_reset_token.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    user = Usuario.verify_reset_token(token)
    if not user:
        flash('O token de redefinição é inválido ou expirou.', 'warning')
        return redirect(url_for('request_reset_token'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if not password or not confirm_password or password != confirm_password:
            flash('As senhas não conferem ou estão vazias.', 'danger')
            return render_template('reset_password.html', token=token)

        user.set_senha(password)
        user.reset_token = None # Invalida o token após o uso
        user.reset_token_expiration = None
        db.session.commit()
        flash('Sua senha foi atualizada com sucesso!', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)

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
            try:
                valor_sessao_float = float(valor_sessao.replace(',', '.'))
                
                # cria paciente
                p = Paciente(
                    nome=nome, cpf=cpf, profissao=profissao or None,
                    cep=cep, endereco=endereco or None,
                    idade=int(idade) if idade and idade.strip() else None,
                    valor_sessao=valor_sessao_float
                )
                db.session.add(p)
                db.session.commit() # Commit paciente para obter ID se necessário, ou mover para depois da transação

                # registra receita única inicial
                t = Transacao(
                    nome=f"{p.nome}",
                    tipo='receita',
                    observacao='Receita única ao cadastrar paciente',
                    valor=valor_sessao_float
                )
                db.session.add(t)
                db.session.commit()

                flash('Paciente e receita inicial cadastrados com sucesso!', 'success')
                return redirect(url_for('listar_pacientes'))
            except ValueError:
                flash('Valor da sessão inválido. Use números e ponto ou vírgula como separador decimal.', 'danger')
            except Exception as e:
                flash(f'Ocorreu um erro ao criar o paciente: {e}', 'danger')
                db.session.rollback()
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
    p.idade        = int(idade) if idade and idade.strip() else None
    
    try:
        p.valor_sessao = float(valor_sessao.replace(',', '.')) if valor_sessao and valor_sessao.strip() else None
        db.session.commit()
        flash('Paciente atualizado com sucesso!', 'success')
        return redirect(url_for('listar_pacientes'))
    except ValueError:
        flash('Valor da sessão inválido. Use números e ponto ou vírgula como separador decimal.', 'danger')
        return redirect(url_for('editar_paciente', paciente_id=p.id))
    except Exception as e:
        flash(f'Ocorreu um erro ao atualizar o paciente: {e}', 'danger')
        db.session.rollback()
        return redirect(url_for('editar_paciente', paciente_id=p.id))

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
        db.session.add(nova) # Adiciona a nova transação à sessão
        db.session.commit()  # Persiste a transação no banco de dados

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
            try:
                valor_float = float(valor.replace(',', '.'))
                data_nova = datetime.strptime(data_str, '%Y-%m-%d')
               
                hora =  0
                minuto =  0

                t.nome = nome
                t.tipo = tipo
                t.observacao = observacao or None
                t.valor = valor_float
                t.data_criacao = datetime(
                    data_nova.year,
                    data_nova.month,
                    data_nova.day,
                    hora,
                    minuto
                )
                db.session.commit()
                flash('Transação atualizada com sucesso!', 'success')
                return redirect(url_for('transacoes'))
            except ValueError as ve:
                flash(f'Valor ou Data inválida: {ve}. Use ponto ou vírgula para decimais e formato AAAA-MM-DD para data.', 'warning')
                return render_template('editar_transacao.html', transacao=t)
            except Exception as e:
                flash(f'Ocorreu um erro ao atualizar a transação: {e}', 'danger')
                db.session.rollback()
                return render_template('editar_transacao.html', transacao=t)

    return render_template('editar_transacao.html', transacao=t)

# LISTA
@app.route('/simulacoes')
@login_required
def lista_simulacoes():
    sims = Simulacao.query.order_by(Simulacao.created_at.desc()).all()
    return render_template('simulacoes.html', simulacoes=sims)

# NOVA
@app.route('/simulacoes/novo', methods=['GET','POST'])
@login_required
def nova_simulacao():
    if request.method=='POST':
        nome = request.form.get('nome_simulacao') # Usar o mesmo nome de campo do form de edição
        if not nome:
            flash('O nome da simulação é obrigatório.', 'warning')
            # Passar um eventos_dict vazio para consistência com a edição
            return render_template('simulacao_form.html', simulacao=None, eventos_dict={})

        sim = Simulacao(nome=nome)
        db.session.add(sim)
        db.session.commit()
        flash('Simulação criada. Agora adicione os itens e eventos.', 'info')
        return redirect(url_for('editar_simulacao', id=sim.id))
    # Para GET, passar um eventos_dict vazio
    return render_template('simulacao_form.html', simulacao=None, eventos_dict={})

# EDITAR
@app.route('/simulacoes/<int:id>/edit', methods=['GET','POST'])
@login_required
def editar_simulacao(id):
    sim = Simulacao.query.get_or_404(id)

    if request.method=='POST':
        # Atualiza o nome da simulação
        novo_nome_simulacao = request.form.get('nome_simulacao')
        if not novo_nome_simulacao:
            flash('O nome da simulação não pode ficar vazio.', 'danger')
            eventos_dict_error = {evento.mes_offset: evento for evento in sim.eventos}
            return render_template('simulacao_form.html', simulacao=sim, eventos_dict=eventos_dict_error)
        
        sim.nome = novo_nome_simulacao
 
        # Atualiza a despesa mensal fixa
        # Pega o valor do formulário. Se o campo não existir ou estiver vazio, get retorna None ou ''
        despesa_str = request.form.get('despesa_mensal_fixa') 
        try:
            if despesa_str and despesa_str.strip(): # Verifica se não é None e não é apenas espaços
                sim.despesa_mensal_fixa = float(despesa_str.replace(',', '.'))
            else:
                sim.despesa_mensal_fixa = 0.0 # Define como 0.0 se o campo estiver vazio ou não fornecido
        except ValueError:
            flash(f'Valor inválido para Despesa Mensal ("{despesa_str}"). Use ponto como separador decimal.', 'danger')
            eventos_dict_error = {evento.mes_offset: evento for evento in sim.eventos}
            return render_template('simulacao_form.html', simulacao=sim, eventos_dict=eventos_dict_error)

        # limpar itens/eventos antigos
        SimulacaoItem.query.filter_by(simulacao_id=id).delete()
        SimulacaoEvento.query.filter_by(simulacao_id=id).delete()
        
        # itens
        for i in range(1,5): # Supondo um máximo de 4 tipos de itens
            cnt_str = request.form.get(f'pacientes_{i}')
            val_str = request.form.get(f'valor_{i}')

            if cnt_str and val_str: # Apenas processa se ambos os campos do item estiverem presentes
                try:
                    pacientes = int(cnt_str)
                    # Substitui vírgula por ponto ANTES de converter para float
                    valor_sessao = float(val_str.replace(',', '.'))
                    
                    db.session.add(SimulacaoItem(
                        simulacao_id=id,
                        pacientes=pacientes,
                        valor_sessao=valor_sessao
                    ))
                except ValueError:
                    flash(f'Valor inválido para item {i} (Nº Pacientes: "{cnt_str}", Valor Sessão: "{val_str}"). Verifique os números e use ponto como separador decimal para valores.', 'danger')
                    # Recarregar o formulário com os dados atuais para correção
                    eventos_dict_error = {evento.mes_offset: evento for evento in sim.eventos}
                    return render_template('simulacao_form.html', simulacao=sim, eventos_dict=eventos_dict_error)

        # eventos
        for m in range(6): # Para 6 meses
            delta_str = request.form.get(f'evento_{m}')
            if delta_str: # Apenas processa se o campo do evento estiver presente
                try:
                    delta = int(delta_str)
                    db.session.add(SimulacaoEvento(simulacao_id=id, mes_offset=m, delta=delta))
                except ValueError:
                    flash(f'Valor inválido para o evento do Mês {m+1} (Delta: "{delta_str}"). Deve ser um número inteiro.', 'danger')
                    eventos_dict_error = {evento.mes_offset: evento for evento in sim.eventos}
                    return render_template('simulacao_form.html', simulacao=sim, eventos_dict=eventos_dict_error)

        db.session.commit()
        flash('Simulação salva.', 'success')
        return redirect(url_for('detalhe_simulacao', id=id))
    
    # Para o método GET, preparar dados para o formulário
    # Os itens já estão em sim.itens
    # Para os eventos, um dicionário facilita o acesso no template
    eventos_dict = {evento.mes_offset: evento for evento in sim.eventos}
    return render_template('simulacao_form.html', simulacao=sim, eventos_dict=eventos_dict)

# DETALHE + GRÁFICO
@app.route('/simulacoes/<int:id>')
@login_required
def detalhe_simulacao(id):
    sim = Simulacao.query.get_or_404(id)

    # Fator para converter valor de sessão em valor mensal (assumindo 1 sessão/semana, 4 semanas/mês)
    FATOR_SESSOES_MES = 4

    # Calcular a renda mensal base e o valor de sessão unitário para o delta
    renda_mensal_base = 0.0
    valor_unitario_mensal_para_delta = 0.0 # Impacto MENSAL de 1 paciente do delta

    if sim.itens:
        soma_pacientes_base_total = 0
        soma_valores_sessao_individuais_itens = 0.0 # Soma dos valores de UMA sessão para cada tipo de item

        for item in sim.itens:
            pacientes_do_item = item.pacientes or 0
            valor_sessao_do_item = item.valor_sessao or 0.0

            # Acumula a renda mensal base considerando 4 sessões por mês por paciente
            renda_mensal_base += pacientes_do_item * valor_sessao_do_item * FATOR_SESSOES_MES
            
            soma_pacientes_base_total += pacientes_do_item
            soma_valores_sessao_individuais_itens += valor_sessao_do_item

        if soma_pacientes_base_total > 0:
            # O valor unitário para o delta é a média ponderada do valor MENSAL por paciente
            valor_unitario_mensal_para_delta = renda_mensal_base / soma_pacientes_base_total
        elif len(sim.itens) > 0 :
            # Se não há pacientes base, o valor unitário para o delta é a média simples
            # dos valores de sessão MENSAIS dos tipos de item.
            media_valor_sessao_individual = soma_valores_sessao_individuais_itens / len(sim.itens)
            valor_unitario_mensal_para_delta = media_valor_sessao_individual * FATOR_SESSOES_MES

    labels = []
    data_receita_projetada = []
    data_despesas_totais = []
    data_resultado_liquido = []

    renda_mensal_projetada_acumulada = renda_mensal_base
    despesa_mensal_simulacao = sim.despesa_mensal_fixa or 0.0
    
    # Para a tabela detalhada
    dados_tabela_projecao = []
    for m in range(6):
        mes_label = f'Mês {m+1}'
        labels.append(mes_label)

        # Busca evento para o mês atual (m é o offset, 0 = Mês 1)
        evt = next((e for e in sim.eventos if e.mes_offset == m), None)
        if evt:
            delta_pacientes_mes = evt.delta or 0
            renda_mensal_projetada_acumulada += delta_pacientes_mes * valor_unitario_mensal_para_delta
        else:
            delta_pacientes_mes = 0
        
        valor_mensal_atual = round(renda_mensal_projetada_acumulada, 2)
        resultado_liquido_mes = round(valor_mensal_atual - despesa_mensal_simulacao, 2)

        data_receita_projetada.append(valor_mensal_atual)
        data_despesas_totais.append(round(despesa_mensal_simulacao, 2))
        data_resultado_liquido.append(resultado_liquido_mes)

        dados_tabela_projecao.append({
            "mes": mes_label,
            "delta_pacientes": delta_pacientes_mes,
            "mensal": valor_mensal_atual,
            "semanal_estimada": round(valor_mensal_atual / 4.33, 2) if valor_mensal_atual > 0 else 0.0,
            "despesa_total_mes": round(despesa_mensal_simulacao, 2),
            "resultado_liquido_mes": resultado_liquido_mes
        })

    return render_template('simulacao_detail.html', sim=sim, labels=labels, 
                           data_receita_projetada=data_receita_projetada, data_despesas_totais=data_despesas_totais,
                           data_resultado_liquido=data_resultado_liquido, dados_tabela_projecao=dados_tabela_projecao)

# EXCLUIR
@app.route('/simulacoes/<int:id>/delete', methods=['POST'])
@login_required
def delete_simulacao(id):
    sim = Simulacao.query.get_or_404(id)
    db.session.delete(sim)
    db.session.commit()
    flash('Simulação removida.', 'info')
    return redirect(url_for('lista_simulacoes'))


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
