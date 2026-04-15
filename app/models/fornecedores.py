"""
Modelos de fornecedores
"""

from datetime import datetime

from app.models.models import SoftDeleteMixin, db


class Fornecedor(db.Model, SoftDeleteMixin):
    """Fornecedores"""

    __tablename__ = 'fornecedores'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    razao_social = db.Column(db.String(200))
    cnpj = db.Column(db.String(20))
    cpf = db.Column(db.String(14))
    email = db.Column(db.String(120))
    telefone = db.Column(db.String(20))
    telefone_2 = db.Column(db.String(20))
    endereco = db.Column(db.String(300))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    cep = db.Column(db.String(10))
    contato = db.Column(db.String(100))
    categoria = db.Column(db.String(100))
    observacoes = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    empresa = db.relationship('Empresa', backref='fornecedores')

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'cnpj': self.cnpj,
            'email': self.email,
            'telefone': self.telefone,
            'categoria': self.categoria,
            'ativo': self.ativo,
        }


class CompraFornecedor(db.Model):
    """Compras de fornecedores"""

    __tablename__ = 'compras_fornecedor'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'), nullable=False)
    obra_id = db.Column(db.Integer, db.ForeignKey('obras.id'))
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, default=0)
    data = db.Column(db.Date)
    status = db.Column(db.String(50), default='Pendente')
    observacoes = db.Column(db.Text)

    fornecedor = db.relationship('Fornecedor', backref='compras')
    obra = db.relationship('Obra', backref='compras_fornecedor')

    def to_dict(self):
        return {
            'id': self.id,
            'descricao': self.descricao,
            'valor': self.valor,
            'data': self.data.strftime('%Y-%m-%d') if self.data else None,
            'status': self.status,
        }
