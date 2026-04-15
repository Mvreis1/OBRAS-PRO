"""DTOs - Data Transfer Objects for the OBRAS_FINANCEIRO application.

DTOs provide a typed, safe way to transfer data between layers (routes -> services -> models).
Each domain has Create, Update, and Response DTOs with validation methods.
"""

# Base DTOs
# Banco DTOs
from app.dtos.banco import (
    ContaBancariaCreateDTO,
    ContaBancariaResponseDTO,
    ContaBancariaResumoDTO,
    ContaBancariaUpdateDTO,
    ExtratoDTO,
    LancamentoContaCreateDTO,
    LancamentoContaResponseDTO,
    TransferenciaCreateDTO,
)
from app.dtos.base import (
    ApiResponse,
    BaseDTO,
    PaginatedResponse,
)

# Contrato DTOs
from app.dtos.contrato import (
    ContratoCreateDTO,
    ContratoFiltrosDTO,
    ContratoResponseDTO,
    ContratoResumoDTO,
    ContratoUpdateDTO,
    ContratoVencimentoDTO,
    ParcelaContratoResponseDTO,
)

# Lancamento DTOs
from app.dtos.lancamento import (
    LancamentoCreateDTO,
    LancamentoFiltrosDTO,
    LancamentoResponseDTO,
    LancamentoResumoDTO,
    LancamentoUpdateDTO,
)

# Notificacao DTOs
from app.dtos.notificacao import (
    EmailConfigDTO,
    EmailEnvioDTO,
    NotificacaoCreateDTO,
    NotificacaoFiltrosDTO,
    NotificacaoResponseDTO,
    NotificacaoResumoDTO,
)

# Obra DTOs
from app.dtos.obra import (
    ObraCreateDTO,
    ObraFiltrosDTO,
    ObraResponseDTO,
    ObraResumoDTO,
    ObraUpdateDTO,
)

# Orcamento DTOs
from app.dtos.orcamento import (
    ItemOrcamentoCreateDTO,
    ItemOrcamentoResponseDTO,
    OrcamentoCreateDTO,
    OrcamentoFiltrosDTO,
    OrcamentoResponseDTO,
    OrcamentoResumoDTO,
    OrcamentoUpdateDTO,
)

# Usuario and Empresa DTOs
from app.dtos.usuario import (
    EmpresaCreateDTO,
    EmpresaResponseDTO,
    EmpresaUpdateDTO,
    LoginDTO,
    RoleCreateDTO,
    RoleResponseDTO,
    UsuarioCreateDTO,
    UsuarioResponseDTO,
    UsuarioUpdateDTO,
)

__all__ = [
    'ApiResponse',
    # Base
    'BaseDTO',
    # Banco
    'ContaBancariaCreateDTO',
    'ContaBancariaResponseDTO',
    'ContaBancariaResumoDTO',
    'ContaBancariaUpdateDTO',
    # Contrato
    'ContratoCreateDTO',
    'ContratoFiltrosDTO',
    'ContratoResponseDTO',
    'ContratoResumoDTO',
    'ContratoUpdateDTO',
    'ContratoVencimentoDTO',
    'EmailConfigDTO',
    'EmailEnvioDTO',
    'EmpresaCreateDTO',
    'EmpresaResponseDTO',
    'EmpresaUpdateDTO',
    'ExtratoDTO',
    'ItemOrcamentoCreateDTO',
    'ItemOrcamentoResponseDTO',
    'LancamentoContaCreateDTO',
    'LancamentoContaResponseDTO',
    # Lancamento
    'LancamentoCreateDTO',
    'LancamentoFiltrosDTO',
    'LancamentoResponseDTO',
    'LancamentoResumoDTO',
    'LancamentoUpdateDTO',
    'LoginDTO',
    # Notificacao
    'NotificacaoCreateDTO',
    'NotificacaoFiltrosDTO',
    'NotificacaoResponseDTO',
    'NotificacaoResumoDTO',
    # Obra
    'ObraCreateDTO',
    'ObraFiltrosDTO',
    'ObraResponseDTO',
    'ObraResumoDTO',
    'ObraUpdateDTO',
    # Orcamento
    'OrcamentoCreateDTO',
    'OrcamentoFiltrosDTO',
    'OrcamentoResponseDTO',
    'OrcamentoResumoDTO',
    'OrcamentoUpdateDTO',
    'PaginatedResponse',
    'ParcelaContratoResponseDTO',
    'RoleCreateDTO',
    'RoleResponseDTO',
    'TransferenciaCreateDTO',
    # Usuario/Empresa
    'UsuarioCreateDTO',
    'UsuarioResponseDTO',
    'UsuarioUpdateDTO',
]
