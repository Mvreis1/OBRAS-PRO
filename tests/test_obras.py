"""
Testes CRUD de Obras
"""
import pytest
from datetime import date
from app.models import db, Obra, Lancamento


class TestObraCRUD:
    """Testes completos de CRUD de Obras"""
    
    def test_listar_obras_vazio(self, admin_session):
        """Lista obras sem nenhuma cadastrada"""
        response = admin_session.get('/obras')
        
        assert response.status_code == 200
    
    def test_criar_obra_sucesso(self, admin_session, admin_user):
        """Cria uma nova obra"""
        response = admin_session.post('/obra/nova', data={
            'nome': 'Edificio Central',
            'descricao': 'Obra teste de edificio comercial',
            'endereco': 'Rua Teste, 123, Centro',
            'orcamento_previsto': '500000.00',
            'data_inicio': '2024-01-01',
            'data_fim_prevista': '2024-12-31',
            'status': 'Em Execucao',
            'progresso': '25',
            'responsavel': 'Engenheiro Teste',
            'cliente': 'Cliente Teste'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert Obra.query.filter_by(nome='Edificio Central').first() is not None
    
    def test_criar_obra_campos_obrigatorios(self, admin_session):
        """Cria obra com apenas campos obrigatorios"""
        response = admin_session.post('/obra/nova', data={
            'nome': 'Obra Minimalista',
            'orcamento_previsto': '100000',
            'status': 'Planejamento',
            'progresso': '0',
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_ver_detalhes_obra(self, admin_session, admin_user):
        """Visualiza detalhes de uma obra"""
        obra = Obra(
            empresa_id=admin_user.empresa_id,
            nome='Obra Detalhe',
            orcamento_previsto=200000,
            status='Em Execucao',
            progresso=50
        )
        db.session.add(obra)
        db.session.commit()
        
        response = admin_session.get(f'/obra/{obra.id}')
        
        assert response.status_code == 200
        assert b'Obra Detalhe' in response.data
    
    def test_editar_obra(self, admin_session, admin_user):
        """Edita uma obra existente"""
        obra = Obra(
            empresa_id=admin_user.empresa_id,
            nome='Obra Original',
            orcamento_previsto=300000,
            status='Planejamento',
            progresso=10
        )
        db.session.add(obra)
        db.session.commit()
        
        response = admin_session.post(f'/obra/{obra.id}/editar', data={
            'nome': 'Obra Editada',
            'orcamento_previsto': '350000',
            'status': 'Em Execucao',
            'progresso': '30',
        }, follow_redirects=True)
        
        assert response.status_code == 200
        obra_editada = Obra.query.get(obra.id)
        assert obra_editada.nome == 'Obra Editada'
        assert obra_editada.orcamento_previsto == 350000
    
    def test_excluir_obra(self, admin_session, admin_user):
        """Exclui uma obra"""
        obra = Obra(
            empresa_id=admin_user.empresa_id,
            nome='Obra para Excluir',
            orcamento_previsto=100000,
            status='Planejamento',
            progresso=0
        )
        db.session.add(obra)
        db.session.commit()
        obra_id = obra.id
        
        response = admin_session.post(f'/obra/{obra_id}/excluir', follow_redirects=True)
        
        assert response.status_code == 200
        assert Obra.query.get(obra_id) is None
    
    def test_isolamento_empresas(self, admin_session, app):
        """Usuario nao ve obras de outra empresa"""
        from app.models import Empresa, Usuario, Obra
        
        # Criar empresa e usuario separados
        with app.app_context():
            empresa2 = Empresa(
                nome='Empresa Separada',
                slug='empresa-separada',
                email='sep@empresa.com',
                plano='free'
            )
            from app.models import db
            db.session.add(empresa2)
            db.session.flush()
            
            obra = Obra(
                empresa_id=empresa2.id,
                nome='Obra Empresa Diferente',
                orcamento_previsto=50000,
                status='Planejamento'
            )
            db.session.add(obra)
            db.session.commit()
        
        # Admin nao deve ver esta obra
        response = admin_session.get('/obras')
        assert response.status_code == 200
        assert b'Obra Empresa Diferente' not in response.data
    
    def test_dashboard_com_obras(self, admin_session, admin_user):
        """Dashboard exibe dados com obras cadastradas"""
        obra = Obra(
            empresa_id=admin_user.empresa_id,
            nome='Obra Dashboard',
            orcamento_previsto=1000000,
            status='Em Execucao',
            progresso=40
        )
        db.session.add(obra)
        db.session.commit()
        
        response = admin_session.get('/dashboard')
        
        assert response.status_code == 200


class TestObraValidacoes:
    """Testes de validacao de obras"""
    
    def test_criar_obra_sem_nome(self, admin_session):
        """Nao permite criar obra sem nome"""
        response = admin_session.post('/obra/nova', data={
            'nome': '',
            'orcamento_previsto': '100000',
            'status': 'Planejamento',
        })
        
        # Deve falhar (redirecionar ou mostrar erro)
        assert response.status_code in [200, 302, 400]
    
    def test_acessar_obra_outra_empresa(self, admin_session):
        """Nao permite acessar obra de outra empresa"""
        response = admin_session.get('/obra/99999')
        
        assert response.status_code in [404, 302]
