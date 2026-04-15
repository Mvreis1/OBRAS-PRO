"""
Modelos de contratos
"""

from datetime import datetime

from app.models.models import SoftDeleteMixin, db


class Contrato(db.Model, SoftDeleteMixin):
    """Contratos com clientes"""

    __tablename__ = 'contratos'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    obra_id = db.Column(db.Integer, db.ForeignKey('obras.id'))
    cliente = db.Column(db.String(200), nullable=False)
    cliente_cnpj = db.Column(db.String(20))
    cliente_email = db.Column(db.String(120))
    cliente_telefone = db.Column(db.String(20))
    cliente_endereco = db.Column(db.String(300))

    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    valor = db.Column(db.Float, default=0)
    valor_aditivo = db.Column(db.Float, default=0)

    data_inicio = db.Column(db.Date)
    data_fim = db.Column(db.Date)
    data_assinatura = db.Column(db.Date)

    status = db.Column(db.String(50), default='Rascunho')
    tipo = db.Column(db.String(50), default='Prestação de Serviços')

    observacoes = db.Column(db.Text)
    arquivo = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    obra = db.relationship('Obra', backref='contratos')
    empresa = db.relationship('Empresa', backref='contratos')

    def to_dict(self):
        return {
            'id': self.id,
            'cliente': self.cliente,
            'titulo': self.titulo,
            'valor': self.valor,
            'valor_total': self.valor + self.valor_aditivo,
            'status': self.status,
            'data_inicio': self.data_inicio.strftime('%Y-%m-%d') if self.data_inicio else None,
            'data_fim': self.data_fim.strftime('%Y-%m-%d') if self.data_fim else None,
        }


class ParcelaContrato(db.Model):
    """Parcelas de contratos"""

    __tablename__ = 'parcelas_contrato'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contratos.id'), nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date)
    status = db.Column(db.String(20), default='Pendente')
    descricao = db.Column(db.String(200))

    # Constraint único para prevenir race condition em parcelas
    __table_args__ = (
        db.UniqueConstraint('contrato_id', 'numero', name='uq_parcela_contrato_numero'),
    )

    contrato = db.relationship('Contrato', backref='parcelas')

    def to_dict(self):
        return {
            'id': self.id,
            'numero': self.numero,
            'valor': self.valor,
            'data_vencimento': self.data_vencimento.strftime('%Y-%m-%d')
            if self.data_vencimento
            else None,
            'data_pagamento': self.data_pagamento.strftime('%Y-%m-%d')
            if self.data_pagamento
            else None,
            'status': self.status,
        }
