"""
Backup automático do sistema OBRAS PRO
Suporta SQLite e PostgreSQL
"""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from app.routes.auth import login_required
from app.utils.monitoring import require_admin

backup_bp = Blueprint('backup', __name__)


class BackupManager:
    """Gerenciador de backups automáticos - Suporta SQLite e PostgreSQL"""

    def __init__(self, backup_dir=None):
        if backup_dir is None:
            # Diretório padrão: instance/backups
            self.backup_dir = Path(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'instance',
                    'backups',
                )
            )
        else:
            self.backup_dir = Path(backup_dir)

        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _is_postgresql(self):
        """Verifica se está usando PostgreSQL"""
        from app.config import DB_PATH

        db_url = DB_PATH
        return 'postgres://' in db_url or 'postgresql://' in db_url

    def _get_db_url(self):
        """Obtém URL do banco de dados"""
        from app.config import DB_PATH

        return DB_PATH

    def criar_backup(self, tipo='full'):
        """
        Cria backup do banco de dados (SQLite ou PostgreSQL)

        Args:
            tipo: 'full' (banco + uploads) ou 'db' (apenas banco)

        Returns:
            dict com informações do backup
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if tipo == 'full':
            filename = f'obras_pro_full_{timestamp}.zip'
        else:
            filename = f'obras_pro_db_{timestamp}.sql'

        filepath = self.backup_dir / filename

        try:
            if self._is_postgresql():
                # Backup PostgreSQL usando pg_dump
                return self._criar_backup_postgres(filepath, tipo, timestamp)
            else:
                # Backup SQLite (cópia direta)
                return self._criar_backup_sqlite(filepath, tipo, timestamp)

        except Exception as e:
            current_app.logger.error(f'Erro ao criar backup: {e}')
            return {'success': False, 'error': str(e)}

    def _criar_backup_postgres(self, filepath, tipo, timestamp):
        """Cria backup usando pg_dump (PostgreSQL)"""
        db_url = self._get_db_url()

        # pg_dump gera SQL dump
        dump_file = filepath.with_suffix('.sql')

        try:
            # Executar pg_dump
            result = subprocess.run(
                ['pg_dump', '--no-owner', '--no-privileges', '--clean', '--if-exists', db_url],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutos timeout
                check=False,
            )

            if result.returncode != 0:
                raise Exception(f'pg_dump failed: {result.stderr}') from None

            # Salvar dump
            with open(dump_file, 'w') as f:
                f.write(result.stdout)

            if tipo == 'full':
                # Adicionar uploads ao zip
                uploads_dir = Path(
                    os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads'
                    )
                )
                if uploads_dir.exists():
                    shutil.make_archive(str(filepath.with_suffix('')), 'zip', uploads_dir)
                else:
                    # Apenas SQL
                    filepath = dump_file

            # Verificar tamanho
            size = filepath.stat().st_size if filepath.exists() else 0

            return {
                'success': True,
                'filename': filepath.name,
                'size_bytes': size,
                'path': str(filepath),
                'created_at': datetime.now().isoformat(),
                'type': 'postgresql',
            }

        except subprocess.TimeoutExpired:
            raise Exception('pg_dump timeout - banco muito grande?') from None
        finally:
            # Limpar arquivo temporário se criou zip
            if tipo == 'full' and dump_file.exists():
                dump_file.unlink()

    def _criar_backup_sqlite(self, filepath, tipo, timestamp):
        """Cria backup por cópia de arquivo (SQLite)"""
        from app.config import DB_PATH

        if not DB_PATH:
            raise Exception('DB_PATH não configurado')

        db_path = DB_PATH.replace('sqlite:///', '')

        if not os.path.exists(db_path):
            raise Exception(f'Arquivo do banco não encontrado: {db_path}')

        if tipo == 'full':
            # Backup completo com uploads
            # Copiar banco para arquivo temporário
            temp_db = filepath.with_suffix('.db')
            shutil.copy2(db_path, temp_db)

            # Compactar
            shutil.make_archive(str(filepath.with_suffix('')), 'zip', self.backup_dir, temp_db.stem)
            temp_db.unlink()
            filepath = filepath.with_suffix('.zip')
        else:
            # Apenas banco
            shutil.copy2(db_path, filepath)

        # Verificar tamanho
        size = filepath.stat().st_size if filepath.exists() else 0

        return {
            'success': True,
            'filename': filepath.name,
            'size_bytes': size,
            'path': str(filepath),
            'created_at': datetime.now().isoformat(),
            'type': 'sqlite',
        }

    def listar_backups(self):
        """Lista backups existentes"""
        backups = []

        for f in sorted(self.backup_dir.glob('obras_pro_*.zip'), reverse=True):
            backups.append(
                {
                    'filename': f.name,
                    'size_bytes': f.stat().st_size,
                    'created_at': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                }
            )

        for f in sorted(self.backup_dir.glob('obras_pro_*.sql'), reverse=True):
            backups.append(
                {
                    'filename': f.name,
                    'size_bytes': f.stat().st_size,
                    'created_at': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                }
            )

        return backups

    def restaurar_backup(self, filename):
        """Restaura um backup (SQLite ou PostgreSQL)"""
        backup_file = self.backup_dir / filename

        if not backup_file.exists():
            return {'success': False, 'error': 'Arquivo não encontrado'}

        try:
            if self._is_postgresql():
                return self._restaurar_backup_postgres(backup_file, filename)
            else:
                return self._restaurar_backup_sqlite(backup_file, filename)

        except Exception as e:
            current_app.logger.error(f'Erro ao restaurar backup: {e}')
            return {'success': False, 'error': str(e)}

    def _restaurar_backup_postgres(self, backup_file, filename):
        """Restaura backup PostgreSQL usando psql"""
        db_url = self._get_db_url()

        try:
            # Backup preventivo do estado atual
            subprocess.run(
                ['pg_dump', '--no-owner', '--no-privileges', db_url],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )

            # Executar restore
            if filename.endswith('.zip'):
                # Extrair SQL do zip
                import zipfile

                with zipfile.ZipFile(backup_file, 'r') as z:
                    sql_files = [f for f in z.namelist() if f.endswith('.sql')]
                    if not sql_files:
                        raise Exception('Nenhum arquivo SQL encontrado no zip')

                    sql_content = z.read(sql_files[0]).decode('utf-8')
            else:
                sql_content = backup_file.read_text()

            # Executar psql
            result = subprocess.run(
                ['psql', db_url],
                input=sql_content,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )

            if result.returncode != 0:
                raise Exception(f'psql failed: {result.stderr}')

            return {'success': True, 'message': 'Backup restaurado com sucesso (PostgreSQL)'}

        except subprocess.TimeoutExpired:
            raise Exception('Restore timeout - banco muito grande?') from None

    def _restaurar_backup_sqlite(self, backup_file, filename):
        """Restaura backup SQLite"""
        from app.config import DB_PATH

        db_path = DB_PATH.replace('sqlite:///', '')

        # Criar backup do estado atual antes de restaurar
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pre_restore = self.backup_dir / f'pre_restore_{timestamp}.db'
        shutil.copy2(db_path, pre_restore)

        # Restaurar
        if filename.endswith('.zip'):
            # Extrair
            import zipfile

            with zipfile.ZipFile(backup_file, 'r') as z:
                z.extractall(self.backup_dir)

            # Pegar .db extraído
            db_files = list(self.backup_dir.glob('obras_pro_*.db'))
            if db_files:
                shutil.copy2(db_files[0], db_path)
        else:
            shutil.copy2(backup_file, db_path)

        return {'success': True, 'message': 'Backup restaurado com sucesso (SQLite)'}

    def excluir_backup(self, filename):
        """Exclui um backup"""
        backup_file = self.backup_dir / filename

        if backup_file.exists():
            backup_file.unlink()
            return {'success': True}

        return {'success': False, 'error': 'Arquivo não encontrado'}


# Instância global
backup_manager = BackupManager()


@backup_bp.route('/backup/criar', methods=['POST'])
@login_required
@require_admin
def criar_backup():
    """
    Criar backup manual
    ---
    tags:
      - Backup
    parameters:
      - name: tipo
        in: body
        type: string
        required: false
        description: Tipo de backup (full ou db)
    responses:
      200:
        description: Backup criado
    """
    tipo = request.json.get('tipo', 'db') if request.json else 'db'
    result = backup_manager.criar_backup(tipo)

    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 500


@backup_bp.route('/backup/listar')
@login_required
@require_admin
def listar_backups():
    """
    Listar backups disponíveis
    ---
    tags:
      - Backup
    responses:
      200:
        description: Lista de backups
    """
    backups = backup_manager.listar_backups()
    return jsonify({'backups': backups})


@backup_bp.route('/backup/restaurar', methods=['POST'])
@login_required
@require_admin
def restaurar_backup():
    """
    Restaurar backup
    ---
    tags:
      - Backup
    responses:
      200:
        description: Backup restaurado
    """
    filename = request.json.get('filename') if request.json else None

    if not filename:
        return jsonify({'error': 'Nome do arquivo não fornecido'}), 400

    result = backup_manager.restaurar_backup(filename)

    if result['success']:
        return jsonify(result)
    return jsonify(result), 500


@backup_bp.route('/backup/excluir', methods=['DELETE'])
@login_required
@require_admin
def excluir_backup():
    """
    Excluir backup
    ---
    tags:
      - Backup
    responses:
      200:
        description: Backup excluído
    """
    filename = request.args.get('filename')

    if not filename:
        return jsonify({'error': 'Nome do arquivo não fornecido'}), 400

    result = backup_manager.excluir_backup(filename)
    return jsonify(result)


def setup_scheduled_backups(app):
    """Configura backups agendados"""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()

    # Backup diário às 2:00 da manhã
    scheduler.add_job(
        lambda: backup_manager.criar_backup('db'),
        'cron',
        hour=2,
        minute=0,
        id='daily_backup',
        name='Backup diário',
        replace_existing=True,
    )

    # Backup semanal aos domingos às 3:00
    scheduler.add_job(
        lambda: backup_manager.criar_backup('full'),
        'cron',
        day_of_week='sun',
        hour=3,
        minute=0,
        id='weekly_full_backup',
        name='Backup semanal completo',
        replace_existing=True,
    )

    scheduler.start()

    # Limpar backups antigos (manter apenas 7 diários + 4 semanais)
    old_backups = sorted(backup_manager.backup_dir.glob('obras_pro_db_*.sql'))
    for old in old_backups[:-7]:
        old.unlink()

    old_full = sorted(backup_manager.backup_dir.glob('obras_pro_full_*.zip'))
    for old in old_full[:-4]:
        old.unlink()

    return scheduler
