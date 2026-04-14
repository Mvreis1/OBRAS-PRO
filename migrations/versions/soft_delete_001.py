"""Add deleted_at column for soft delete

Revision ID: soft_delete_001
Revises: 7acc0c0ff920
Create Date: 2026-04-14
"""
from alembic import op
import sqlalchemy as sa


revision = 'soft_delete_001'
down_revision = '7acc0c0ff920'
branch_labels = None
depends_on = None


def upgrade():
    tables = [
        'obras',
        'lancamentos',
        'fornecedores',
        'contratos',
        'orcamentos',
        'contas_bancarias'
    ]
    
    for table in tables:
        op.add_column(table, sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade():
    tables = [
        'obras',
        'lancamentos',
        'fornecedores',
        'contratos',
        'orcamentos',
        'contas_bancarias'
    ]
    
    for table in tables:
        op.drop_column(table, 'deleted_at')