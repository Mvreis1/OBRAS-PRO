"""
Executar o servidor Flask
"""
import os
from app import create_app
from app.config import validate_production_config
from app.models import db

app = create_app()


def create_cli_commands(app):
    """Registra comandos CLI na app"""
    
    @app.cli.command()
    def init_roles():
        """Inicializa roles padrão do sistema"""
        from app.models.acesso import Role
        
        roles_data = [
            {'nome': 'Administrador', 'descricao': 'Acesso total ao sistema', 'is_system': True},
            {'nome': 'Gerente', 'descricao': 'Gerencia obras e financeiro', 'is_system': True},
            {'nome': 'Operador', 'descricao': 'Cadastra lançamentos e obras', 'is_system': True},
            {'nome': 'Visualizador', 'descricao': 'Apenas visualiza relatórios', 'is_system': True},
        ]
        
        for role_data in roles_data:
            existing = Role.query.filter_by(nome=role_data['nome'], is_system=True).first()
            if not existing:
                role = Role(**role_data)
                db.session.add(role)
        
        db.session.commit()
        print("✅ Roles padrão criados!")

    @app.cli.command()
    def migrate_roles():
        """Migra usuários de role legacy para role_id"""
        from app.models import Usuario
        from app.models.acesso import Role
        
        app.cli.invoke(init_roles)
        
        role_mapping = {
            'admin': 'Administrador',
            'viewer': 'Visualizador',
            'gerente': 'Gerente',
            'operador': 'Operador',
        }
        
        usuarios = Usuario.query.filter(
            Usuario.role.isnot(None),
            Usuario.role_id.is_(None)
        ).all()
        
        migrated = 0
        for usuario in usuarios:
            legacy = usuario.role or 'admin'
            role_nome = role_mapping.get(legacy, 'Administrador')
            novo_role = Role.query.filter_by(nome=role_nome, is_system=True).first()
            
            if novo_role:
                usuario.role_id = novo_role.id
                migrated += 1
        
        db.session.commit()
        print(f"✅ {migrated} usuários migrados!")

    @app.cli.command()
    def verify_migration():
        """Verifica status da migração"""
        from app.models import Usuario
        
        com_role = Usuario.query.filter(Usuario.role_id.isnot(None)).count()
        sem_role = Usuario.query.filter(Usuario.role_id.is_(None)).count()
        com_legacy = Usuario.query.filter(Usuario.role.isnot(None)).count()
        
        print(f"\n📊 Status:")
        print(f"   - Com role_id: {com_role}")
        print(f"   - Sem role_id: {sem_role}")
        print(f"   - Com role legacy: {com_legacy}")

    @app.cli.command()
    def seed_db():
        """Executa seed de dados iniciais"""
        from seed_rbac import seed_rbac
        
        print("🌱 Executando seed do banco de dados...")
        try:
            seed_rbac()
            print("✅ Seed concluído com sucesso!")
        except Exception as e:
            print(f"❌ Erro no seed: {e}")
            import traceback
            print(traceback.format_exc())

    @app.cli.command()
    def create_admin():
        """Cria usuário admin para testes"""
        from app.models import Empresa, Usuario
        from app.models.acesso import Role
        
        print("👤 Criando usuário admin de teste...")
        
        try:
            # Criar empresa
            empresa = Empresa.query.filter_by(slug='admin-teste').first()
            if not empresa:
                empresa = Empresa(
                    nome='Empresa Admin Teste',
                    slug='admin-teste',
                    cnpj='12345678000190',
                    email='admin@teste.com',
                    plano='pro',
                    max_usuarios=10,
                    max_obras=100
                )
                db.session.add(empresa)
                db.session.flush()
                print(f"✅ Empresa criada: {empresa.nome} (ID: {empresa.id})")
            
            # Buscar role Administrador
            admin_role = Role.query.filter_by(nome='Administrador', is_system=True).first()
            
            # Criar usuário admin
            usuario = Usuario.query.filter_by(email='admin@obraspro.com').first()
            if not usuario:
                usuario = Usuario(
                    empresa_id=empresa.id,
                    nome='Administrador',
                    email='admin@obraspro.com',
                    username='admin',
                    cargo='Administrador',
                    role='admin',
                    role_id=admin_role.id if admin_role else None,
                    ativo=True
                )
                usuario.set_senha('Admin123!')
                db.session.add(usuario)
                db.session.commit()
                print(f"✅ Usuário admin criado!")
                print(f"   Email: admin@obraspro.com")
                print(f"   Senha: Admin123!")
                print(f"   Empresa: {empresa.nome}")
            else:
                print("ℹ️ Usuário admin já existe")
                print(f"   Email: admin@obraspro.com")
                print(f"   Senha: Admin123!")
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            import traceback
            print(traceback.format_exc())
            db.session.rollback()


if __name__ == '__main__':
    from app.config import validate_production_config
    
    create_cli_commands(app)
    validate_production_config()
    
    print("=" * 50)
    print("OBRAS PRO - Servidor iniciado")
    print("=" * 50)
    print("Acesse: http://localhost:5000")
    print("=" * 50)
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
