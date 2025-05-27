# backend/auth.py
from flask import render_template, request, redirect, url_for, session
from models import Usuario, db

def login_user():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        user = Usuario.query.filter_by(email=email).first()
        if user and user.check_senha(senha):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='E-mail ou senha incorretos.')
    return render_template('login.html')

def register_user():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        if Usuario.query.filter_by(email=email).first():
            return 'E-mail já cadastrado'
        user = Usuario(nome=nome, email=email)
        user.set_senha(senha)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

def logout_user():
    session.pop('user_id', None)
    return redirect(url_for('login'))

def is_logged_in():
    return 'user_id' in session