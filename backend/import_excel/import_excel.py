# backend/import_excel.py

import pandas as pd
from datetime import datetime
from models import db, Paciente, Nota

def importar_excel(caminho_arquivo: str):
    """
    Lê um arquivo Excel de extrato com colunas:
    - CPF
    - Nome
    - Data       (formato YYYY-MM-DD ou detectável pelo pandas)
    - Valor      (float)
    - Tipo       ('Receita' ou 'Despesa')
    - Descrição  (texto)
    
    Insere/atualiza Paciente e Nota no banco SQLite.
    """
    df = pd.read_excel(caminho_arquivo, engine='openpyxl')
    for _, row in df.iterrows():
        cpf    = str(row.get('CPF')).strip()
        nome   = str(row.get('Nome')).strip()
        data   = pd.to_datetime(row.get('Data')).date()
        valor  = float(row.get('Valor', 0))
        tipo   = str(row.get('Tipo')).strip().lower()
        descricao = str(row.get('Descrição', ''))

        # Busca ou cria paciente
        paciente = Paciente.query.filter_by(cpf=cpf).first()
        if not paciente:
            paciente = Paciente(nome=nome, cpf=cpf)
            db.session.add(paciente)
            db.session.commit()

        # Cria a nota
        nota = Nota(
            paciente_id = paciente.id,
            data        = data,
            valor       = valor,
            receita     = (tipo == 'receita'),
            despesa     = (tipo == 'despesa'),
            descricao   = descricao
        )
        db.session.add(nota)

    db.session.commit()
