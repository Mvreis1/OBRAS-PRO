"""
Testes CRUD de Lancamentos Financeiros
"""
import pytest
from datetime import date, datetime
from app.models import db, Obra, Lancamento


@pytest.fixture
def obra_teste(admin_user):
    """Cria obra para testes de lancamentos"""
    obra = Obra(
        empresa_id=admin_user.empresa_id,
        nome='Obra Lancamento',
        orcamento_previsto=500000,
        status='Em Execucao',
        progresso=30
    )
    db.session.add(obra)
    db.session.commit()
    return obra


class TestLancamentoCRUD:
    """Testes completos de CRUD de Lancamentos"""
    
    def test_listar_lancamentos_vazio(self, admin_session):
        """Lista lancamentos sem nenhum cadastrado"""
        response = admin_session.get('/lancamentos')
        
        assert response.status_code == 200
    
    def test_criar_receita(self, admin_session, admin_user, obra_teste):
        """Cria lancamento de receita"""
        response = admin_session.post('/lancamento/novo', data={
            'obra_id': str(obra_teste.id),
            'descricao': 'Recebimento do cliente',
            'categoria': 'Vendas',
            'tipo': 'Receita',
            'valor': '50000.00',
            'data': '2024-01-15',
            'forma_pagamento': 'PIX',
            'status_pagamento': 'Pago',
            'parcelas': '1'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        lanc = Lancamento.query.filter_by(descricao='Recebimento do cliente').first()
        assert lanc is not None
        assert lanc.tipo == 'Receita'
        assert lanc.valor == 50000.00
    
    def test_criar_despesa(self, admin_session, admin_user, obra_teste):
        """Cria lancamento de despesa"""
        response = admin_session.post('/lancamento/novo', data={
            'obra_id': str(obra_teste.id),
            'descricao': 'Compra de cimento',
            'categoria': 'Material',
            'tipo': 'Despesa',
            'valor': '5000.00',
            'data': '2024-01-20',
            'forma_pagamento': 'Transferencia',
            'status_pagamento': 'Pago',
            'parcelas': '1'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        lanc = Lancamento.query.filter_by(descricao='Compra de cimento').first()
        assert lanc is not None
        assert lanc.tipo == 'Despesa'
    
    def test_criar_lancamento_parcelado(self, admin_session, admin_user, obra_teste):
        """Cria lancamento com parcelas"""
        response = admin_session.post('/lancamento/novo', data={
            'obra_id': str(obra_teste.id),
            'descricao': 'Aluguel de equipamento',
            'categoria': 'Equipamento',
            'tipo': 'Despesa',
            'valor': '12000.00',
            'data': '2024-02-01',
            'forma_pagamento': 'Boleto',
            'status_pagamento': 'Pendente',
            'parcelas': '12'
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_editar_lancamento(self, admin_session, admin_user, obra_teste):
        """Edita lancamento existente"""
        lanc = Lancamento(
            empresa_id=admin_user.empresa_id,
            obra_id=obra_teste.id,
            descricao='Lancamento Original',
            categoria='Material',
            tipo='Despesa',
            valor=1000.00,
            data=date.today().replace(day=1),
            forma_pagamento='Dinheiro',
            status_pagamento='Pago'
        )
        db.session.add(lanc)
        db.session.commit()
        
        response = admin_session.post(f'/lancamento/{lanc.id}/editar', data={
            'obra_id': str(obra_teste.id),
            'descricao': 'Lancamento Editado',
            'categoria': 'Material',
            'tipo': 'Despesa',
            'valor': '1500.00',
            'data': '2024-02-01',
            'forma_pagamento': 'PIX',
            'status_pagamento': 'Pago',
            'parcelas': '1'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        lanc_editado = Lancamento.query.get(lanc.id)
        assert lanc_editado.descricao == 'Lancamento Editado'
        assert lanc_editado.valor == 1500.00
    
    def test_excluir_lancamento(self, admin_session, admin_user, obra_teste):
        """Exclui lancamento"""
        lanc = Lancamento(
            empresa_id=admin_user.empresa_id,
            obra_id=obra_teste.id,
            descricao='Para Excluir',
            categoria='Outros',
            tipo='Despesa',
            valor=100.00,
            data=date.today().replace(day=1),
            forma_pagamento='Dinheiro',
            status_pagamento='Pago'
        )
        db.session.add(lanc)
        db.session.commit()
        lanc_id = lanc.id
        
        response = admin_session.post(f'/lancamento/{lanc_id}/excluir', follow_redirects=True)
        
        assert response.status_code == 200
        assert Lancamento.query.get(lanc_id) is None
    
    def test_filtrar_lancamentos_por_tipo(self, admin_session, admin_user, obra_teste):
        """Filtra lancamentos por tipo"""
        # Criar lancamentos de tipos diferentes
        for tipo in ['Receita', 'Despesa']:
            lanc = Lancamento(
                empresa_id=admin_user.empresa_id,
                obra_id=obra_teste.id,
                descricao=f'Lancamento {tipo}',
                categoria='Outros',
                tipo=tipo,
                valor=1000.00,
                data=date.today().replace(day=1),
                forma_pagamento='PIX',
                status_pagamento='Pago'
            )
            db.session.add(lanc)
        db.session.commit()
        
        response = admin_session.get('/lancamentos?tipo=Receita')
        
        assert response.status_code == 200
        assert b'Receita' in response.data
    
    def test_filtrar_lancamentos_por_obra(self, admin_session, admin_user):
        """Filtra lancamentos por obra"""
        obra1 = Obra(
            empresa_id=admin_user.empresa_id,
            nome='Obra A',
            orcamento_previsto=100000,
            status='Em Execucao'
        )
        obra2 = Obra(
            empresa_id=admin_user.empresa_id,
            nome='Obra B',
            orcamento_previsto=200000,
            status='Em Execucao'
        )
        db.session.add_all([obra1, obra2])
        db.session.commit()
        
        lanc = Lancamento(
            empresa_id=admin_user.empresa_id,
            obra_id=obra1.id,
            descricao='Lancamento Obra A',
            categoria='Material',
            tipo='Despesa',
            valor=5000.00,
            data=date.today().replace(day=1),
            forma_pagamento='PIX',
            status_pagamento='Pago'
        )
        db.session.add(lanc)
        db.session.commit()
        
        response = admin_session.get(f'/lancamentos?obra_id={obra1.id}')
        
        assert response.status_code == 200
        assert b'Lancamento Obra A' in response.data
    
    def test_resumo_financeiro(self, admin_session, admin_user, obra_teste):
        """Verifica resumo financeiro na listagem"""
        # Criar receita e despesa
        for tipo, valor in [('Receita', 50000), ('Despesa', 30000)]:
            lanc = Lancamento(
                empresa_id=admin_user.empresa_id,
                obra_id=obra_teste.id,
                descricao=f'Resumo {tipo}',
                categoria='Outros',
                tipo=tipo,
                valor=float(valor),
                data=date.today().replace(day=1),
                forma_pagamento='PIX',
                status_pagamento='Pago'
            )
            db.session.add(lanc)
        db.session.commit()
        
        response = admin_session.get('/lancamentos')
        
        assert response.status_code == 200
        # Deve mostrar totals
        assert b'50000' in response.data or b'50.000' in response.data
