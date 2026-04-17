"""Add performance indexes

Revision ID: performance_indexes_003
Revises: soft_delete_001
Create Date: 2026-04-17

Add indexes for:
- Lancamento: soft delete + empresa + data
- Lancamento: tipo + empresa (relatorios)
- Lancamento: categoria (despesas por categoria)
- Obra: status + empresa (obras por status)
- Index for deleted_at soft delete
"""

from alembic import op
import sqlalchemy as sa


revision = 'performance_indexes_003'
down_revision = 'soft_delete_001'
branch_labels = None
depends_on = None


def upgrade():
    # Lancamento indexes
    op.create_index(
        'idx_lancamento_soft_delete',
        'lancamentos',
        ['empresa_id', 'deleted_at', 'data'],
        unique=False,
    )

    op.create_index(
        'idx_lancamento_tipo_empresa', 'lancamentos', ['empresa_id', 'tipo'], unique=False
    )

    op.create_index('idx_lancamento_categoria', 'lancamentos', ['categoria'], unique=False)

    op.create_index('idx_lancamento_deleted_at', 'lancamentos', ['deleted_at'], unique=False)

    # Obra indexes
    op.create_index('idx_obra_status_empresa', 'obras', ['empresa_id', 'status'], unique=False)

    op.create_index('idx_obra_deleted_at', 'obras', ['deleted_at'], unique=False)

    # Fornecedor indexes
    op.create_index('idx_fornecedor_deleted_at', 'fornecedores', ['deleted_at'], unique=False)

    # Orcamento indexes
    op.create_index('idx_orcamento_deleted_at', 'orcamentos', ['deleted_at'], unique=False)


def downgrade():
    # Lancamento indexes
    op.drop_index('idx_lancamento_soft_delete', 'lancamentos')
    op.drop_index('idx_lancamento_tipo_empresa', 'lancamentos')
    op.drop_index('idx_lancamento_categoria', 'lancamentos')
    op.drop_index('idx_lancamento_deleted_at', 'lancamentos')

    # Obra indexes
    op.drop_index('idx_obra_status_empresa', 'obras')
    op.drop_index('idx_obra_deleted_at', 'obras')

    # Fornecedor indexes
    op.drop_index('idx_fornecedor_deleted_at', 'fornecedores')

    # Orcamento indexes
    op.drop_index('idx_orcamento_deleted_at', 'orcamentos')
