# backend/app.py
import os
from flask import Flask, render_template, redirect, url_for, session, request, flash
from functools import wraps

# Simulação de um "banco de dados" de usuários em memória
usuarios = {}

# Decorator para rotas que exigem login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Ajuste dos caminhos dos templates e arquivos estáticos
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'frontend', 'templates')
STATIC_DIR = os.path.join(BASE_DIR, '..', 'frontend', 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = 'segredo-super-seguro'

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        if email in usuarios and usuarios[email] == senha:
            session['user_id'] = email
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        if not email or not senha:
            flash('Preencha todos os campos.', 'warning')
            return render_template('register.html')
        if email in usuarios:
            flash('E-mail já cadastrado.', 'danger')
            return render_template('register.html')
        usuarios[email] = senha
        flash('Registro realizado com sucesso! Faça login.', 'success')
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
    total_notas = 0
    receita_total = "0.00"
    despesa_total = "0.00"
    lucro = "0.00"
    return render_template(
        'dashboard.html',
        total_notas=total_notas,
        receita_total=receita_total,
        despesa_total=despesa_total,
        lucro=lucro
    )

@app.route('/notas')
@login_required
def notas():
    notas_list = []
    return render_template('notas.html', notas=notas_list)

@app.route('/notas/<int:nota_id>')
@login_required
def nota_detalhe(nota_id):
    nota = {
        'id': nota_id,
        'paciente': {'nome': 'Nome Exemplo', 'cpf': '000.000.000-00'},
        'data': '01/01/2025',
        'valor': '0.00',
        'descricao': 'Detalhes da nota'
    }
    return render_template('nota_detalhe.html', nota=nota)

@app.route('/importar')
@login_required
def importar():
    return render_template('importar.html', sucesso=False)

if __name__ == '__main__':
    app.run(debug=True)
