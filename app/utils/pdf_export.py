"""
Helper para exportação de relatórios em PDF
"""
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch


class PDFExport:
    """Classe base para exportação de PDFs"""
    
    def __init__(self, title="OBRAS PRO"):
        self.buffer = BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer, 
            pagesize=A4, 
            rightMargin=50, 
            leftMargin=50, 
            topMargin=50, 
            bottomMargin=50
        )
        self.elements = []
        self.styles = getSampleStyleSheet()
        
        # Estilos padrão
        self.title_style = ParagraphStyle(
            'Title', parent=self.styles['Heading1'], 
            fontSize=20, textColor=colors.HexColor('#6366f1'), 
            spaceAfter=20, alignment=TA_CENTER
        )
        self.subtitle_style = ParagraphStyle(
            'Subtitle', parent=self.styles['Normal'], 
            fontSize=12, textColor=colors.gray, 
            alignment=TA_CENTER, spaceAfter=30
        )
        self.heading_style = ParagraphStyle(
            'Heading', parent=self.styles['Heading2'], 
            fontSize=14, textColor=colors.HexColor('#6366f1'), 
            spaceBefore=20, spaceAfter=10
        )
        
    def add_title(self, title):
        self.elements.append(Paragraph(title, self.title_style))
    
    def add_subtitle(self, subtitle):
        self.elements.append(Paragraph(subtitle, self.subtitle_style))
    
    def add_heading(self, heading):
        self.elements.append(Paragraph(heading, self.heading_style))
    
    def add_info_table(self, data, col_widths=None):
        """Adiciona tabela de informações com estilo padrão"""
        if col_widths is None:
            col_widths = [120, 350]
        
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ]))
        self.elements.append(table)
    
    def add_finance_table(self, data, highlight_row=None, highlight_color=None):
        """Adiciona tabela financeira com cores condicionais"""
        col_widths = [200, 200]
        table = Table(data, colWidths=col_widths)
        
        style = TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ])
        
        if highlight_row is not None and highlight_color:
            style.add('TEXTCOLOR', (1, highlight_row), (1, highlight_row), highlight_color)
        
        table.setStyle(style)
        self.elements.append(table)
    
    def add_data_table(self, headers, rows, col_widths=None):
        """Adiciona tabela de dados com header estilizado"""
        if col_widths is None:
            col_widths = [70, 150, 80, 60, 80, 70]
        
        data = [headers] + rows
        table = Table(data, colWidths=col_widths)
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))
        self.elements.append(table)
    
    def add_footer(self):
        self.elements.append(Spacer(1, 30))
        footer_style = ParagraphStyle('Footer', fontSize=8, textColor=colors.gray, alignment=TA_CENTER)
        self.elements.append(Paragraph(f'Relatório gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}', footer_style))
    
    def build(self, filename):
        self.doc.build(self.elements)
        self.buffer.seek(0)
        return self.buffer.getvalue()


def exportar_obra_pdf(obra, lancamentos, total_despesas, total_receitas, saldo):
    """Exporta dados de uma obra para PDF"""
    pdf = PDFExport("Relatório Financeiro da Obra")
    
    pdf.add_title("OBRAS PRO")
    pdf.add_subtitle("Relatório Financeiro da Obra")
    
    # Dados da obra
    pdf.add_heading("Dados da Obra")
    dados_obra = [
        ['Nome:', obra.nome],
        ['Cliente:', obra.cliente or 'Não informado'],
        ['Endereço:', obra.endereco or 'Não informado'],
        ['Status:', obra.status],
        ['Orçamento:', f'R$ {obra.orcamento_previsto:,.2f}'],
        ['Progresso:', f'{obra.progresso}%'],
        ['Data Início:', obra.data_inicio.strftime('%d/%m/%Y') if obra.data_inicio else 'Não definida'],
        ['Previsão Término:', obra.data_fim_prevista.strftime('%d/%m/%Y') if obra.data_fim_prevista else 'Não definida'],
    ]
    pdf.add_info_table(dados_obra)
    
    # Resumo financeiro
    pdf.add_heading("Resumo Financeiro")
    saldo_color = colors.HexColor('#22c55e') if saldo >= 0 else colors.HexColor('#ef4444')
    dados_financeiro = [
        ['Total Receitas', f'R$ {total_receitas:,.2f}'],
        ['Total Despesas', f'R$ {total_despesas:,.2f}'],
        ['Saldo', f'R$ {saldo:,.2f}'],
        ['% Orçamento Utilizado', f'{(total_despesas/obra.orcamento_previsto*100):.1f}%' if obra.orcamento_previsto > 0 else '0%'],
    ]
    pdf.add_finance_table(dados_financeiro, highlight_row=2, highlight_color=saldo_color)
    
    # Lançamentos
    if lancamentos:
        pdf.add_heading("Lançamentos")
        headers = ['Data', 'Descrição', 'Categoria', 'Tipo', 'Valor', 'Status']
        rows = []
        for lanc in lancamentos:
            valor_str = f'R$ {lanc.valor:,.2f}'
            if lanc.tipo == 'Despesa':
                valor_str = f'- {valor_str}'
            
            rows.append([
                lanc.data.strftime('%d/%m/%Y'),
                lanc.descricao[:30] + '...' if len(lanc.descricao) > 30 else lanc.descricao,
                lanc.categoria,
                lanc.tipo,
                valor_str,
                lanc.status_pagamento
            ])
        
        pdf.add_data_table(headers, rows)
    
    pdf.add_footer()
    
    return pdf.build(f"obra_{obra.nome.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf")


def exportar_relatorio_pdf(lancamentos, total_receitas, total_despesas, lucro_prejuizo, obras, data_inicio=None, data_fim=None):
    """Exporta relatório financeiro geral para PDF"""
    pdf = PDFExport("Relatório Financeiro")
    
    pdf.add_title("OBRAS PRO")
    pdf.add_subtitle("Relatório Financeiro")
    
    # Período
    if data_inicio and data_fim:
        pdf.add_subtitle(f"Período: {data_inicio} a {data_fim}")
    elif data_inicio:
        pdf.add_subtitle(f"A partir de: {data_inicio}")
    elif data_fim:
        pdf.add_subtitle(f"Até: {data_fim}")
    
    # Resumo
    pdf.add_heading("Resumo Financeiro")
    lucro_color = colors.HexColor('#22c55e') if lucro_prejuizo >= 0 else colors.HexColor('#ef4444')
    dados_resumo = [
        ['Total Receitas', f'R$ {total_receitas:,.2f}'],
        ['Total Despesas', f'R$ {total_despesas:,.2f}'],
        ['Lucro/Prejuízo', f'R$ {lucro_prejuizo:,.2f}']
    ]
    pdf.add_finance_table(dados_resumo, highlight_row=2, highlight_color=lucro_color)
    
    # Por obra
    pdf.add_heading("Detalhamento por Obra")
    headers = ['Obra', 'Receitas', 'Despesas', 'Saldo']
    rows = []
    
    for obra in obras:
        lancs_obra = [l for l in lancamentos if l.obra_id == obra.id]
        receita = sum(l.valor for l in lancs_obra if l.tipo == 'Receita')
        despesa = sum(l.valor for l in lancs_obra if l.tipo == 'Despesa')
        
        rows.append([
            obra.nome[:25],
            f'R$ {receita:,.2f}',
            f'R$ {despesa:,.2f}',
            f'R$ {receita - despesa:,.2f}'
        ])
    
    if rows:
        pdf.add_data_table(headers, rows, col_widths=[150, 100, 100, 100])
    
    pdf.add_footer()
    
    return pdf.build(f"relatorio_{datetime.now().strftime('%Y%m%d')}.pdf")