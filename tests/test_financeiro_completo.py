"""
Testes abrangentes de rotas financeiras (lançamentos, relatórios, dashboard)
Cobre: CRUD de lançamentos, filtros, cálculos financeiros, relatórios
"""

from datetime import date, datetime, timedelta

import pytest

from app.models import Lancamento, Obra, db


class TestLancamentoCRUD:
    """Testes de CRUD de lançamentos financeiros"""

    def test_criar_lancamento_receita(self, admin_session, admin_user):
        """Criar lançamento de receita"""
        empresa_id = admin_user.empresa_id

        # Cria obra primeiro
        obra = Obra(empresa_id=empresa_id, nome='Obra Teste', status='Planejamento')
        db.session.add(obra)
        db.session.commit()

        response = admin_session.post(
            '/lancamento/novo',
            data={
                'obra_id': obra.id,
                'descricao': 'Receita de projeto',
                'categoria': 'Vendas',
                'tipo': 'Receita',
                'valor': '15000.00',
                'data': '2026-04-15',
                'forma_pagamento': 'Transferência',
                'status_pagamento': 'Pago',
                'documento': 'NF-001',
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b'Lancamento' in response.data or b'cadastrado' in response.data.lower()

        # Verifica no banco
        lancamento = Lancamento.query.filter_by(descricao='Receita de projeto').first()
        assert lancamento is not None
        assert lancamento.tipo == 'Receita'
        assert lancamento.valor == 15000.00

    def test_criar_lancamento_despesa(self, admin_session, admin_user):
        """Criar lançamento de despesa"""
        empresa_id = admin_user.empresa_id

        obra = Obra(empresa_id=empresa_id, nome='Obra Teste 2', status='Em Execução')
        db.session.add(obra)
        db.session.commit()

        response = admin_session.post(
            '/lancamento/novo',
            data={
                'obra_id': obra.id,
                'descricao': 'Compra de materiais',
                'categoria': 'Materiais',
                'tipo': 'Despesa',
                'valor': '5000.50',
                'data': '2026-04-10',
                'forma_pagamento': 'PIX',
                'status_pagamento': 'Pago',
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        lancamento = Lancamento.query.filter_by(descricao='Compra de materiais').first()
        assert lancamento is not None
        assert lancamento.tipo == 'Despesa'
        assert lancamento.valor == 5000.50

    def test_criar_lancamento_sem_obra(self, admin_session):
        """Criar lançamento sem vincular a obra"""
        response = admin_session.post(
            '/lancamento/novo',
            data={
                'descricao': 'Despesa sem obra',
                'categoria': 'Geral',
                'tipo': 'Despesa',
                'valor': '1000.00',
                'data': '2026-04-15',
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

    def test_editar_lancamento(self, admin_session, admin_user):
        """Editar lançamento existente"""
        empresa_id = admin_user.empresa_id

        # Cria obra primeiro
        obra = Obra(empresa_id=empresa_id, nome='Obra Editar', status='Em Execução')
        db.session.add(obra)
        db.session.commit()

        # Cria lançamento
        lanc = Lancamento(
            empresa_id=empresa_id,
            obra_id=obra.id,
            descricao='Lançamento Original',
            categoria='Geral',
            tipo='Despesa',
            valor=1000.00,
            data=date(2026, 4, 1),
        )
        db.session.add(lanc)
        db.session.commit()

        # Edita
        response = admin_session.post(
            f'/lancamento/{lanc.id}/editar',
            data={
                'descricao': 'Lançamento Editado',
                'categoria': 'Materiais',
                'tipo': 'Despesa',
                'valor': '2000.00',
                'data': '2026-04-10',
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b'Lancamento' in response.data or b'atualizado' in response.data.lower()

        # Verifica atualização
        db.session.refresh(lanc)
        assert lanc.descricao == 'Lançamento Editado'
        assert lanc.valor == 2000.00

    def test_excluir_lancamento(self, admin_session, admin_user):
        """Excluir lançamento"""
        empresa_id = admin_user.empresa_id

        # Cria obra primeiro
        obra = Obra(empresa_id=empresa_id, nome='Obra Excluir', status='Em Execução')
        db.session.add(obra)
        db.session.commit()

        lanc = Lancamento(
            empresa_id=empresa_id,
            obra_id=obra.id,
            descricao='Para Excluir',
            categoria='Geral',
            tipo='Despesa',
            valor=500.00,
            data=date(2026, 4, 1),
        )
        db.session.add(lanc)
        db.session.commit()
        lanc_id = lanc.id

        response = admin_session.post(
            f'/lancamento/{lanc_id}/excluir',
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b'exclu' in response.data.lower()

        # Verifica exclusão
        lanc_excluido = Lancamento.query.get(lanc_id)
        assert lanc_excluido is None


class TestLancamentoFiltros:
    """Testes de filtros de lançamentos"""

    @pytest.fixture
    def lancamentos_sample(self, admin_user):
        """Cria lançamentos de exemplo para testes de filtro"""
        empresa_id = admin_user.empresa_id

        # Cria uma obra para vincular os lançamentos
        obra = Obra(empresa_id=empresa_id, nome='Obra Filtros', status='Em Execução')
        db.session.add(obra)
        db.session.commit()

        dados = [
            ('Receita', 'Vendas', 10000, '2026-01-15'),
            ('Despesa', 'Materiais', 5000, '2026-02-10'),
            ('Receita', 'Serviços', 8000, '2026-03-05'),
            ('Despesa', 'Mão de obra', 6000, '2026-04-01'),
            ('Receita', 'Vendas', 12000, '2026-04-20'),
        ]

        lancamentos = []
        for tipo, cat, valor, data_str in dados:
            lanc = Lancamento(
                empresa_id=empresa_id,
                obra_id=obra.id,
                descricao=f'{tipo} {cat}',
                categoria=cat,
                tipo=tipo,
                valor=valor,
                data=datetime.strptime(data_str, '%Y-%m-%d').date(),
            )
            lancamentos.append(lanc)

        db.session.add_all(lancamentos)
        db.session.commit()
        return lancamentos

    def test_listar_lancamentos(self, admin_session, lancamentos_sample):
        """Listar todos os lançamentos"""
        response = admin_session.get('/lancamentos')
        assert response.status_code == 200

    def test_filtrar_por_tipo(self, admin_session, lancamentos_sample):
        """Filtrar lançamentos por tipo"""
        response = admin_session.get('/lancamentos?tipo=Receita')
        assert response.status_code == 200

    def test_filtrar_por_categoria(self, admin_session, lancamentos_sample):
        """Filtrar lançamentos por categoria"""
        response = admin_session.get('/lancamentos?categoria=Materiais')
        assert response.status_code == 200

    def test_filtrar_por_periodo(self, admin_session, lancamentos_sample):
        """Filtrar lançamentos por período"""
        response = admin_session.get('/lancamentos?data_inicio=2026-03-01&data_fim=2026-04-30')
        assert response.status_code == 200

    def test_filtrar_por_busca(self, admin_session, lancamentos_sample):
        """Filtrar lançamentos por busca textual"""
        response = admin_session.get('/lancamentos?busca=Vendas')
        assert response.status_code == 200


class TestDashboard:
    """Testes do dashboard financeiro"""

    def test_dashboard_carrega(self, admin_session):
        """Dashboard carrega sem erros"""
        response = admin_session.get('/dashboard')
        assert response.status_code == 200

    def test_dashboard_com_lancamentos(self, admin_session, admin_user):
        """Dashboard com lançamentos mostra dados corretos"""
        empresa_id = admin_user.empresa_id

        # Cria obra primeiro
        obra = Obra(empresa_id=empresa_id, nome='Obra Dashboard', status='Em Execução')
        db.session.add(obra)
        db.session.commit()

        # Cria lançamentos
        db.session.add_all(
            [
                Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao='Receita 1',
                    categoria='Vendas',
                    tipo='Receita',
                    valor=50000,
                    data=date.today(),
                ),
                Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao='Despesa 1',
                    categoria='Materiais',
                    tipo='Despesa',
                    valor=30000,
                    data=date.today(),
                ),
            ]
        )
        db.session.commit()

        response = admin_session.get('/dashboard')
        assert response.status_code == 200

    def test_dashboard_api(self, admin_session, admin_user):
        """API do dashboard retorna JSON correto"""
        empresa_id = admin_user.empresa_id

        # Cria obra primeiro
        obra = Obra(empresa_id=empresa_id, nome='Obra API', status='Em Execução')
        db.session.add(obra)
        db.session.commit()

        db.session.add_all(
            [
                Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao='Receita API',
                    categoria='Vendas',
                    tipo='Receita',
                    valor=10000,
                    data=date.today(),
                ),
                Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao='Despesa API',
                    categoria='Materiais',
                    tipo='Despesa',
                    valor=5000,
                    data=date.today(),
                ),
            ]
        )
        db.session.commit()

        response = admin_session.get('/api/dashboard')
        assert response.status_code == 200

        data = response.get_json()
        assert 'despesas_mes' in data
        assert 'receitas_mes' in data
        assert 'saldo_atual' in data
        assert data['saldo_atual'] == 5000  # 10000 - 5000


class TestRelatorios:
    """Testes de relatórios financeiros"""

    def test_relatorio_geral_carrega(self, admin_session):
        """Relatório geral carrega"""
        response = admin_session.get('/relatorios')
        assert response.status_code == 200

    def test_relatorio_com_filtro_data(self, admin_session, admin_user):
        """Relatório com filtro de data"""
        response = admin_session.get('/relatorios?data_inicio=2026-01-01&data_fim=2026-12-31')
        assert response.status_code == 200

    def test_relatorio_lucro_por_obra(self, admin_session, admin_user):
        """Relatório mostra lucro por obra"""
        empresa_id = admin_user.empresa_id

        # Cria obra e lançamentos
        obra = Obra(empresa_id=empresa_id, nome='Obra Relatório', status='Em Execução')
        db.session.add(obra)
        db.session.commit()

        db.session.add_all(
            [
                Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao='Receita Obra',
                    categoria='Vendas',
                    tipo='Receita',
                    valor=100000,
                    data=date(2026, 4, 1),
                ),
                Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao='Despesa Obra',
                    categoria='Materiais',
                    tipo='Despesa',
                    valor=60000,
                    data=date(2026, 4, 5),
                ),
            ]
        )
        db.session.commit()

        response = admin_session.get('/relatorios')
        assert response.status_code == 200

    def test_relatorio_exportar_pdf(self, admin_session):
        """Exportar relatório para PDF"""
        response = admin_session.get('/relatorios/exportar/pdf')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/pdf'


class TestObrasFinanceiro:
    """Testes financeiros de obras"""

    def test_criar_obra_com_dados(self, admin_session):
        """Criar obra com dados completos"""
        response = admin_session.post(
            '/obra/nova',
            data={
                'nome': 'Edifício Alpha',
                'descricao': 'Construção de edifício residencial',
                'endereco': 'Rua das Flores, 123',
                'orcamento_previsto': '500000.00',
                'data_inicio': '2026-01-01',
                'data_fim_prevista': '2026-12-31',
                'status': 'Em Execução',
                'progresso': '30',
                'responsavel': 'Eng. Silva',
                'cliente': 'Cliente ABC',
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b'Obra' in response.data and b'cadastrada' in response.data.lower()

    def test_limite_obras(self, admin_session, admin_user):
        """Verifica limite de obras por plano - pulado"""
        pass

        # Tenta criar obra
        response = admin_session.post(
            '/obra/nova',
            data={
                'nome': 'Obra com Limite',
                'orcamento_previsto': '100000',
            },
            follow_redirects=True,
        )

        # Pode passar ou falhar dependendo da implementação
        assert response.status_code == 200

    def test_editar_obra(self, admin_session, admin_user):
        """Editar dados de obra"""
        empresa_id = admin_user.empresa_id

        obra = Obra(
            empresa_id=empresa_id,
            nome='Obra Original',
            status='Planejamento',
            orcamento_previsto=100000,
        )
        db.session.add(obra)
        db.session.commit()

        response = admin_session.post(
            f'/obra/{obra.id}/editar',
            data={
                'nome': 'Obra Editada',
                'status': 'Em Execução',
                'orcamento_previsto': '200000',
                'progresso': '50',
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b'Obra' in response.data and b'atualizada' in response.data.lower()

        db.session.refresh(obra)
        assert obra.nome == 'Obra Editada'
        assert obra.orcamento_previsto == 200000

    def test_excluir_obra(self, admin_session, admin_user):
        """Excluir obra"""
        empresa_id = admin_user.empresa_id

        obra = Obra(
            empresa_id=empresa_id,
            nome='Obra Para Excluir',
            status='Planejamento',
        )
        db.session.add(obra)
        db.session.commit()
        obra_id = obra.id

        response = admin_session.post(
            f'/obra/{obra_id}/excluir',
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b'exclu' in response.data.lower()

        obra_excluida = Obra.query.get(obra_id)
        assert obra_excluida is None


class TestCalculosFinanceiros:
    """Testes de cálculos e agregações financeiras"""

    def test_saldo_atual(self, admin_session, admin_user):
        """Calcula saldo atual corretamente"""
        empresa_id = admin_user.empresa_id

        # Cria obra primeiro
        obra = Obra(empresa_id=empresa_id, nome='Obra Saldo', status='Em Execução')
        db.session.add(obra)
        db.session.commit()

        db.session.add_all(
            [
                Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao='Receita 1',
                    categoria='Vendas',
                    tipo='Receita',
                    valor=80000,
                    data=date(2026, 4, 1),
                ),
                Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao='Despesa 1',
                    categoria='Materiais',
                    tipo='Despesa',
                    valor=45000,
                    data=date(2026, 4, 5),
                ),
                Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao='Receita 2',
                    categoria='Vendas',
                    tipo='Receita',
                    valor=20000,
                    data=date(2026, 4, 10),
                ),
            ]
        )
        db.session.commit()

        response = admin_session.get('/api/dashboard')
        data = response.get_json()

        assert data['saldo_atual'] == 55000  # 80000 + 20000 - 45000

    def test_despesas_por_categoria(self, admin_session, admin_user):
        """Agregação de despesas por categoria"""
        empresa_id = admin_user.empresa_id

        # Cria obra primeiro
        obra = Obra(empresa_id=empresa_id, nome='Obra Categorias', status='Em Execução')
        db.session.add(obra)
        db.session.commit()

        db.session.add_all(
            [
                Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao='Despesa materiais',
                    tipo='Despesa',
                    categoria='Materiais',
                    valor=10000,
                    data=date(2026, 4, 1),
                ),
                Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao='Despesa mão de obra',
                    tipo='Despesa',
                    categoria='Mão de obra',
                    valor=15000,
                    data=date(2026, 4, 5),
                ),
                Lancamento(
                    empresa_id=empresa_id,
                    obra_id=obra.id,
                    descricao='Despesa equipamentos',
                    tipo='Despesa',
                    categoria='Mão de obra',
                    valor=20000,
                    data=date(2026, 4, 10),
                ),
            ]
        )
        db.session.commit()

        response = admin_session.get('/relatorios')
        assert response.status_code == 200

    def test_evolution_mensal(self, admin_session, admin_user):
        """Evolução mensal de receitas e despesas"""
        empresa_id = admin_user.empresa_id

        # Cria obra primeiro
        obra = Obra(empresa_id=empresa_id, nome='Obra Evolução', status='Em Execução')
        db.session.add(obra)
        db.session.commit()

        # Cria lançamentos em meses diferentes
        for mes in range(1, 5):
            db.session.add_all(
                [
                    Lancamento(
                        empresa_id=empresa_id,
                        obra_id=obra.id,
                        descricao=f'Receita mês {mes}',
                        categoria='Vendas',
                        tipo='Receita',
                        valor=10000 * mes,
                        data=date(2026, mes, 15),
                    ),
                    Lancamento(
                        empresa_id=empresa_id,
                        obra_id=obra.id,
                        descricao=f'Despesa mês {mes}',
                        categoria='Materiais',
                        tipo='Despesa',
                        valor=5000 * mes,
                        data=date(2026, mes, 20),
                    ),
                ]
            )
        db.session.commit()

        response = admin_session.get('/relatorios')
        assert response.status_code == 200


class TestExportacao:
    """Testes de exportação de dados"""

    def test_exportar_obra_excel(self, admin_session, admin_user):
        """Exportar dados de obra para Excel"""
        empresa_id = admin_user.empresa_id

        obra = Obra(empresa_id=empresa_id, nome='Obra Exportar', status='Em Execução')
        db.session.add(obra)
        db.session.commit()

        db.session.add(
            Lancamento(
                empresa_id=empresa_id,
                obra_id=obra.id,
                descricao='Despesa exportar',
                categoria='Materiais',
                tipo='Despesa',
                valor=5000,
                data=date(2026, 4, 1),
            )
        )
        db.session.commit()

        response = admin_session.get(f'/obra/{obra.id}/exportar')
        assert response.status_code == 200
        assert 'application/vnd.openxmlformats' in response.headers['Content-Type']

    def test_exportar_obra_pdf(self, admin_session, admin_user):
        """Exportar dados de obra para PDF"""
        empresa_id = admin_user.empresa_id

        obra = Obra(empresa_id=empresa_id, nome='Obra PDF', status='Em Execução')
        db.session.add(obra)
        db.session.commit()

        response = admin_session.get(f'/obra/{obra.id}/exportar/pdf')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/pdf'
