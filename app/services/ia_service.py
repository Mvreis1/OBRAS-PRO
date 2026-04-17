"""IA Service - AI model orchestration and chat management"""

from typing import Optional

from app.config import CLAUDE_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY
from app.models import ConfigIA
from app.utils.ia import gerar_resposta, get_contexto_empresa


class IAService:
    """Service for managing AI models and chat interactions"""

    # Supported AI models
    OPENAI_MODELS = ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini']
    DEFAULT_MODEL = 'local'

    @staticmethod
    def chat(
        empresa_id: int, mensagem: str, modelo: str = DEFAULT_MODEL, max_length: int = 500
    ) -> str:
        """
        Process chat message with selected AI model.
        """
        if not mensagem:
            return "Por favor, digite uma mensagem."

        # Validate message length
        if len(mensagem) > max_length:
            return f'Mensagem muito longa. Limite: {max_length} caracteres.'

        # Get context and config
        contexto = get_contexto_empresa(empresa_id)
        config = ConfigIA.query.filter_by(empresa_id=empresa_id).first()

        # Route to appropriate model
        try:
            if modelo in IAService.OPENAI_MODELS:
                return IAService._call_openai(mensagem, contexto, modelo, config)
            elif modelo == 'gemini':
                return IAService._call_gemini(mensagem, contexto, config)
            elif modelo == 'claude':
                return IAService._call_claude(mensagem, contexto, config)
            else:
                # Use local AI
                return gerar_resposta(mensagem, contexto)
        except Exception as e:
            print(f"ERRO IA CRITICO: {e!s}")
            return f"Ocorreu um erro interno ao processar sua solicitação: {e!s}. Usando assistente local.\n\n" + gerar_resposta(mensagem, contexto)

    @staticmethod
    def _call_openai(mensagem: str, contexto: dict, modelo: str, config) -> str:
        """Call OpenAI API"""
        # Get API key (Empresa key has precedence over Global key)
        api_key = config.get_openai_key() if config else None
        if not api_key:
            api_key = OPENAI_API_KEY

        if not api_key:
            return (
                '⚠️ API Key da OpenAI não configurada. Configure no arquivo .env ou em Configurações > IA.\n\n'
                + gerar_resposta(mensagem, contexto)
            )

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            system_prompt = IAService._build_system_prompt(contexto)

            response = client.chat.completions.create(
                model=modelo,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': mensagem},
                ],
                max_tokens=500,
                temperature=0.7,
            )

            return response.choices[0].message.content

        except Exception as e:
            error_msg = str(e)
            if "insufficient_quota" in error_msg:
                return "❌ Erro na OpenAI: Saldo insuficiente ou cota atingida. Verifique sua conta na OpenAI."
            if "invalid_api_key" in error_msg:
                return "❌ Erro na OpenAI: API Key inválida."
            return f'Erro ao conectar com {modelo}: {error_msg}\n\nUsando o assistente local.'

    @staticmethod
    def _call_gemini(mensagem: str, contexto: dict, config) -> str:
        """Call Google Gemini API"""
        api_key = config.get_gemini_key() if config else None
        if not api_key:
            api_key = GEMINI_API_KEY

        if not api_key:
            return (
                '⚠️ API Key do Gemini não configurada.\n\n'
                + gerar_resposta(mensagem, contexto)
            )

        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            system_prompt = IAService._build_system_prompt(contexto)

            response = model.generate_content(f'{system_prompt}\n\nPergunta: {mensagem}')
            return response.text

        except Exception as e:
            return f'Erro no Gemini: {e!s}. Usando assistente local.'

    @staticmethod
    def _call_claude(mensagem: str, contexto: dict, config) -> str:
        """Call Anthropic Claude API"""
        api_key = config.get_claude_key() if config else None
        if not api_key:
            api_key = CLAUDE_API_KEY

        if not api_key:
            return (
                '⚠️ API Key do Claude não configurada.\n\n'
                + gerar_resposta(mensagem, contexto)
            )

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            system_prompt = IAService._build_system_prompt(contexto)

            message = client.messages.create(
                model='claude-3-haiku-20240307',
                max_tokens=500,
                system=system_prompt,
                messages=[{'role': 'user', 'content': mensagem}],
            )
            return message.content[0].text

        except Exception as e:
            return f'Erro no Claude: {e!s}. Usando assistente local.'

    @staticmethod
    def _build_system_prompt(contexto: dict) -> str:
        """Build system prompt with company context"""
        return f"""
Você é um assistente de gestão de obras para uma construtora.
Sistema: OBRAS PRO - Gestão Financeira Profissional

Dados atuais do sistema:
- Total de obras: {contexto['total_obras']}
- Total de receitas: R$ {contexto['total_receitas']:,.2f}
- Total de despesas: R$ {contexto['total_despesas']:,.2f}
- Saldo atual: R$ {contexto['saldo_atual']:,.2f}
- Obra com maior gasto: {contexto['obra_maior_gasto'].nome if contexto['obra_maior_gasto'] else 'N/A'}

Responda em português brasileiro de forma clara e profissional.
""".strip()

    @staticmethod
    def get_quick_buttons() -> list:
        """Get quick action buttons for IA chat"""
        return [
            {'texto': 'Relatório de custos', 'acao': 'custo'},
            {'texto': 'Alertas de risco', 'acao': 'risco'},
            {'texto': 'Ver todas as obras', 'acao': 'obra'},
            {'texto': 'Saldo geral', 'acao': 'saldo'},
            {'texto': 'Por que negativo?', 'acao': 'negativo'},
            {'texto': 'Exportar relatório', 'acao': 'exportar'},
        ]

    @staticmethod
    def validate_api_key(model: str, api_key: str) -> tuple[bool, str]:
        """
        Validate AI model API key.

        Args:
            model: Model name (openai, gemini, claude)
            api_key: API key to validate

        Returns:
            Tuple (is_valid, error_message)
        """
        if not api_key or not api_key.strip():
            return False, 'API key não pode ser vazia'

        try:
            if model == 'openai':
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
                # Test with minimal request
                client.models.list()
                return True, ''

            elif model == 'gemini':
                import google.generativeai as genai

                genai.configure(api_key=api_key)
                model_obj = genai.GenerativeModel('gemini-pro')
                model_obj.generate_content('test')
                return True, ''

            elif model == 'claude':
                import anthropic

                client = anthropic.Anthropic(api_key=api_key)
                client.messages.create(
                    model='claude-3-haiku-20240307',
                    max_tokens=10,
                    messages=[{'role': 'user', 'content': 'test'}],
                )
                return True, ''

            else:
                return False, f'Modelo {model} não suportado'

        except Exception as e:
            return False, f'API key inválida: {e!s}'

    @staticmethod
    def get_model_status(empresa_id: int) -> dict:
        """
        Get status of all AI models for a company.

        Returns:
            Dict with model availability status
        """
        config = ConfigIA.query.filter_by(empresa_id=empresa_id).first()

        return {
            'openai': {
                'configured': bool(config.get_openai_key() if config else OPENAI_API_KEY),
                'models': IAService.OPENAI_MODELS,
            },
            'gemini': {
                'configured': bool(config.get_gemini_key() if config else False),
            },
            'claude': {
                'configured': bool(config.get_claude_key() if config else False),
            },
            'local': {
                'configured': True,
            },
        }
