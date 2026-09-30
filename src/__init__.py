"""Paquete src del sistema modular de selección de conductores y simulación electrostática."""

from src.lector_catalogo import (
    ConductorEntrada,
    CandidatoHaz,
    RegistroDescarte,
    ResultadoLectura,
    leer_y_filtrar_catalogo,
)
from src.balance_termico import (
    ParametrosAmbientales,
    ResultadoBalanceTermico,
    calcular_balance_termico,
)
from src.metodo_cargas import (
    ResultadoCSM,
    simular_csm,
)
from src.exportador import (
    RegistroConductorFinal,
    exportar_resultados_excel,
    exportar_figuras,
    exportar_reporte_auditoria,
)

__all__ = [
    "ConductorEntrada",
    "CandidatoHaz",
    "RegistroDescarte",
    "ResultadoLectura",
    "leer_y_filtrar_catalogo",
    "ParametrosAmbientales",
    "ResultadoBalanceTermico",
    "calcular_balance_termico",
    "ResultadoCSM",
    "simular_csm",
    "RegistroConductorFinal",
    "exportar_resultados_excel",
    "exportar_figuras",
    "exportar_reporte_auditoria",
]
