"""
Modelos de contas bancárias
"""

from datetime import datetime

from app.models.models import SoftDeleteMixin, db


class ContaBancaria(db.Model, SoftDeleteMixin):
    """Contas bancárias do sistema"""

    __tablename__ = 'contas_bancarias'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    banco = db.Column(db.String(100))
    agencia = db.Column(db.String(20))
    conta = db.Column(db.String(30))
    tipo = db.Column(db.String(20))
    saldo_inicial = db.Column(db.Float, default=0)
    saldo_atual = db.Column(db.Float, default=0)
    ativo = db.Column(db.Boolean, default=True)
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lancamentos = db.relationship(
        'LancamentoConta', backref='conta', lazy='dynamic', cascade='all, delete-orphan'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'empresa_id': self.empresa_id,
            'nome': self.nome,
            'banco': self.banco,
            'agencia': self.agencia,
            'conta': self.conta,
            'tipo': self.tipo,
            'saldo_atual': self.saldo_atual,
            'ativo': self.ativo,
        }


class LancamentoConta(db.Model):
    """Lançamentos em contas bancárias"""

    __tablename__ = 'lancamentos_conta'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    conta_id = db.Column(db.Integer, db.ForeignKey('contas_bancarias.id'), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    documento = db.Column(db.String(100))
    categoria = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'empresa_id': self.empresa_id,
            'conta_id': self.conta_id,
            'conta_nome': self.conta.nome if self.conta else '',
            'descricao': self.descricao,
            'tipo': self.tipo,
            'valor': self.valor,
            'data': self.data.strftime('%Y-%m-%d') if self.data else None,
            'documento': self.documento,
            'categoria': self.categoria,
        }
