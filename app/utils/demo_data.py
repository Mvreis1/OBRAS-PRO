"""
Gerador de dados completos de demonstração para o sistema OBRAS PRO
"""

import random
from datetime import date, timedelta

from app.models import Empresa, Lancamento, Obra, db
from app.models.banco import ContaBancaria
from app.models.contratos import Contrato
from app.models.fornecedores import Fornecedor
from app.models.orcamentos import Orcamento


def criar_dados_demo_completos(empresa_id):
    """
    Cria dados completos de demonstração para uma empresa:
    - 10 obras
    - 50+ lançamentos
    - 5 contratos
    - 8 orçamentos
    - 10 fornecedores
    - 3 contas bancárias
    """
    empresa = Empresa.query.get(empresa_id)
    if not empresa:
        raise ValueError('Empresa não encontrada')

    # Verificar se já existem dados
    if Obra.query.filter_by(empresa_id=empresa_id).count() > 5:
        return {'status': 'warning', 'message': 'Já existem dados suficientes na empresa'}

    resultados = {
        'obras': 0,
        'lancamentos': 0,
        'contratos': 0,
        'orcamentos': 0,
        'fornecedores': 0,
        'contas_bancarias': 0,
    }

    # Dados fictícios
    obras_data = [
        {
            'nome': 'Residencial Villa Nova',
            'cliente': 'João Silva',
            'endereco': 'Rua das Flores, 123 - São Paulo, SP',
            'status': 'Em Execução',
            'orcamento': 850000,
            'progresso': 65,
        },
        {
            'nome': 'Centro Comercial Plaza',
            'cliente': 'Imobiliária ABC Ltda',
            'endereco': 'Av. Principal, 500 - Rio de Janeiro, RJ',
            'status': 'Planejamento',
            'orcamento': 2500000,
            'progresso': 10,
        },
        {
            'nome': 'Escola Municipal Prof. Lima',
            'cliente': 'Prefeitura Municipal',
            'endereco': 'Rua da Educação, 45 - Belo Horizonte, MG',
            'status': 'Em Execução',
            'orcamento': 1200000,
            'progresso': 40,
        },
        {
            'nome': 'Hospital Regional Norte',
            'cliente': 'Secretaria de Saúde',
            'endereco': 'Av. da Saúde, 1000 - Porto Alegre, RS',
            'status': 'Planejamento',
            'orcamento': 5000000,
            'progresso': 5,
        },
        {
            'nome': 'Galpão Industrial Logística',
            'cliente': 'Transportadora Rápida S/A',
            'endereco': 'Rodovia BR-101, Km 50 - Curitiba, PR',
            'status': 'Concluída',
            'orcamento': 450000,
            'progresso': 100,
        },
        {
            'nome': 'Edifício Corporate Tower',
            'cliente': 'Empreendimentos XYZ',
            'endereco': 'Av. Paulista, 2000 - São Paulo, SP',
            'status': 'Em Execução',
            'orcamento': 8000000,
            'progresso': 50,
        },
        {
            'nome': 'Residencial Parque Verde',
            'cliente': 'Construtora Horizonte',
            'endereco': 'Rua do Parque, 789 - Florianópolis, SC',
            'status': 'Paralisada',
            'orcamento': 600000,
            'progresso': 30,
        },
        {
            'nome': 'Hotel Resort Tropical',
            'cliente': 'Turismo e Lazer S/A',
            'endereco': 'Rodovia do Sol, Km 25 - Fortaleza, CE',
            'status': 'Entregue',
            'orcamento': 5500000,
            'progresso': 100,
        },
        {
            'nome': 'Fábrica de Componentes',
            'cliente': 'Tech Industry Ltda',
            'endereco': 'Distrito Industrial, Lote 45 - Manaus, AM',
            'status': 'Em Execução',
            'orcamento': 2800000,
            'progresso': 45,
        },
        {
            'nome': 'Condomínio Horizontal Solar',
            'cliente': 'Incorporadora Sol Nascente',
            'endereco': 'Alameda das Palmeiras, 200 - Natal, RN',
            'status': 'Em Execução',
            'orcamento': 1800000,
            'progresso': 55,
        },
    ]

    categorias_despesa = [
        'Material',
        'Mão de Obra',
        'Equipamento',
        'Serviço Terceiro',
        'Imposto',
        'Outros',
    ]
    categorias_receita = ['Venda', 'Prestação de Serviço', 'Outros']

    obras_criadas = []

    # Criar obras
    hoje = date.today()
    for _i, obra_data in enumerate(obras_data):
        obra = Obra(
            empresa_id=empresa_id,
            nome=obra_data['nome'],
            cliente=obra_data['cliente'],
            endereco=obra_data['endereco'],
            status=obra_data['status'],
            orcamento_previsto=obra_data['orcamento'],
            data_inicio=hoje - timedelta(days=random.randint(60, 300)),
            data_fim_prevista=hoje + timedelta(days=random.randint(30, 365)),
            progresso=obra_data['progresso'],
            responsavel=f'Eng. {random.choice(["Carlos", "Maria", "Pedro", "Ana", "Roberto", "Fernanda"])} {random.choice(["Mendes", "Santos", "Oliveira", "Costa", "Lima", "Souza"])}',
            descricao=f'Obra de {obra_data["nome"]} com orçamento de R$ {obra_data["orcamento"]:,.2f}',
        )
        db.session.add(obra)
        obras_criadas.append(obra)
        resultados['obras'] += 1

    db.session.flush()

    # Criar lançamentos para cada obra
    for obra in obras_criadas:
        num_lancamentos = random.randint(5, 8)
        for _ in range(num_lancamentos):
            # Despesas
            for _ in range(random.randint(2, 4)):
                lanc = Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao=random.choice(
                        [
                            'Compra de material de construção',
                            'Pagamento de mão de obra',
                            'Aluguel de equipamentos',
                            'Serviços de engenharia',
                            'Despesas administrativas',
                            'Compra de ferramentas',
                        ]
                    ),
                    categoria=random.choice(categorias_despesa),
                    tipo='Despesa',
                    valor=random.randint(1000, 50000),
                    data=hoje - timedelta(days=random.randint(1, 180)),
                    forma_pagamento=random.choice(['Transferência', 'Boleto', 'PIX', 'Dinheiro']),
                    status_pagamento=random.choice(['Pago', 'Pago', 'Pendente']),
                    parcelas=1,
                )
                db.session.add(lanc)
                resultados['lancamentos'] += 1

            # Receitas
            for _ in range(random.randint(1, 3)):
                lanc = Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao=random.choice(
                        [
                            'Recebimento de cliente',
                            'Entrada de contrato',
                            'Parcela de obra',
                            'Receita de vendas',
                        ]
                    ),
                    categoria=random.choice(categorias_receita),
                    tipo='Receita',
                    valor=random.randint(10000, 100000),
                    data=hoje - timedelta(days=random.randint(1, 180)),
                    forma_pagamento=random.choice(['Transferência', 'Boleto', 'PIX']),
                    status_pagamento='Pago',
                    parcelas=1,
                )
                db.session.add(lanc)
                resultados['lancamentos'] += 1

    # Criar contratos
    contratos_data = [
        {'titulo': 'Contrato de Construção - Villa Nova', 'cliente': 'João Silva', 'valor': 850000},
        {
            'titulo': 'Contrato de Reforma - Escola Lima',
            'cliente': 'Prefeitura Municipal',
            'valor': 1200000,
        },
        {
            'titulo': 'Contrato de Ampliação - Galpão Logística',
            'cliente': 'Transportadora Rápida',
            'valor': 200000,
        },
        {
            'titulo': 'Contrato de Construção - Corporate Tower',
            'cliente': 'Empreendimentos XYZ',
            'valor': 8000000,
        },
        {
            'titulo': 'Contrato de Serviços - Hotel Resort',
            'cliente': 'Turismo e Lazer',
            'valor': 1500000,
        },
    ]

    for contrato_data in contratos_data:
        contrato = Contrato(
            empresa_id=empresa_id,
            titulo=contrato_data['titulo'],
            cliente=contrato_data['cliente'],
            valor=contrato_data['valor'],
            data_inicio=hoje - timedelta(days=random.randint(30, 180)),
            data_fim=hoje + timedelta(days=random.randint(60, 365)),
            status=random.choice(['Ativo', 'Ativo', 'Concluído']),
            tipo='Obra',
            descricao=f'Contrato para {contrato_data["titulo"]}',
        )
        db.session.add(contrato)
        resultados['contratos'] += 1

    # Criar orçamentos
    orcamentos_data = [
        {
            'titulo': 'Orçamento Residencial Villa Nova',
            'cliente': 'João Silva',
            'valor': 850000,
            'status': 'Aprovado',
        },
        {
            'titulo': 'Orçamento Centro Comercial Plaza',
            'cliente': 'Imobiliária ABC',
            'valor': 2500000,
            'status': 'Enviado',
        },
        {
            'titulo': 'Orçamento Escola Municipal',
            'cliente': 'Prefeitura',
            'valor': 1200000,
            'status': 'Aprovado',
        },
        {
            'titulo': 'Orçamento Hospital Regional',
            'cliente': 'Secretaria de Saúde',
            'valor': 5000000,
            'status': 'Rascunho',
        },
        {
            'titulo': 'Orçamento Galpão Industrial',
            'cliente': 'Transportadora',
            'valor': 450000,
            'status': 'Aprovado',
        },
        {
            'titulo': 'Orçamento Corporate Tower',
            'cliente': 'Empreendimentos XYZ',
            'valor': 8000000,
            'status': 'Enviado',
        },
        {
            'titulo': 'Orçamento Hotel Resort',
            'cliente': 'Turismo e Lazer',
            'valor': 5500000,
            'status': 'Aprovado',
        },
        {
            'titulo': 'Orçamento Fábrica Componentes',
            'cliente': 'Tech Industry',
            'valor': 2800000,
            'status': 'Rascunho',
        },
    ]

    for orc_data in orcamentos_data:
        orcamento = Orcamento(
            empresa_id=empresa_id,
            titulo=orc_data['titulo'],
            cliente=orc_data['cliente'],
            valor_materiais=orc_data['valor'] * 0.4,
            valor_mao_obra=orc_data['valor'] * 0.3,
            valor_equipamentos=orc_data['valor'] * 0.15,
            valor_outros=orc_data['valor'] * 0.15,
            desconto=random.randint(0, 50000),
            status=orc_data['status'],
            validade=30,
            prazo_execucao=random.randint(180, 730),
        )
        db.session.add(orcamento)
        resultados['orcamentos'] += 1

    # Criar fornecedores
    fornecedores_data = [
        {
            'nome': 'Materiais de Construção Silva',
            'cnpj': '12.345.678/0001-90',
            'telefone': '(11) 3333-4444',
            'email': 'contato@materiaissilva.com',
        },
        {
            'nome': 'Equipamentos Pesados Ltda',
            'cnpj': '23.456.789/0001-01',
            'telefone': '(11) 3444-5555',
            'email': 'vendas@equipamentos.com',
        },
        {
            'nome': 'Mão de Obra Especializada',
            'cnpj': '34.567.890/0001-12',
            'telefone': '(11) 3555-6666',
            'email': 'contato@maodeobra.com',
        },
        {
            'nome': 'Serviços de Engenharia Pro',
            'cnpj': '45.678.901/0001-23',
            'telefone': '(11) 3666-7777',
            'email': 'projetos@engenhariapro.com',
        },
        {
            'nome': 'Ferramentas e Equipamentos',
            'cnpj': '56.789.012/0001-34',
            'telefone': '(11) 3777-8888',
            'email': 'vendas@ferramentas.com',
        },
        {
            'nome': 'Transportadora Construções',
            'cnpj': '67.890.123/0001-45',
            'telefone': '(11) 3888-9999',
            'email': 'logistica@transportadora.com',
        },
        {
            'nome': 'Acabamentos Premium',
            'cnpj': '78.901.234/0001-56',
            'telefone': '(11) 3999-0000',
            'email': 'vendas@acabamentos.com',
        },
        {
            'nome': 'Elétrica e Hidráulica Ltda',
            'cnpj': '89.012.345/0001-67',
            'telefone': '(11) 4000-1111',
            'email': 'contato@eletricahidraulica.com',
        },
        {
            'nome': 'Vidros e Esquadrias',
            'cnpj': '90.123.456/0001-78',
            'telefone': '(11) 4111-2222',
            'email': 'vendas@vidros.com',
        },
        {
            'nome': 'Pisos e Revestimentos',
            'cnpj': '01.234.567/0001-89',
            'telefone': '(11) 4222-3333',
            'email': 'contato@pisos.com',
        },
    ]

    for forn_data in fornecedores_data:
        fornecedor = Fornecedor(
            empresa_id=empresa_id,
            nome=forn_data['nome'],
            cnpj=forn_data['cnpj'],
            telefone=forn_data['telefone'],
            email=forn_data['email'],
            status='Ativo',
        )
        db.session.add(fornecedor)
        resultados['fornecedores'] += 1

    # Criar contas bancárias
    contas_data = [
        {'banco': 'Banco do Brasil', 'agencia': '1234-5', 'conta': '12345-6', 'saldo': 500000},
        {'banco': 'Itaú', 'agencia': '6789-0', 'conta': '98765-4', 'saldo': 350000},
        {'banco': 'Bradesco', 'agencia': '4567-8', 'conta': '54321-0', 'saldo': 200000},
    ]

    for conta_data in contas_data:
        conta = ContaBancaria(
            empresa_id=empresa_id,
            banco=conta_data['banco'],
            agencia=conta_data['agencia'],
            conta=conta_data['conta'],
            saldo_inicial=conta_data['saldo'],
            ativa=True,
        )
        db.session.add(conta)
        resultados['contas_bancarias'] += 1

    db.session.commit()

    return {
        'status': 'ok',
        'message': 'Dados de demonstração criados com sucesso!',
        'dados': resultados,
    }
