"""
Helpers para o Assistente IA
"""

from sqlalchemy import func

from app.models import Lancamento, Obra, db

MAX_RESPONSE_LENGTH = 1000  # Limite de caracteres para respostas locais


def get_contexto_empresa(empresa_id):
    """Retorna contexto resumido da empresa para o IA"""

    # Total de obras
    total_obras = Obra.query.filter_by(empresa_id=empresa_id).count()

    # Totais agregados com uma única query
    totais = (
        db.session.query(
            func.sum(func.case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label(
                'receitas'
            ),
            func.sum(func.case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label(
                'despesas'
            ),
        )
        .filter(Lancamento.empresa_id == empresa_id)
        .first()
    )

    todas_despesas = totais.despesas or 0
    todas_receitas = totais.receitas or 0
    saldo_atual = todas_receitas - todas_despesas

    # Obra com maior gasto - query agregada
    obra_maior_gasto_data = (
        db.session.query(Obra.id, Obra.nome, func.sum(Lancamento.valor).label('total_gasto'))
        .join(Lancamento)
        .filter(Lancamento.empresa_id == empresa_id, Lancamento.tipo == 'Despesa')
        .group_by(Obra.id, Obra.nome)
        .order_by(func.sum(Lancamento.valor).desc())
        .first()
    )

    obra_maior_gasto = None
    if obra_maior_gasto_data:
        obra_maior_gasto = type(
            'obj',
            (object,),
            {
                'id': obra_maior_gasto_data[0],
                'nome': obra_maior_gasto_data[1],
                'total_gasto': obra_maior_gasto_data[2] or 0,
            },
        )()

    return {
        'total_obras': total_obras,
        'saldo_atual': saldo_atual,
        'total_despesas': todas_despesas,
        'total_receitas': todas_receitas,
        'obra_maior_gasto': obra_maior_gasto,
    }


class RespostaIA:
    """Classe para construir respostas do assistente IA"""

    CATEGORIAS = {
        'saudacao': ['oi', 'olá', 'ola', 'hello', 'hi'],
        'negativo': ['negativo', 'por que', 'porque', 'explica', 'causa', 'motivo'],
        'saldo': ['saldo', 'dinheiro', 'quanto', 'financeiro'],
        'obra': ['obra', 'projeto', 'obra alpha', 'residencial'],
        'custo': ['custo', 'gasto', 'despesa'],
        'relatorio': ['relatório', 'relatorio', 'report', 'exportar', 'pdf', 'excel'],
        'risco': ['risco', 'alerta', 'problema'],
        'previsao': ['previsão', 'previsao', 'conclusão', 'conclusao'],
        'obrigado': ['obrigado', 'thanks', 'vlw', 'obrigada'],
    }

    @staticmethod
    def detectar_categoria(mensagem):
        """Detecta a categoria da mensagem"""
        for categoria, palavras in RespostaIA.CATEGORIAS.items():
            if any(p in mensagem for p in palavras):
                return categoria
        return 'default'

    @staticmethod
    def gerar_saudacao():
        return (
            'Olá! Sou o assistente de gestão de obras. '
            'Posso ajudar com:\n'
            '• Informações financeiras das obras\n'
            '• Status e progresso das obras\n'
            '• Relatórios de custos\n'
            '• Previsões e alertas\n'
            '• Análise de saldo negativo\n'
            '• Exportar relatórios\n'
            'Como posso ajudar?'
        )

    @staticmethod
    def analisar_negativo(contexto, mensagem):
        """Analisa saldo negativo"""
        if contexto['saldo_atual'] < 0:
            analise = ['📉 ANÁLISE: Por que o saldo está negativo?\n']
            analise.append(f'• Receitas total: R$ {contexto["total_receitas"]:,.2f}')
            analise.append(f'• Despesas total: R$ {contexto["total_despesas"]:,.2f}')
            analise.append(f'• Diferença: R$ {contexto["saldo_atual"]:,.2f}\n')

            analise.append('💡 RECOMENDAÇÕES:')
            analise.append('   • Negocie pagamentos com fornecedores')
            analise.append('   • Acelere recebimento de clientes')
            analise.append('   • Revise custos desnecessários')
            return '\n'.join(analise)
        else:
            return (
                '✅ Seu saldo está POSITIVO! Não há motivo para preocupação.\n\n'
                f'Saldo atual: R$ {contexto["saldo_atual"]:,.2f}\n'
                f'Receitas: R$ {contexto["total_receitas"]:,.2f}\n'
                f'Despesas: R$ {contexto["total_despesas"]:,.2f}'
            )

    @staticmethod
    def gerar_saldo(contexto):
        """Retorna informações de saldo"""
        if contexto['saldo_atual'] >= 0:
            return (
                f'💰 Seu saldo atual é R$ {contexto["saldo_atual"]:,.2f}. '
                f'\n\nTotal de receitas: R$ {contexto["total_receitas"]:,.2f}\n'
                f'Total de despesas: R$ {contexto["total_despesas"]:,.2f}'
            )
        else:
            return (
                f'⚠️ ATENÇÃO: Seu saldo é NEGATIVO: R$ {contexto["saldo_atual"]:,.2f}. '
                f'\n\nTotal de receitas: R$ {contexto["total_receitas"]:,.2f}\n'
                f'Total de despesas: R$ {contexto["total_despesas"]:,.2f}\n\n'
                "Digite 'por que negativo?' para uma análise completa!"
            )

    @staticmethod
    def gerar_obra(contexto):
        """Retorna informações de obras"""
        if contexto['obra_maior_gasto']:
            return (
                f'📋 Você tem {contexto["total_obras"]} obra(s) cadastrada(s).\n\n'
                f'🎯 Maior gasto: {contexto["obra_maior_gasto"].nome}\n'
                f'   Valor: R$ {contexto["obra_maior_gasto"].total_gasto:,.2f}\n'
            )
        return f'Você tem {contexto["total_obras"]} obra(s) cadastrada(s).'

    @staticmethod
    def gerar_custo(contexto):
        """Retorna informações de custos"""
        return (
            f'📊 Resumo de custos:\n\n'
            f'• Total de despesas: R$ {contexto["total_despesas"]:,.2f}\n'
            f'• Total de receitas: R$ {contexto["total_receitas"]:,.2f}\n'
            f'• Saldo: R$ {contexto["saldo_atual"]:,.2f}\n\n'
            'Para mais detalhes, visite a página de uma obra específica.'
        )

    @staticmethod
    def gerar_relatorio(contexto):
        """Retorna informações de relatórios"""
        return (
            '📊 RELATÓRIOS\n\n'
            f'• Obras ativas: {contexto["total_obras"]}\n'
            f'• Despesas totais: R$ {contexto["total_despesas"]:,.2f}\n'
            f'• Receitas totais: R$ {contexto["total_receitas"]:,.2f}\n'
            f'• Saldo atual: R$ {contexto["saldo_atual"]:,.2f}\n\n'
            '📥 Para exportar:\n'
            '• Acesse a página de uma obra\n'
            "• Clique no botão 'Exportar' no topo\n"
            '• Escolha PDF ou Excel'
        )

    @staticmethod
    def gerar_obrigado():
        """Retorna resposta de agradecimento"""
        return '😊 De nada! Estou aqui para ajudar no que precisar!'

    @staticmethod
    def gerar_default():
        """Retorna resposta padrão"""
        return (
            '🤔 Não entendi exatamente. Posso ajudar com:\n\n'
            '• Saldo e finanças gerais\n'
            '• Informações sobre obras\n'
            '• Relatórios de custos\n'
            '• Alertas de risco\n'
            '• Por que o saldo está negativo?\n'
            '• Exportar relatórios\n\n'
            'Digite o que precisa!'
        )


def gerar_resposta(mensagem, contexto):
    """Gera resposta baseada na categoria detectada"""
    categoria = RespostaIA.detectar_categoria(mensagem)

    handlers = {
        'saudacao': RespostaIA.gerar_saudacao,
        'negativo': lambda: RespostaIA.analisar_negativo(contexto, mensagem),
        'saldo': lambda: RespostaIA.gerar_saldo(contexto),
        'obra': lambda: RespostaIA.gerar_obra(contexto),
        'custo': lambda: RespostaIA.gerar_custo(contexto),
        'relatorio': lambda: RespostaIA.gerar_relatorio(contexto),
        'obrigado': RespostaIA.gerar_obrigado,
    }

    handler = handlers.get(categoria, RespostaIA.gerar_default)
    resposta = handler()

    # Limitar tamanho da resposta (prevenir respostas muito longas)
    if len(resposta) > MAX_RESPONSE_LENGTH:
        resposta = resposta[:MAX_RESPONSE_LENGTH] + '\n\n[resposta truncada]'

    return resposta
