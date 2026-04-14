"""
Rotas de importação de extrato bancário
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.models import db, Empresa, ContaBancaria, LancamentoConta
from app.routes.auth import login_required
from app.config import MAX_CONTENT_LENGTH

extrato_bp = Blueprint('extrato', __name__, url_prefix='/extrato')


# Extensões permitidas para importação de extrato
ALLOWED_EXTENSIONS = {'ofx', 'csv', 'txt'}
ALLOWED_MIME_TYPES = {
    'ofx': ['application/x-ofx', 'application-ofx', 'text/xml'],
    'csv': ['text/csv', 'text/plain', 'application/csv'],
    'txt': ['text/plain', 'application/octet-stream']
}


def validate_upload(file, max_size=None):
    """Valida arquivo de upload"""
    errors = []
    
    if not file or file.filename == '':
        return False, "Nenhum arquivo selecionado"
    
    # Verificar extensão
    ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Extensão não permitida. Use: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Verificar tamanho
    if max_size is None:
        max_size = MAX_CONTENT_LENGTH
    
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if size > max_size:
        return False, f"Arquivo muito grande (max {max_size / 1024 / 1024:.1f}MB)"
    
    if size == 0:
        return False, "Arquivo vazio"
    
    return True, None


@extrato_bp.route('/banco/<int:conta_id>/importar', methods=['GET', 'POST'])
@login_required
def importar_extrato(conta_id):
    """Importar extrato bancário"""
    empresa_id = session.get('empresa_id')
    conta = ContaBancaria.query.filter_by(id=conta_id, empresa_id=empresa_id).first_or_404()
    
    if request.method == 'POST':
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo enviado', 'danger')
            return redirect(url_for('extrato.importar_extrato', conta_id=conta_id))
        
        file = request.files['arquivo']
        
        # Validar arquivo
        valido, erro = validate_upload(file)
        if not valido:
            flash(erro, 'danger')
            return redirect(url_for('extrato.importar_extrato', conta_id=conta_id))
        
        filename = file.filename.lower()
        
        # Tentar detectar encoding - UTF-8 primeiro, fallback para latin-1
        try:
            conteudo = file.read().decode('utf-8')
        except UnicodeDecodeError:
            try:
                conteudo = file.read().decode('latin-1')
            except UnicodeDecodeError:
                flash('Erro ao decodificar arquivo', 'danger')
                return redirect(url_for('extrato.importar_extrato', conta_id=conta_id))
        
        # Limitar tamanho do conteúdo (prevenir DoS)
        if len(conteudo) > 10 * 1024 * 1024:  # 10MB
            flash('Arquivo muito grande para processar', 'danger')
            return redirect(url_for('extrato.importar_extrato', conta_id=conta_id))
        
        lancamentos_importados = 0
        erros = []
        
        # Importar helpers otimizados
        from app.utils.extrato import processar_ofx, processar_csv, processar_cnab
        
        if filename.endswith('.ofx'):
            lancamentos_importados, erros = processar_ofx(conteudo, empresa_id, conta_id)
        elif filename.endswith('.csv'):
            lancamentos_importados, erros = processar_csv(conteudo, empresa_id, conta_id)
        elif filename.endswith('.txt'):
            lancamentos_importados, erros = processar_cnab(conteudo, empresa_id, conta_id)
        else:
            flash('Formato não suportado. Use .ofx, .csv ou .txt (CNAB)', 'danger')
            return redirect(url_for('extrato.importar_extrato', conta_id=conta_id))
        
        if lancamentos_importados > 0:
            flash(f'{lancamentos_importados} lançamento(s) importado(s)!', 'success')
        else:
            flash('Nenhum lançamento encontrado', 'warning')
        
        if erros:
            for erro in erros[:5]:
                flash(erro, 'warning')
        
        return redirect(url_for('banco.banco_detalhe', conta_id=conta_id))
    
    return render_template('banco/importar_extrato.html', conta=conta)


@extrato_bp.route('/api/importar/modelo-csv')
@login_required
def modelo_csv():
    """Baixa modelo de CSV"""
    import csv
    from flask import make_response
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Data', 'Descricao', 'Valor', 'Documento'])
    writer.writerow(['01/01/2026', 'Exemplo crédito', '1500.00', '12345'])
    writer.writerow(['02/01/2026', 'Exemplo débito', '-500.00', ''])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=modelo_extrato.csv'
    
    return response


# Import necessário para io no modelo_csv
import io