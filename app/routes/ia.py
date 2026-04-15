"""
Rotas do Assistente IA
"""

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app.config import OPENAI_API_KEY
from app.models import ConfigIA
from app.routes.auth import login_required
from app.utils.ia import gerar_resposta, get_contexto_empresa

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
    mensagem = data.get('mensagem', '').lower()
    modelo = data.get('modelo', 'local')
    empresa_id = session.get('empresa_id')

    # Limitar tamanho da mensagem (prevenir abuse)
    if len(mensagem) > 500:
        return jsonify({'resposta': 'Mensagem muito longa. Limite: 500 caracteres.'}), 400

    # Usar helper otimizado para contexto (evita N+1)
    contexto = get_contexto_empresa(empresa_id)

    # Obter configurações da empresa
    config = get_config_ia(empresa_id)

    # Modelos suportados
    modelos_openai = ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini']

    # Verificar se há configuração para o modelo selecionado
    if modelo in modelos_openai:
        api_key = config.get_openai_key() if config else None
        if api_key:
            resposta = chamar_openai(mensagem, contexto, modelo, api_key)
        elif OPENAI_API_KEY:
            resposta = chamar_openai(mensagem, contexto, modelo, OPENAI_API_KEY)
        else:
            resposta = (
                '⚠️ API Key da OpenAI não configurada. Vá em Configurações > IA para cadastrar.\n\n'
                + gerar_resposta(mensagem, contexto)
            )
    elif modelo == 'gemini':
        api_key = config.get_gemini_key() if config else None
        if api_key:
            resposta = chamar_gemini(mensagem, contexto, api_key)
        else:
            resposta = (
                '⚠️ API Key do Gemini não configurada. Vá em Configurações > IA para cadastrar.\n\n'
                + gerar_resposta(mensagem, contexto)
            )
    elif modelo == 'claude':
        api_key = config.get_claude_key() if config else None
        if api_key:
            resposta = chamar_claude(mensagem, contexto, api_key)
        else:
            resposta = (
                '⚠️ API Key do Claude não configurada. Vá em Configurações > IA para cadastrar.\n\n'
                + gerar_resposta(mensagem, contexto)
            )
    else:
        resposta = gerar_resposta(mensagem, contexto)

    return jsonify({'resposta': resposta})


def chamar_openai(mensagem, contexto, modelo, api_key):
    """Chama a API da OpenAI (ChatGPT)"""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        info_sistema = f"""
Você é um assistente de gestão de obras para uma construtora.
Sistema: OBRAS PRO - Gestão Financeira Profissional

Dados atuais do sistema:
- Total de obras: {contexto['total_obras']}
- Total de receitas: R$ {contexto['total_receitas']:,.2f}
- Total de despesas: R$ {contexto['total_despesas']:,.2f}
- Saldo atual: R$ {contexto['saldo_atual']:,.2f}
- Obra com maior gasto: {contexto['obra_maior_gasto'].nome if contexto['obra_maior_gasto'] else 'N/A'}

Responda em português brasileiro de forma clara e profissional.
"""

        response = client.chat.completions.create(
            model=modelo,
            messages=[
                {'role': 'system', 'content': info_sistema},
                {'role': 'user', 'content': mensagem},
            ],
            max_tokens=500,
            temperature=0.7,
        )

        return response.choices[0].message.content

    except Exception as e:
        return f'Erro ao conectar com {modelo}: {e!s}\n\nUsando o assistente local.'


def chamar_gemini(mensagem, contexto, api_key):
    """Chama a API do Google Gemini"""
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')

        info_sistema = f"""Você é um assistente de gestão de obras.
Sistema: OBRAS PRO

Dados atuais:
- Obras: {contexto['total_obras']}
- Receitas: R$ {contexto['total_receitas']:,.2f}
- Despesas: R$ {contexto['total_despesas']:,.2f}
- Saldo: R$ {contexto['saldo_atual']:,.2f}

Responda em português de forma clara e profissional."""

        response = model.generate_content(f'{info_sistema}\n\nPergunta: {mensagem}')
        return response.text
    except Exception as e:
        return f'Erro no Gemini: {e!s}. Usando assistente local.'


def chamar_claude(mensagem, contexto, api_key):
    """Chama a API do Anthropic Claude"""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        info_sistema = f"""Você é um assistente de gestão de obras.
Sistema: OBRAS PRO

Dados atuais:
- Obras: {contexto['total_obras']}
- Receitas: R$ {contexto['total_receitas']:,.2f}
- Despesas: R$ {contexto['total_despesas']:,.2f}
- Saldo: R$ {contexto['saldo_atual']:,.2f}

Responda em português de forma clara e profissional."""

        message = client.messages.create(
            model='claude-3-haiku-20240307',
            max_tokens=500,
            system=info_sistema,
            messages=[{'role': 'user', 'content': mensagem}],
        )
        return message.content[0].text
    except Exception as e:
        return f'Erro no Claude: {e!s}. Usando assistente local.'


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
