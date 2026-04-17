"""
Modelos para notificações e alertas
"""

from datetime import datetime

from app.models.models import db


class Notificacao(db.Model):
    """Notificações do sistema"""

    __tablename__ = 'notificacoes'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    obra_id = db.Column(db.Integer, db.ForeignKey('obras.id'))
    lancamento_id = db.Column(db.Integer, db.ForeignKey('lancamentos.id'))
    tipo = db.Column(db.String(50), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    mensagem = db.Column(db.Text)
    lida = db.Column(db.Boolean, default=False)
    enviada_email = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    empresa = db.relationship('Empresa', backref='notificacoes')

    def to_dict(self):
        return {
            'id': self.id,
            'tipo': self.tipo,
            'titulo': self.titulo,
            'mensagem': self.mensagem,
            'lida': self.lida,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M'),
        }


class ConfigEmail(db.Model):
    """Configurações de email por empresa"""

    __tablename__ = 'config_email'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False, unique=True)
    smtp_host = db.Column(db.String(100))
    smtp_port = db.Column(db.Integer, default=587)
    smtp_user = db.Column(db.String(100))
    smtp_password = db.Column(db.String(256))
    smtp_usar_tls = db.Column(db.Boolean, default=True)
    email_destino = db.Column(db.String(200))
    alertas_ativos = db.Column(db.Boolean, default=True)
    ultimo_envio = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'smtp_host': self.smtp_host,
            'smtp_port': self.smtp_port,
            'email_destino': self.email_destino,
            'alertas_ativos': self.alertas_ativos,
        }
