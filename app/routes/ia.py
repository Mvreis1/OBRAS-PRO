"""
Rotas do Assistente IA
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.routes.auth import login_required
from app.utils.ia import get_contexto_empresa, gerar_resposta

ia_bp = Blueprint('ia', __name__)


@ia_bp.route('/assistente-ia')
def assistente():
    """Página do assistente IA"""
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('main/assistente_ia.html')


@ia_bp.route('/api/ia/chat', methods=['POST'])
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
    
    # Cache simples em memória (para produção, usar Redis)
    cache_key = f"ia_response:{hash(mensagem[:50])}"
    # implementação simples - em produção usar Flask-Caching
    
    if modelo != 'local' and OPENAI_API_KEY:
        resposta = chamar_openai(mensagem, contexto, modelo)
    else:
        resposta = gerar_resposta(mensagem, contexto)
    
    return jsonify({'resposta': resposta})


def chamar_openai(mensagem, contexto, modelo):
    """Chama a API da OpenAI (ChatGPT)"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
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
                {"role": "system", "content": info_sistema},
                {"role": "user", "content": mensagem}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Erro ao conectar com {modelo}: {str(e)}\n\n使用 o assistente local enquanto configura a API."


@ia_bp.route('/api/ia/botoes', methods=['GET'])
@login_required
def ia_botoes():
    """API para botões rápidos do IA"""
    return jsonify([
        {'texto': 'Relatório de custos', 'acao': 'custo'},
        {'texto': 'Alertas de risco', 'acao': 'risco'},
        {'texto': 'Ver todas as obras', 'acao': 'obra'},
        {'texto': 'Saldo geral', 'acao': 'saldo'},
        {'texto': 'Por que negativo?', 'acao': 'negativo'},
        {'texto': 'Exportar relatório', 'acao': 'exportar'}
    ])