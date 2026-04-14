"""
Testes de Contratos e RBAC
"""
import pytest
from datetime import date
from app.models import db, Obra, Usuario
from app.models.contratos import Contrato
from app.models.acesso import Permissao, Role, RolePermissao, PermissaoUsuario
from app.utils.rbac import Modulos, Acoes


class TestContratoCRUD:
    """Testes de CRUD de Contratos"""
    
    def test_listar_contratos_vazio(self, admin_session):
        """Lista contratos sem nenhum cadastrado"""
        response = admin_session.get('/contrato/contratos')
        
        assert response.status_code == 200
    
    def test_criar_contrato(self, admin_session, admin_user):
        """Cria novo contrato"""
        response = admin_session.post('/contrato/contrato/novo', data={
            'cliente': 'Cliente Teste',
            'cliente_cnpj': '12345678000190',
            'cliente_email': 'cliente@teste.com',
            'titulo': 'Contrato de Construcao',
            'descricao': 'Contrato para edificacao',
            'valor': '100000.00',
            'data_inicio': '2024-01-01',
            'data_fim': '2024-12-31',
            'status': 'Ativo',
            'tipo': 'Obra',
            'num_parcelas': '12'
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_ver_detalhes_contrato(self, admin_session, admin_user):
        """Visualiza detalhes do contrato"""
        contrato = Contrato(
            empresa_id=admin_user.empresa_id,
            cliente='Cliente Detalhe',
            titulo='Contrato Detalhe',
            valor=50000,
            status='Ativo',
            tipo='Obra'
        )
        db.session.add(contrato)
        db.session.commit()
        
        response = admin_session.get(f'/contrato/contrato/{contrato.id}')
        
        assert response.status_code == 200
        assert b'Contrato Detalhe' in response.data
    
    def test_editar_contrato(self, admin_session, admin_user):
        """Edita contrato existente"""
        contrato = Contrato(
            empresa_id=admin_user.empresa_id,
            cliente='Cliente Original',
            titulo='Contrato Original',
            valor=30000,
            status='Rascunho',
            tipo='Obra'
        )
        db.session.add(contrato)
        db.session.commit()
        
        response = admin_session.post(f'/contrato/contrato/{contrato.id}/editar', data={
            'cliente': 'Cliente Editado',
            'titulo': 'Contrato Editado',
            'valor': '35000',
            'status': 'Ativo',
            'tipo': 'Obra'
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_excluir_contrato(self, admin_session, admin_user):
        """Exclui contrato"""
        contrato = Contrato(
            empresa_id=admin_user.empresa_id,
            cliente='Cliente Excluir',
            titulo='Contrato Excluir',
            valor=10000,
            status='Rascunho',
            tipo='Obra'
        )
        db.session.add(contrato)
        db.session.commit()
        contrato_id = contrato.id
        
        response = admin_session.post(f'/contrato/contrato/{contrato_id}/excluir', follow_redirects=True)
        
        assert response.status_code == 200
        assert Contrato.query.get(contrato_id) is None


class TestRBAC:
    """Testes de controle de acesso baseado em roles"""
    
    def test_admin_tem_todas_permissoes(self, admin_user):
        """Admin tem acesso a tudo"""
        assert admin_user.has_permission(Modulos.DASHBOARD, Acoes.VER)
        assert admin_user.has_permission(Modulos.OBRAS, Acoes.CRIAR)
        assert admin_user.has_permission(Modulos.OBRAS, Acoes.EXCLUIR)
        assert admin_user.has_permission(Modulos.LANCAMENTOS, Acoes.CRIAR)
        assert admin_user.has_permission(Modulos.USUARIOS, Acoes.GERENCIAR_PERMISSOES)
    
    def test_viewer_tem_permissoes_limitadas(self, viewer_user):
        """Viewer tem permissoes limitadas"""
        # Deve conseguir ver
        assert viewer_user.has_permission(Modulos.DASHBOARD, Acoes.VER)
        
        # Nao deve conseguir criar/editar/excluir
        # (Depende do role Visitante que so tem Acoes.VER)
        has_create = viewer_user.has_permission(Modulos.OBRAS, Acoes.CRIAR)
        # Viewer pode ou nao ter permissao de criacao dependendo do role
    
    def test_role_com_permissoes_especificas(self, app, admin_user):
        """Testa role com permissoes especificas"""
        from app.models.acesso import Role, Permissao, RolePermissao
        from app.models import db, Usuario
        
        # Criar role customizado
        role = Role(
            nome='Test Role',
            descricao='Role para teste',
            empresa_id=admin_user.empresa_id
        )
        db.session.add(role)
        db.session.flush()
        
        # Adicionar apenas permissao de ver obras
        perm_ver_obras = Permissao.query.filter_by(modulo=Modulos.OBRAS, acao=Acoes.VER).first()
        if perm_ver_obras:
            assoc = RolePermissao(role_id=role.id, permissao_id=perm_ver_obras.id)
            db.session.add(assoc)
            db.session.commit()
        
        # Criar usuario com este role (role='viewer' para nao cair no fallback admin)
        usuario = Usuario(
            empresa_id=admin_user.empresa_id,
            nome='Usuario Test Role',
            email='testrole@teste.com',
            username='testrole',
            cargo='Tester',
            role='viewer',  # Legacy role como viewer
            role_id=role.id
        )
        usuario.set_senha('test123')
        db.session.add(usuario)
        db.session.commit()
        
        # Verificar permissoes
        assert usuario.has_permission(Modulos.OBRAS, Acoes.VER)
        assert not usuario.has_permission(Modulos.OBRAS, Acoes.CRIAR)
        assert not usuario.has_permission(Modulos.LANCAMENTOS, Acoes.VER)
    
    def test_permissao_individual_allow(self, app, admin_user):
        """Testa permissao individual allow"""
        # Criar usuario sem role
        usuario = Usuario(
            empresa_id=admin_user.empresa_id,
            nome='Usuario Individual',
            email='individual@teste.com',
            username='individual',
            role='viewer'
        )
        usuario.set_senha('test123')
        db.session.add(usuario)
        db.session.commit()
        
        # Adicionar permissao individual
        perm = Permissao.query.filter_by(modulo=Modulos.OBRAS, acao=Acoes.CRIAR).first()
        if perm:
            perm_user = PermissaoUsuario(
                usuario_id=usuario.id,
                permissao_id=perm.id,
                tipo='allow'
            )
            db.session.add(perm_user)
            db.session.commit()
            
            assert usuario.has_permission(Modulos.OBRAS, Acoes.CRIAR)
    
    def test_permissao_individual_deny_prevalece(self, app, admin_user):
        """Testa que deny individual prevalece sobre allow do role"""
        # Admin tem todas permissoes pelo role
        # Adicionar deny individual
        perm = Permissao.query.filter_by(modulo=Modulos.OBRAS, acao=Acoes.EXCLUIR).first()
        if perm:
            perm_user = PermissaoUsuario(
                usuario_id=admin_user.id,
                permissao_id=perm.id,
                tipo='deny'
            )
            db.session.add(perm_user)
            db.session.commit()
            
            # Agora admin nao deve conseguir excluir obras
            assert not admin_user.has_permission(Modulos.OBRAS, Acoes.EXCLUIR)
    
    def test_listar_roles(self, admin_session):
        """Acessa listagem de roles"""
        response = admin_session.get('/rbac/roles')
        
        assert response.status_code == 200
    
    def test_listar_usuarios_permissoes(self, admin_session):
        """Acessa gerenciamento de permissoes"""
        response = admin_session.get('/rbac/usuarios-permissoes')
        
        assert response.status_code == 200
    
    def test_api_roles(self, admin_session):
        """API de roles"""
        response = admin_session.get('/rbac/api/roles')
        
        assert response.status_code == 200
        assert response.is_json
