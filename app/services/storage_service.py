"""Storage service - Cloud storage (S3, R2, etc.) para uploads persistentes"""

import os
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename

# Tenta importar boto3, mas permite fallback para storage local
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class StorageService:
    """Serviço para upload e gerenciamento de arquivos em cloud storage (S3-compatible)"""

    @staticmethod
    def _get_s3_client():
        """Obtém cliente S3 configurado"""
        if not BOTO3_AVAILABLE:
            raise RuntimeError('boto3 não está instalado. Execute: pip install boto3')

        endpoint_url = current_app.config.get('AWS_S3_ENDPOINT_URL') or None
        return boto3.client(
            's3',
            aws_access_key_id=current_app.config.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=current_app.config.get('AWS_SECRET_ACCESS_KEY'),
            region_name=current_app.config.get('AWS_S3_REGION', 'us-east-1'),
            endpoint_url=endpoint_url,
        )

    @staticmethod
    def upload_file(file, folder='obras', filename=None):
        """
        Faz upload de arquivo para S3.

        Args:
            file: File object do Flask (request.files)
            folder: Pasta no bucket (ex: 'obras', 'documentos')
            filename: Nome customizado (gera automático se None)

        Returns:
            (url_arquivo, error_message)
        """
        if not current_app.config.get('USE_S3_STORAGE'):
            return None, 'S3 storage não configurado'

        try:
            # Validar arquivo
            if not file or not file.filename:
                return None, 'Nenhum arquivo selecionado'

            # Gerar nome seguro
            original_filename = secure_filename(file.filename)
            if not original_filename:
                return None, 'Nome de arquivo inválido'

            # Extrair extensão
            extensao = os.path.splitext(original_filename)[1].lower()
            if not extensao:
                return None, 'Arquivo sem extensão'

            # Gerar nome único com timestamp
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'{timestamp}_{original_filename}'

            # Caminho completo no S3
            s3_key = f'{folder}/{filename}'

            # Upload para S3
            s3_client = StorageService._get_s3_client()
            bucket = current_app.config.get('AWS_S3_BUCKET')

            # Reset file pointer
            file.seek(0)

            s3_client.upload_fileobj(
                file,
                bucket,
                s3_key,
                ExtraArgs={
                    'ContentType': file.content_type or 'application/octet-stream',
                    'ACL': 'public-read',  # Tornar arquivo público
                },
            )

            # Gerar URL pública
            endpoint_url = current_app.config.get('AWS_S3_ENDPOINT_URL')
            custom_url = current_app.config.get('AWS_S3_URL')

            if custom_url:
                # Usar URL customizada (CloudFront, etc)
                url_arquivo = f'{custom_url.rstrip("/")}/{s3_key}'
            elif endpoint_url:
                # URL do endpoint (R2, MinIO)
                url_arquivo = f'{endpoint_url.rstrip("/")}/{bucket}/{s3_key}'
            else:
                # URL padrão AWS S3
                region = current_app.config.get('AWS_S3_REGION', 'us-east-1')
                if region == 'us-east-1':
                    url_arquivo = f'https://{bucket}.s3.amazonaws.com/{s3_key}'
                else:
                    url_arquivo = f'https://{bucket}.s3.{region}.amazonaws.com/{s3_key}'

            return url_arquivo, None

        except NoCredentialsError:
            return None, 'Credenciais S3 não configuradas'
        except ClientError as e:
            current_app.logger.error(f'Erro no upload S3: {e}')
            return None, f'Erro no upload: {e!s}'
        except Exception as e:
            current_app.logger.error(f'Erro inesperado no upload: {e}')
            return None, f'Erro ao fazer upload: {e!s}'

    @staticmethod
    def delete_file(file_url):
        """
        Remove arquivo do S3.

        Args:
            file_url: URL completa do arquivo ou chave S3

        Returns:
            (success, error_message)
        """
        if not current_app.config.get('USE_S3_STORAGE'):
            return False, 'S3 storage não configurado'

        try:
            # Extrair chave S3 da URL
            s3_key = StorageService._extract_s3_key(file_url)
            if not s3_key:
                return False, 'Não foi possível identificar o arquivo'

            s3_client = StorageService._get_s3_client()
            bucket = current_app.config.get('AWS_S3_BUCKET')

            s3_client.delete_object(Bucket=bucket, Key=s3_key)
            return True, None

        except ClientError as e:
            current_app.logger.error(f'Erro ao deletar arquivo S3: {e}')
            return False, f'Erro ao deletar: {e!s}'
        except Exception as e:
            current_app.logger.error(f'Erro inesperado ao deletar: {e}')
            return False, f'Erro ao deletar arquivo: {e!s}'

    @staticmethod
    def _extract_s3_key(file_url):
        """Extrai a chave S3 de uma URL"""
        if not file_url:
            return None

        # Se já é uma chave (sem http), retorna direto
        if not file_url.startswith('http'):
            return file_url

        # Extrair da URL
        endpoint_url = current_app.config.get('AWS_S3_ENDPOINT_URL')
        custom_url = current_app.config.get('AWS_S3_URL')
        bucket = current_app.config.get('AWS_S3_BUCKET')

        if custom_url and file_url.startswith(custom_url):
            return file_url.replace(f'{custom_url.rstrip("/")}/', '')

        if endpoint_url and file_url.startswith(endpoint_url):
            return file_url.replace(f'{endpoint_url.rstrip("/")}/{bucket}/', '')

        # AWS S3 padrão
        if '.s3' in file_url:
            parts = file_url.split('.s3')
            if len(parts) > 1:
                # Extrair após a região
                rest = parts[1]
                if '.amazonaws.com/' in rest:
                    return rest.split('.amazonaws.com/', 1)[1]
                elif 'amazonaws.com/' in rest:
                    return rest.split('amazonaws.com/', 1)[1]

        return None

    @staticmethod
    def get_local_upload_path(folder='obras'):
        """
        Obtém caminho local para upload (fallback quando S3 não configurado).

        Returns:
            (upload_dir, relative_path)
        """
        upload_dir = os.path.join('app', 'static', 'uploads', folder)
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir, upload_dir

    @staticmethod
    def save_local_file(file, folder='obras', filename=None):
        """
        Salva arquivo localmente (fallback).

        Returns:
            (relative_url, error_message)
        """
        try:
            if not file or not file.filename:
                return None, 'Nenhum arquivo selecionado'

            original_filename = secure_filename(file.filename)
            if not original_filename:
                return None, 'Nome de arquivo inválido'

            extensao = os.path.splitext(original_filename)[1].lower()
            if not extensao:
                return None, 'Arquivo sem extensão'

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if not filename:
                filename = f'{timestamp}_{original_filename}'

            upload_dir = StorageService.get_local_upload_path(folder)[0]
            caminho_arquivo = os.path.join(upload_dir, filename)

            file.seek(0)
            file.save(caminho_arquivo)

            if os.path.exists(caminho_arquivo):
                relative_url = f'/static/uploads/{folder}/{filename}'
                return relative_url, None
            else:
                return None, 'Erro ao salvar arquivo'

        except Exception as e:
            current_app.logger.error(f'Erro ao salvar localmente: {e}')
            return None, f'Erro ao salvar: {e!s}'

    @staticmethod
    def delete_local_file(relative_url):
        """Remove arquivo local (fallback)"""
        try:
            if not relative_url or not relative_url.startswith('/static'):
                return False, 'URL inválida'

            # Converter URL para caminho filesystem
            file_path = os.path.join('app', relative_url.lstrip('/'))

            if os.path.exists(file_path):
                os.remove(file_path)
                return True, None
            return False, 'Arquivo não encontrado'

        except Exception as e:
            current_app.logger.error(f'Erro ao remover arquivo local: {e}')
            return False, f'Erro ao remover: {e!s}'
