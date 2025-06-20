"""Adiciona modelo Transacao

Revision ID: a1f902856b97
Revises: 2f1f86d0d101
Create Date: 2025-05-30 14:48:55.230760

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1f902856b97'
down_revision = '2f1f86d0d101'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('transacoes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=120), nullable=False),
    sa.Column('tipo', sa.String(length=10), nullable=False),
    sa.Column('observacao', sa.Text(), nullable=True),
    sa.Column('valor', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('transacoes')
    # ### end Alembic commands ###
