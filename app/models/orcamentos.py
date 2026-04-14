"""
Modelos de orçamentos
"""
from app.models.models import db, SoftDeleteMixin
from datetime import datetime


class Orcamento(db.Model, SoftDeleteMixin):
    """Orçamentos para clientes"""
    __tablename__ = 'orcamentos'
    
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    cliente = db.Column(db.String(200), nullable=False)
    cliente_email = db.Column(db.String(120))
    cliente_telefone = db.Column(db.String(20))
    cliente_endereco = db.Column(db.String(300))
    
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    
    valor_materiais = db.Column(db.Float, default=0)
    valor_mao_obra = db.Column(db.Float, default=0)
    valor_equipamentos = db.Column(db.Float, default=0)
    valor_outros = db.Column(db.Float, default=0)
    desconto = db.Column(db.Float, default=0)
    
    prazo_execucao = db.Column(db.Integer)
    validade = db.Column(db.Integer, default=30)
    
    status = db.Column(db.String(50), default='Rascunho')
    forma_pagamento = db.Column(db.String(200))
    
    enviado = db.Column(db.Boolean, default=False)
    data_envio = db.Column(db.Date)
    visualizado = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    empresa = db.relationship('Empresa', backref='orcamentos')
    
    @property
    def valor_total(self):
        subtotal = self.valor_materiais + self.valor_mao_obra + self.valor_equipamentos + self.valor_outros
        return subtotal - self.desconto
    
    @property
    def valor_total_display(self):
        return self.valor_total
    
    def to_dict(self):
        return {
            'id': self.id,
            'cliente': self.cliente,
            'titulo': self.titulo,
            'valor': self.valor_total,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None
        }


class ItemOrcamento(db.Model):
    """Itens do orçamento"""
    __tablename__ = 'itens_orcamento'
    
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamentos.id'), nullable=False)
    categoria = db.Column(db.String(100))
    descricao = db.Column(db.String(200), nullable=False)
    unidade = db.Column(db.String(20), default='un')
    quantidade = db.Column(db.Float, default=1)
    valor_unitario = db.Column(db.Float, default=0)
    
    orcamento = db.relationship('Orcamento', backref='itens')
    
    @property
    def valor_total(self):
        return self.quantidade * self.valor_unitario
    
    def to_dict(self):
        return {
            'id': self.id,
            'descricao': self.descricao,
            'unidade': self.unidade,
            'quantidade': self.quantidade,
            'valor_unitario': self.valor_unitario,
            'valor_total': self.valor_total
        }