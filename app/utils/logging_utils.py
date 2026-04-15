"""
Logging estruturado para o sistema OBRAS PRO
"""

import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

from flask import request, session


class StructuredFormatter(logging.Formatter):
    """Formatter que gera logs estruturados em JSON"""

    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Adicionar contexto da request se disponível
        try:
            if hasattr(request, 'endpoint') and request.endpoint:
                log_data['request'] = {
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                }

            # Adicionar usuário se logado
            if session.get('usuario_id'):
                log_data['user'] = {
                    'id': session.get('usuario_id'),
                    'empresa_id': session.get('empresa_id'),
                }
        except RuntimeError:
            pass

        # Adicionar extras
        if hasattr(record, 'extra'):
            log_data.update(record.extra)

        # Adicionar exceção se presente
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(app):
    """Configura logging estruturado para a aplicação"""

    # Criar diretório de logs se não existir
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Configurar logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Handler para arquivo (rotativo)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'obras_pro.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(StructuredFormatter())

    # Handler para console (desenvolvimento)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )

    # Adicionar handlers
    root_logger.addHandler(file_handler)

    # Logger específico para erros
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'obras_pro_errors.log'),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(error_handler)

    # Em desenvolvimento, adicionar console
    if app.config.get('DEBUG'):
        root_logger.addHandler(console_handler)

    return root_logger


def log_acao(acao, entidade=None, entidade_id=None, detalhes=None, nivel='info'):
    """
    Log estruturado de ações do usuário

    Args:
        acao: Nome da ação (criar, editar, excluir, etc)
        entidade: Tipo da entidade (Obra, Lancamento, etc)
        entidade_id: ID da entidade
        detalhes: Dicionário com detalhes adicionais
        nivel: nivel do log (debug, info, warning, error)
    """
    logger = logging.getLogger('obras_pro.acao')

    log_data = {
        'acao': acao,
        'entidade': entidade,
        'entidade_id': entidade_id,
        'detalhes': detalhes or {},
    }

    getattr(logger, nivel)(json.dumps(log_data))


def log_acesso(recurso, status, detalhes=None):
    """Log de acesso a recursos"""
    logger = logging.getLogger('obras_pro.acesso')

    log_data = {'recurso': recurso, 'status': status, 'detalhes': detalhes or {}}

    logger.info(json.dumps(log_data))


def log_erro(erro, contexto=None):
    """Log de erros com contexto"""
    logger = logging.getLogger('obras_pro.erro')

    log_data = {'erro': str(erro), 'tipo': type(erro).__name__, 'contexto': contexto or {}}

    logger.error(json.dumps(log_data))


def log_performance(inicio, fim, operacao, detalhes=None):
    """Log de performance de operações"""
    logger = logging.getLogger('obras_pro.performance')
    duracao = (fim - inicio).total_seconds()

    log_data = {
        'operacao': operacao,
        'duracao_ms': round(duracao * 1000, 2),
        'detalhes': detalhes or {},
    }

    if duracao > 1.0:  # Log only if > 1 second
        logger.warning(json.dumps(log_data))
    else:
        logger.info(json.dumps(log_data))


def log_seguranca(evento, detalhes=None):
    """Log de eventos de segurança"""
    logger = logging.getLogger('obras_pro.seguranca')

    log_data = {'evento': evento, 'detalhes': detalhes or {}}

    logger.warning(json.dumps(log_data))
