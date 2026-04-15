"""Notification service - Email and in-app notifications"""

import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional

from flask import current_app

from app.models import db
from app.models.notificacoes import ConfigEmail, Notificacao
from app.services.base_service import BaseService


class NotificationService(BaseService):
    """Service for sending emails and managing notifications"""

    @staticmethod
    def enviar_email(
        destinatario: str,
        assunto: str,
        mensagem: str,
        empresa_id: int | None = None,
        html: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Send email using SMTP or company config

        Args:
            destinatario: Email recipient
            assunto: Email subject
            mensagem: Email body (plain text)
            empresa_id: Optional company ID for custom config
            html: Optional HTML body

        Returns:
            Tuple (success, error_message)
        """
        try:
            # Get email config
            if empresa_id:
                config = ConfigEmail.query.filter_by(empresa_id=empresa_id).first()
            else:
                config = None

            # Use company config or default from environment
            mail_server = config.smtp_server if config else current_app.config.get('MAIL_SERVER')
            mail_port = config.smtp_port if config else current_app.config.get('MAIL_PORT', 587)
            mail_username = config.smtp_user if config else current_app.config.get('MAIL_USERNAME')
            mail_password = (
                config.smtp_password if config else current_app.config.get('MAIL_PASSWORD')
            )
            mail_use_tls = config.smtp_tls if config else True

            if not mail_server or not mail_username:
                return False, 'Configuração de email não encontrada'

            # Create message
            msg = MIMEText(mensagem, 'plain' if not html else 'html')
            msg['Subject'] = assunto
            msg['From'] = mail_username
            msg['To'] = destinatario

            # Send email
            if mail_use_tls:
                server = smtplib.SMTP(mail_server, mail_port)
                server.starttls()
            else:
                server = smtplib.SMTP(mail_server, mail_port)

            server.login(mail_username, mail_password)
            server.sendmail(mail_username, [destinatario], msg.as_string())
            server.quit()

            return True, None

        except smtplib.SMTPException as e:
            current_app.logger.error(f'Erro ao enviar email: {e}')
            return False, f'Erro SMTP: {e!s}'
        except Exception as e:
            current_app.logger.error(f'Erro ao enviar email: {e}')
            return False, f'Erro ao enviar email: {e!s}'

    @staticmethod
    def criar_notificacao(
        usuario_id: int,
        empresa_id: int,
        tipo: str,
        titulo: str,
        mensagem: str,
        link: str | None = None,
    ) -> Notificacao:
        """
        Create in-app notification

        Args:
            usuario_id: User ID
            empresa_id: Company ID
            tipo: Notification type (alerta, info, sucesso, erro)
            titulo: Notification title
            mensagem: Notification message
            link: Optional link for action

        Returns:
            Notificacao instance
        """
        notificacao = Notificacao(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            link=link,
            lida=False,
        )
        db.session.add(notificacao)
        db.session.commit()

        return notificacao

    @staticmethod
    def get_notificacoes_nao_lidas(usuario_id: int, empresa_id: int) -> list[Notificacao]:
        """Get unread notifications for user"""
        return (
            Notificacao.query.filter_by(
                usuario_id=usuario_id,
                empresa_id=empresa_id,
                lida=False,
            )
            .order_by(Notificacao.created_at.desc())
            .all()
        )

    @staticmethod
    def marcar_como_lida(notificacao_id: int, usuario_id: int) -> bool:
        """Mark notification as read. Returns success"""
        notificacao = Notificacao.query.filter_by(
            id=notificacao_id,
            usuario_id=usuario_id,
        ).first()

        if not notificacao:
            return False

        notificacao.lida = True
        db.session.commit()
        return True

    @staticmethod
    def marcar_todas_como_lidas(usuario_id: int, empresa_id: int) -> int:
        """Mark all notifications as read. Returns count"""
        count = Notificacao.query.filter_by(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            lida=False,
        ).update({'lida': True})
        db.session.commit()
        return count

    @staticmethod
    def notificar_alerta_orcamento(
        usuario_id: int,
        empresa_id: int,
        obra_nome: str,
        percentual_usado: float,
    ):
        """Notify about budget alert"""
        if percentual_usado >= 90:
            tipo = 'erro'
            titulo = 'Orçamento Crítico'
            mensagem = f'A obra "{obra_nome}" utilizou {percentual_usado:.1f}% do orçamento!'
        elif percentual_usado >= 70:
            tipo = 'alerta'
            titulo = 'Alerta de Orçamento'
            mensagem = f'A obra "{obra_nome}" já utilizou {percentual_usado:.1f}% do orçamento.'
        else:
            return

        NotificationService.criar_notificacao(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            link=f'/obra?filter={obra_nome}',
        )

    @staticmethod
    def notificar_obra_atrasada(
        usuario_id: int,
        empresa_id: int,
        obra_nome: str,
        dias_atraso: int,
    ):
        """Notify about delayed project"""
        NotificationService.criar_notificacao(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            tipo='alerta',
            titulo='Obra Atrasada',
            mensagem=f'A obra "{obra_nome}" está atrasada há {dias_atraso} dias!',
            link=f'/obra?filter={obra_nome}',
        )

    @staticmethod
    def notificar_pagamento_pendente(
        usuario_id: int,
        empresa_id: int,
        contrato_titulo: str,
        parcela_numero: int,
        valor: float,
        vencimento: str,
    ):
        """Notify about pending payment"""
        NotificationService.criar_notificacao(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            tipo='info',
            titulo='Pagamento Pendente',
            mensagem=f'Parcela {parcela_numero} do contrato "{contrato_titulo}" no valor de R$ {valor:.2f} vence em {vencimento}.',
            link='/contratos',
        )

    @staticmethod
    def enviar_relatorio_mensal(
        destinatario: str,
        empresa_id: int,
        mes: int,
        ano: int,
        dados_relatorio: dict,
    ) -> tuple[bool, str | None]:
        """Send monthly financial report via email"""
        assunto = f'Relatório Mensal - {mes:02d}/{ano}'

        # Build HTML report
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Relatório Mensal - {mes:02d}/{ano}</h2>

            <h3>Resumo Financeiro</h3>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr>
                    <td><strong>Receitas</strong></td>
                    <td>R$ {dados_relatorio.get('receitas', 0):.2f}</td>
                </tr>
                <tr>
                    <td><strong>Despesas</strong></td>
                    <td>R$ {dados_relatorio.get('despesas', 0):.2f}</td>
                </tr>
                <tr>
                    <td><strong>Saldo</strong></td>
                    <td>R$ {dados_relatorio.get('saldo', 0):.2f}</td>
                </tr>
            </table>

            <h3>Obras Ativas</h3>
            <p>{dados_relatorio.get('obras_ativas', 0)} obras em execução</p>

            <p style="margin-top: 20px; color: #666;">
                Este é um relatório automático do sistema OBRAS PRO.
            </p>
        </body>
        </html>
        """

        mensagem = f"""
        Relatório Mensal - {mes:02d}/{ano}

        Receitas: R$ {dados_relatorio.get('receitas', 0):.2f}
        Despesas: R$ {dados_relatorio.get('despesas', 0):.2f}
        Saldo: R$ {dados_relatorio.get('saldo', 0):.2f}

        Obras Ativas: {dados_relatorio.get('obras_ativas', 0)}

        --
        Sistema OBRAS PRO
        """

        return NotificationService.enviar_email(
            destinatario=destinatario,
            assunto=assunto,
            mensagem=mensagem,
            empresa_id=empresa_id,
            html=html,
        )
