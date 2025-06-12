# backend/models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self):
        return f"<Usuario {self.email}>"

class Paciente(db.Model):
    __tablename__ = 'pacientes'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    profissao = db.Column(db.String(120), nullable=True)
    cep = db.Column(db.String(10), nullable=False)
    endereco = db.Column(db.String(200), nullable=True)
    idade = db.Column(db.Integer, nullable=True)
    valor_sessao  = db.Column(db.Float, nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    notas = db.relationship('Nota', backref='paciente', lazy=True)

    def __repr__(self):
        return f"<Paciente {self.nome}>"

class Nota(db.Model):
    __tablename__ = 'notas'

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    data = db.Column(db.Date, default=datetime.utcnow)
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Nota {self.id} - Paciente {self.paciente_id}>"


class Transacao(db.Model):
    __tablename__ = 'transacoes'

    id         = db.Column(db.Integer, primary_key=True)
    nome       = db.Column(db.String(120), nullable=False)
    tipo       = db.Column(db.String(10), nullable=False) 
    observacao = db.Column(db.Text, nullable=True)
    valor      = db.Column(db.Float, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Transacao {self.tipo} {self.nome}: {self.valor}>"
