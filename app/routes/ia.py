"""
Rotas do Assistente IA
"""

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app.config import OPENAI_API_KEY
from app.models import ConfigIA
from app.routes.auth import login_required
from app.utils.ia import gerar_resposta, get_contexto_empresa

from app.services.ia_service import IAService

ia_bp = Blueprint('ia', __name__)


def get_config_ia(empresa_id):
    """Obtém configurações de IA da empresa"""
    return ConfigIA.query.filter_by(empresa_id=empresa_id).first()


@ia_bp.route('/assistente-ia')
def assistente():
    """Página do assistente IA"""
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('main/assistente_ia.html')


@ia_bp.route('/chat', methods=['POST'])
@login_required
def chat_ia():
    """API para interação com o assistente IA"""
    data = request.get_json()
    mensagem = data.get('mensagem', '')
    modelo = data.get('modelo', 'local')
    empresa_id = session.get('empresa_id')

    # Usar o serviço centralizado de IA
    resposta = IAService.chat(
        empresa_id=empresa_id,
        mensagem=mensagem,
        modelo=modelo
    )

    return jsonify({'resposta': resposta})


@ia_bp.route('/botoes', methods=['GET'])
@login_required
def ia_botoes():
    """API para botões rápidos do IA"""
    return jsonify(
        [
            {'texto': 'Relatório de custos', 'acao': 'custo'},
            {'texto': 'Alertas de risco', 'acao': 'risco'},
            {'texto': 'Ver todas as obras', 'acao': 'obra'},
            {'texto': 'Saldo geral', 'acao': 'saldo'},
            {'texto': 'Por que negativo?', 'acao': 'negativo'},
            {'texto': 'Exportar relatório', 'acao': 'exportar'},
        ]
    )
