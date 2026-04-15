"""Audit service - Centralized activity logging"""

from flask import request, session

from app.models import LogAtividade, db


class AuditService:
    """Service for logging activity and audit trails"""

    @staticmethod
    def log(acao, entidade=None, entidade_id=None, detalhes=None):
        """Registra atividade no log de auditoria"""
        try:
            empresa_id = session.get('empresa_id')
            log = LogAtividade(
                usuario_id=session.get('usuario_id'),
                empresa_id=empresa_id,
                acao=acao,
                entidade=entidade,
                entidade_id=entidade_id,
                detalhes=detalhes,
                ip=request.remote_addr if request else None,
            )
            db.session.add(log)
            db.session.commit()

            # Invalida cache ao alterar dados
            try:
                from flask_caching import cache

                cache.delete('dashboard_data')
            except Exception:
                pass
        except Exception:
            pass
