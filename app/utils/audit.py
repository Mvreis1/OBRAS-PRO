"""
Sistema de Histórico de Alterações (Audit Trail)
"""
from datetime import datetime
from app.models import db


class AuditTrail:
    """Sistema de auditoria de alterações"""
    
    @staticmethod
    def registrar(usuario_id, empresa_id, acao, entidade, entidade_id, dados_old=None, dados_new=None):
        """
        Registra uma alteração no histórico
        
        Args:
            usuario_id: ID do usuário que fez a alteração
            empresa_id: ID da empresa
            acao: Ação (create, update, delete, view, export)
            entidade: Tipo da entidade (Obra, Lancamento, etc)
            entidade_id: ID da entidade
            dados_old: Dados antes da alteração (dict)
            dados_new: Dados depois da alteração (dict)
        """
        from app.models.models import LogAtividade
        
        # Gerar descrição da alteração
        detalhes = AuditTrail._gerar_detalhes(acao, dados_old, dados_new)
        
        log = LogAtividade(
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            acao=acao,
            entidade=entidade,
            entidade_id=entidade_id,
            detalhes=detalhes
        )
        
        db.session.add(log)
        return log
    
    @staticmethod
    def _gerar_detalhes(acao, dados_old, dados_new):
        """Gera string de detalhes baseada na ação"""
        if acao == 'create':
            return f"Criado: {dados_new}"
        elif acao == 'update':
            mudancas = []
            if dados_old and dados_new:
                for key in dados_new:
                    if key in dados_old and dados_old[key] != dados_new[key]:
                        mudancas.append(f"{key}: {dados_old[key]} → {dados_new[key]}")
            return ", ".join(mudancas) if mudancas else "Alterações realizadas"
        elif acao == 'delete':
            return f"Excluído: {dados_old}"
        elif acao == 'export':
            return f"Exportado: {dados_new.get('formato', 'desconhecido')}"
        else:
            return str(dados_new or '')
    
    @staticmethod
    def get_historico_entidade(entidade, entidade_id, limite=50):
        """Retorna histórico de uma entidade específica"""
        from app.models.models import LogAtividade
        
        logs = LogAtividade.query.filter_by(
            entidade=entidade,
            entidade_id=entidade_id
        ).order_by(LogAtividade.created_at.desc()).limit(limite).all()
        
        return [log.to_dict() for log in logs]
    
    @staticmethod
    def get_historico_empresa(empresa_id, entidade=None, usuario_id=None, data_inicio=None, data_fim=None, page=1, per_page=20):
        """Retorna histórico da empresa com filtros"""
        from app.models.models import LogAtividade
        from app.utils.paginacao import Paginacao
        
        query = LogAtividade.query.filter_by(empresa_id=empresa_id)
        
        if entidade:
            query = query.filter_by(entidade=entidade)
        if usuario_id:
            query = query.filter_by(usuario_id=usuario_id)
        if data_inicio:
            query = query.filter(LogAtividade.created_at >= data_inicio)
        if data_fim:
            query = query.filter(LogAtividade.created_at <= data_fim)
        
        return Paginacao(query.order_by(LogAtividade.created_at.desc()), page=page, per_page=per_page)


def audit_create(entidade_nome):
    """Decorator para auditar criação de entidades"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            
            # Pegar entidade retornada
            if hasattr(result, 'id'):
                from flask import session
                empresa_id = session.get('empresa_id')
                usuario_id = session.get('usuario_id')
                
                AuditTrail.registrar(
                    usuario_id=usuario_id,
                    empresa_id=empresa_id,
                    acao='create',
                    entidade=entidade_nome,
                    entidade_id=result.id,
                    dados_new=result.to_dict() if hasattr(result, 'to_dict') else {}
                )
            
            return result
        return wrapper
    return decorator


def audit_update(entidade_nome):
    """Decorator para auditar atualização de entidades"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            # Capturar dados antes
            from flask import session
            empresa_id = session.get('empresa_id')
            usuario_id = session.get('usuario_id')
            
            # Obter ID da entidade do args/kwargs
            entidade_id = args[1] if len(args) > 1 else kwargs.get('id')
            
            # Executar função
            result = f(*args, **kwargs)
            
            # Registrar atualização
            if result:
                AuditTrail.registrar(
                    usuario_id=usuario_id,
                    empresa_id=empresa_id,
                    acao='update',
                    entidade=entidade_nome,
                    entidade_id=entidade_id,
                    dados_old={},  # Você pode implementar captura de old
                    dados_new=result.to_dict() if hasattr(result, 'to_dict') else {}
                )
            
            return result
        return wrapper
    return decorator


def audit_delete(entidade_nome):
    """Decorator para auditar exclusão de entidades"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            from flask import session
            empresa_id = session.get('empresa_id')
            usuario_id = session.get('usuario_id')
            
            entidade_id = args[1] if len(args) > 1 else kwargs.get('id')
            
            result = f(*args, **kwargs)
            
            if result:
                AuditTrail.registrar(
                    usuario_id=usuario_id,
                    empresa_id=empresa_id,
                    acao='delete',
                    entidade=entidade_nome,
                    entidade_id=entidade_id,
                    dados_old={'id': entidade_id}
                )
            
            return result
        return wrapper
    return decorator