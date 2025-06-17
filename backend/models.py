from backend.db import db
from sqlalchemy import Column, Integer, String
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    senha_hash = Column(String(256), nullable=False)

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
    valor_sessao = db.Column(db.Float, nullable=True)
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

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    observacao = db.Column(db.Text, nullable=True)
    valor = db.Column(db.Float, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Transacao {self.tipo} {self.nome}: {self.valor}>"

class Simulacao(db.Model):
    __tablename__ = 'simulacoes'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    despesa_mensal_fixa = db.Column(db.Float, nullable=True, default=0.0)

    itens = db.relationship('SimulacaoItem', backref='simulacao', cascade='all,delete-orphan')
    eventos = db.relationship('SimulacaoEvento', backref='simulacao', cascade='all,delete-orphan')

class SimulacaoItem(db.Model):
    __tablename__ = 'simulacao_itens'

    id = db.Column(db.Integer, primary_key=True)
    simulacao_id = db.Column(db.Integer, db.ForeignKey('simulacoes.id'), nullable=False)
    pacientes = db.Column(db.Integer, nullable=False)
    valor_sessao = db.Column(db.Float, nullable=False)

class SimulacaoEvento(db.Model):
    __tablename__ = 'simulacao_eventos'

    id = db.Column(db.Integer, primary_key=True)
    simulacao_id = db.Column(db.Integer, db.ForeignKey('simulacoes.id'), nullable=False)
    mes_offset = db.Column(db.Integer, nullable=False)
    delta = db.Column(db.Integer, nullable=False)
