"""
Utilitários de paginação para o sistema OBRAS PRO
"""
from math import ceil


def _validar_page(page):
    """Valida e converte o número da página"""
    try:
        p = int(page) if page else 1
        return max(1, p)
    except (ValueError, TypeError):
        return 1


class Paginacao:
    """
    Classe de paginação reutilizável.
    
    Uso:
        pag = Paginacao(query, page, per_page=20)
        items = pág.items # itens da página atual
        return render_template('...', paginacao=pag, items=items)
    
    Args:
        query: Query SQLAlchemy
        page: Número da página
        per_page: Itens por página
        use_count: Se False, não executa count() (otimização para tabelas grandes)
    """
    
    def __init__(self, query, page=None, per_page=20, use_count=True):
        self.query = query
        self.per_page = per_page
        self.page = _validar_page(page)
        
        # Contagem opcional (pode ser lento em tabelas grandes)
        if use_count:
            self.total = query.count()
        else:
            # Usar SQL COUNT sem overhead
            self.total = query.with_entities(query.model.__table__.primary_key).count()
        
        self.pages = ceil(self.total / per_page) if self.total > 0 else 1
        
        # Garantir que page está dentro do range
        if self.page > self.pages:
            self.page = self.pages
        
        # Calcular offset
        self.offset = (self.page - 1) * per_page
        
        # Buscar itens
        self.items = query.offset(self.offset).limit(per_page).all()
        
        # Flags de navegação
        self.has_prev = self.page > 1
        self.has_next = self.page < self.pages
        
        # Números de página para exibição
        self.prev_num = self.page - 1 if self.has_prev else None
        self.next_num = self.page + 1 if self.has_next else None

    def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
        """
        Gera uma lista inteligente de números de página para exibição.
        Exemplo: [1, 2, None, 8, 9, 10, 11, 12, None, 49, 50]
        """
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge or
                (self.page - left_current <= num <= self.page + right_current) or
                num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num
    
    def to_dict(self):
        """Converte para dict (útil para APIs)"""
        return {
            'page': self.page,
            'per_page': self.per_page,
            'total': self.total,
            'pages': self.pages,
            'has_prev': self.has_prev,
            'has_next': self.has_next,
            'prev_num': self.prev_num,
            'next_num': self.next_num,
        }


def paginar_query(query, page=None, per_page=20, use_count=True):
    """
    Função helper para paginação simples.
    
    Args:
        query: Query SQLAlchemy
        page: Número da página
        per_page: Itens por página
        use_count: Se False, otimiza para tabelas grandes
    
    Retorna uma instância de Paginacao.
    """
    return Paginacao(query, page=page, per_page=per_page, use_count=use_count)
