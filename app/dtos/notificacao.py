"""DTOs para Notificacao (Notification)"""

from dataclasses import dataclass

from app.dtos.base import BaseDTO


@dataclass
class NotificacaoCreateDTO(BaseDTO):
    """DTO for creating a new notification"""

    tipo: str
    titulo: str
    mensagem: str | None = None
    obra_id: int | None = None
    lancamento_id: int | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.tipo or not self.tipo.strip():
            return 'Tipo é obrigatório.'
        if not self.titulo or not self.titulo.strip():
            return 'Título é obrigatório.'
        return None


@dataclass
class NotificacaoResponseDTO(BaseDTO):
    """DTO for notification response data"""

    id: int
    empresa_id: int
    tipo: str
    titulo: str
    usuario_id: int | None = None
    obra_id: int | None = None
    lancamento_id: int | None = None
    mensagem: str | None = None
    lida: bool = False
    enviada_email: bool = False
    created_at: str | None = None

    @classmethod
    def from_model(cls, notificacao) -> 'NotificacaoResponseDTO':
        """Create DTO from Notificacao model instance"""
        notif_dict = notificacao.to_dict()
        return cls(
            id=notificacao.id,
            empresa_id=notificacao.empresa_id,
            usuario_id=notif_dict.get('usuario_id'),
            obra_id=notificacao.obra_id,
            lancamento_id=notificacao.lancamento_id,
            tipo=notificacao.tipo,
            titulo=notificacao.titulo,
            mensagem=notificacao.mensagem,
            lida=notificacao.lida if notificacao.lida is not None else False,
            enviada_email=notificacao.enviada_email
            if notificacao.enviada_email is not None
            else False,
            created_at=notif_dict.get('created_at'),
        )


@dataclass
class NotificacaoFiltrosDTO(BaseDTO):
    """DTO for notification search/filter parameters"""

    lida: bool | None = None
    tipo: str | None = None
    obra_id: int | None = None
    page: int = 1
    per_page: int = 20


@dataclass
class NotificacaoResumoDTO(BaseDTO):
    """DTO for notification summary (counts)"""

    total: int = 0
    nao_lidas: int = 0
    lidas: int = 0


@dataclass
class EmailConfigDTO(BaseDTO):
    """DTO for email configuration"""

    empresa_id: int
    id: int | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_usar_tls: bool = True
    email_destino: str | None = None
    alertas_ativos: bool = True

    @classmethod
    def from_model(cls, config) -> 'EmailConfigDTO':
        """Create DTO from ConfigEmail model instance"""
        config.to_dict()
        return cls(
            id=config.id,
            empresa_id=config.empresa_id,
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port or 587,
            smtp_user=config.smtp_user,
            smtp_usar_tls=config.smtp_usar_tls if config.smtp_usar_tls is not None else True,
            email_destino=config.email_destino,
            alertas_ativos=config.alertas_ativos if config.alertas_ativos is not None else True,
        )

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if self.smtp_port and (self.smtp_port < 1 or self.smtp_port > 65535):
            return 'Porta SMTP inválida.'
        return None


@dataclass
class EmailEnvioDTO(BaseDTO):
    """DTO for sending email"""

    destinatario: str
    assunto: str
    mensagem: str
    html: str | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.destinatario or not self.destinatario.strip():
            return 'Destinatário é obrigatório.'
        if not self.assunto or not self.assunto.strip():
            return 'Assunto é obrigatório.'
        if not self.mensagem or not self.mensagem.strip():
            return 'Mensagem é obrigatória.'
        return None
