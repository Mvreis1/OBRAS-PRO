"""
Migration: Migrar usuarios de 'role' (legacy) para 'role_id' (RBAC)

Executar: flask db_manager migrate_roles
"""
import click
from flask import Flask
from app.models import db
from app.models.models import Usuario, Empresa
from app.models.acesso import Role, Permissao


def create_default_roles(empresa_id=None):
    """Cria roles padrão do sistema"""
    roles_data = [
        {'nome': 'Administrador', 'descricao': 'Acesso total ao sistema', 'is_system': True},
        {'nome': 'Gerente', 'descricao': 'Gerencia obras e financeiro', 'is_system': True},
        {'nome': 'Operador', 'descricao': 'Cadastra lançamentos e obras', 'is_system': True},
        {'nome': 'Visualizador', 'descricao': 'Apenas visualiza relatórios', 'is_system': True},
    ]
    
    roles_created = []
    
    for role_data in roles_data:
        existing = Role.query.filter_by(nome=role_data['nome'], is_system=True).first()
        if not existing:
            role = Role(
                nome=role_data['nome'],
                descricao=role_data['descricao'],
                empresa_id=empresa_id,
                is_system=role_data['is_system']
            )
            db.session.add(role)
            roles_created.append(role_data['nome'])
        else:
            roles_created.append(existing.nome)
    
    return roles_created


def get_role_mapping():
    """Mapeamento do role legacy para nome do role RBAC"""
    return {
        'admin': 'Administrador',
        'viewer': 'Visualizador',
        'gerente': 'Gerente',
        'operador': 'Operador',
    }


def migrate_users_to_role_id():
    """Migra usuários do campo 'role' para 'role_id'"""
    
    # Buscar role Administrador do sistema (global)
    admin_role = Role.query.filter_by(nome='Administrador', is_system=True).first()
    if not admin_role:
        click.echo("❌ Erro: Role Administrador não encontrado. Execute create_default_roles primeiro.")
        return False
    
    # Mapeamento legacy -> role
    role_mapping = get_role_mapping()
    
    # Buscar todos os usuários com role legacy mas sem role_id
    usuarios_legacy = Usuario.query.filter(
        Usuario.role.isnot(None),
        Usuario.role_id.is_(None)
    ).all()
    
    if not usuarios_legacy:
        click.echo("✅ Nenhum usuário para migrar.")
        return True
    
    migrated = 0
    errors = 0
    
    for usuario in usuarios_legacy:
        try:
            legacy_role = usuario.role or 'admin'
            
            # Buscar role correspondente
            role_nome = role_mapping.get(legacy_role, 'Administrador')
            novo_role = Role.query.filter_by(nome=role_nome, is_system=True).first()
            
            if novo_role:
                usuario.role_id = novo_role.id
                # NÃO remover 'role' ainda - mantém para rollback
                migrated += 1
            else:
                # Fallback: usar admin
                usuario.role_id = admin_role.id
                errors += 1
                
        except Exception as e:
            errors += 1
            click.echo(f"❌ Erro migrando usuário {usuario.id}: {e}")
    
    db.session.commit()
    
    click.echo(f"✅ Migração concluída: {migrated} usuários migrados, {errors} com erros.")
    return True


def verify_migration():
    """Verifica se migração foi bem-sucedida"""
    
    # Usuários ainda sem role_id
    sem_role = Usuario.query.filter(Usuario.role_id.is_(None)).count()
    
    # Usuários com role_id
    com_role = Usuario.query.filter(Usuario.role_id.isnot(None)).count()
    
    # Usuários ainda com role legacy
    com_legacy = Usuario.query.filter(Usuario.role.isnot(None)).count()
    
    click.echo(f"\n📊 Status da Migração:")
    click.echo(f"   - Usuários com role_id: {com_role}")
    click.echo(f"   - Usuários sem role_id: {sem_role}")
    click.echo(f"   - Usuários com role legacy: {com_legacy}")
    
    return sem_role == 0 and com_role > 0


def remove_legacy_role_column():
    """Remove a coluna role após verificação (opcional)"""
    
    click.echo("\n⚠️  Para remover completamente o campo 'role' legacy:")
    click.echo("   1. Execute: flask db_manager verify_migration")
    click.echo("   2. Se tudo OK, remova a coluna 'role' manualmente")
    click.echo("   3. Atualize has_permission() para remover fallback")


@click.group()
def db_manager():
    """Gerenciador de migração de roles"""
    pass


@db_manager.command()
def init_roles():
    """Inicializa roles padrão do sistema"""
    with Flask(__name__).app_context():
        roles = create_default_roles()
        db.session.commit()
        click.echo(f"✅ Roles criados: {', '.join(roles)}")


@db_manager.command()
def migrate_roles():
    """Migra usuários de role legacy para role_id"""
    with Flask(__name__).app_context():
        # Primeiro criar roles
        create_default_roles(None)
        db.session.commit()
        
        # Migrar
        migrate_users_to_role_id()
        
        # Verificar
        verify_migration()


@db_manager.command()
def verify_migration():
    """Verifica status da migração"""
    with Flask(__name__).app_context():
        verify_migration()


if __name__ == '__main__':
    db_manager()