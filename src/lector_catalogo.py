"""Módulo de lectura, validación y filtrado preliminar de catálogos de conductores.

Este módulo carga la plantilla estándar en formato Excel, valida su integridad estructural
y tipos de datos, y aplica el criterio normativo de descarte inmediato (UPME 04-2014)
sobre resistencia equivalente DC y capacidad de corriente preliminar para los haces evaluados.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import openpyxl


@dataclass
class ConductorEntrada:
    """Representa los datos técnicos de entrada de un conductor del catálogo."""

    fila_origen: int
    tipo_conductor: str
    calibre: str
    nombre_clave: str
    diametro_exterior_mm: float
    resistencia_dc_20c_ohm_km: float
    ampacidad_catalogo_A: float
    area_aluminio_mm2: Optional[float] = None
    area_acero_mm2: Optional[float] = None
    peso_kg_km: Optional[float] = None
    carga_rotura_kgf: Optional[float] = None

    @property
    def radio_m(self) -> float:
        """Radio exterior del conductor en metros."""
        return (self.diametro_exterior_mm / 1000.0) / 2.0

    @property
    def diametro_m(self) -> float:
        """Diámetro exterior del conductor en metros."""
        return self.diametro_exterior_mm / 1000.0

    @property
    def resistencia_dc_20c_ohm_m(self) -> float:
        """Resistencia DC a 20 °C en Ohm/m."""
        return self.resistencia_dc_20c_ohm_km / 1000.0


@dataclass
class CandidatoHaz:
    """Representa la combinación de un conductor y una configuración de haz que pasa el filtro previo."""

    conductor: ConductorEntrada
    n_subconductores: int
    resistencia_eq_dc_20c_ohm_km: float
    corriente_preliminar_A: float


@dataclass
class RegistroDescarte:
    """Registra la causa exacta por la cual una combinación conductor-haz fue descartada."""

    conductor: ConductorEntrada
    n_subconductores: int
    etapa: str  # 'filtro_rapido' o 'balance_termico'
    motivo: str
    resistencia_eq: Optional[float] = None
    corriente_evaluada: Optional[float] = None


@dataclass
class ResultadoLectura:
    """Contenedor de los resultados de la carga y filtrado del catálogo."""

    candidatos_admitidos: List[CandidatoHaz] = field(default_factory=list)
    descartes: List[RegistroDescarte] = field(default_factory=list)
    total_conductores_leidos: int = 0
    descartes_resistencia: int = 0
    descartes_corriente: int = 0
    descartes_ambos: int = 0
    advertencias: List[str] = field(default_factory=list)


COLUMNAS_OBLIGATORIAS = [
    "tipo_conductor",
    "calibre",
    "nombre_clave",
    "diametro_exterior_mm",
    "resistencia_dc_20c_ohm_km",
    "ampacidad_catalogo_a",
]

COLUMNAS_OPCIONALES = [
    "area_aluminio_mm2",
    "area_acero_mm2",
    "peso_kg_km",
    "carga_rotura_kgf",
]


def _limpiar_numero(valor: Any) -> Optional[float]:
    """Convierte un valor genérico a float, tolerando strings con coma decimal o espacios."""
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    val_str = str(valor).strip().replace(",", ".")
    try:
        return float(val_str)
    except ValueError:
        return None


def leer_y_filtrar_catalogo(
    ruta_archivo: str,
    haces_a_evaluar: List[int],
    r_max_upme_ohm_km: float = 0.0230,
    i_requerida_a: float = 2400.0,
) -> ResultadoLectura:
    """Carga la plantilla Excel del catálogo y aplica el filtro preliminar UPME.

    Parameters
    ----------
    ruta_archivo : str
        Ruta al archivo Excel de la plantilla estandarizada.
    haces_a_evaluar : list of int
        Lista de configuraciones de haz a evaluar, ej. [3, 4].
    r_max_upme_ohm_km : float, optional
        Límite normativo superior de resistencia equivalente a 20 °C en Ohm/km (defecto: 0.0230).
    i_requerida_a : float, optional
        Límite normativo inferior de capacidad de corriente por fase en Amperios (defecto: 2400.0).

    Returns
    -------
    ResultadoLectura
        Estructura con los candidatos que superaron el filtro, los registros de descarte
        y el resumen estadístico de la lectura.

    Raises
    ------
    FileNotFoundError
        Si no se encuentra el archivo en la ruta indicada.
    ValueError
        Si faltan columnas obligatorias en la plantilla.
    """
    if not os.path.exists(ruta_archivo):
        raise FileNotFoundError(f"No se encontró el archivo del catálogo en: '{ruta_archivo}'")

    resultado = ResultadoLectura()

    # Cargar archivo con pandas
    try:
        df = pd.read_excel(ruta_archivo, sheet_name=0)
    except Exception as exc:
        raise ValueError(f"Error al leer el archivo Excel '{ruta_archivo}': {exc}") from exc

    # Normalizar nombres de columnas (minúsculas, sin espacios redundantes)
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Verificar columnas obligatorias
    faltantes = [col for col in COLUMNAS_OBLIGATORIAS if col not in df.columns]
    if faltantes:
        raise ValueError(
            f"La plantilla Excel no contiene las columnas obligatorias requeridas: {faltantes}. "
            f"Columnas detectadas: {list(df.columns)}"
        )

    resultado.total_conductores_leidos = len(df)

    # Iterar cada registro del catálogo
    for idx, row in df.iterrows():
        fila_excel = idx + 2  # Asumiendo encabezado en fila 1

        tipo = str(row.get("tipo_conductor", "")).strip()
        calibre = str(row.get("calibre", "")).strip()
        nombre_clave = str(row.get("nombre_clave", "")).strip()

        # Omitir filas completamente vacías
        if not calibre and not nombre_clave:
            continue

        d_mm = _limpiar_numero(row.get("diametro_exterior_mm"))
        rdc20 = _limpiar_numero(row.get("resistencia_dc_20c_ohm_km"))
        i_cat = _limpiar_numero(row.get("ampacidad_catalogo_a"))

        # Validaciones de integridad numérica
        if d_mm is None or d_mm <= 0:
            resultado.advertencias.append(
                f"Fila {fila_excel} ({calibre} {nombre_clave}): Diámetro exterior inválido ({d_mm}). Se omite."
            )
            continue
        if rdc20 is None or rdc20 <= 0:
            resultado.advertencias.append(
                f"Fila {fila_excel} ({calibre} {nombre_clave}): Resistencia DC 20°C inválida ({rdc20}). Se omite."
            )
            continue
        if i_cat is None or i_cat <= 0:
            resultado.advertencias.append(
                f"Fila {fila_excel} ({calibre} {nombre_clave}): Ampacidad de catálogo inválida ({i_cat}). Se omite."
            )
            continue

        cond = ConductorEntrada(
            fila_origen=fila_excel,
            tipo_conductor=tipo or "ACSR",
            calibre=calibre,
            nombre_clave=nombre_clave or calibre,
            diametro_exterior_mm=d_mm,
            resistencia_dc_20c_ohm_km=rdc20,
            ampacidad_catalogo_A=i_cat,
            area_aluminio_mm2=_limpiar_numero(row.get("area_aluminio_mm2")),
            area_acero_mm2=_limpiar_numero(row.get("area_acero_mm2")),
            peso_kg_km=_limpiar_numero(row.get("peso_kg_km")),
            carga_rotura_kgf=_limpiar_numero(row.get("carga_rotura_kgf")),
        )

        # Evaluar para cada configuración de haz
        for n in haces_a_evaluar:
            req_n = rdc20 / float(n)
            i_prelim_n = float(n) * i_cat

            cumple_r = req_n <= r_max_upme_ohm_km
            cumple_i = i_prelim_n >= i_requerida_a

            if cumple_r and cumple_i:
                resultado.candidatos_admitidos.append(
                    CandidatoHaz(
                        conductor=cond,
                        n_subconductores=n,
                        resistencia_eq_dc_20c_ohm_km=req_n,
                        corriente_preliminar_A=i_prelim_n,
                    )
                )
            else:
                # Determinar motivo de descarte
                if not cumple_r and not cumple_i:
                    motivo = (
                        f"R_eq={req_n:.5f} > {r_max_upme_ohm_km:.4f} Ω/km "
                        f"e I_prelim={i_prelim_n:.1f} < {i_requerida_a:.1f} A"
                    )
                    resultado.descartes_ambos += 1
                elif not cumple_r:
                    motivo = f"R_eq={req_n:.5f} > {r_max_upme_ohm_km:.4f} Ω/km"
                    resultado.descartes_resistencia += 1
                else:
                    motivo = f"I_prelim={i_prelim_n:.1f} < {i_requerida_a:.1f} A"
                    resultado.descartes_corriente += 1

                resultado.descartes.append(
                    RegistroDescarte(
                        conductor=cond,
                        n_subconductores=n,
                        etapa="filtro_rapido",
                        motivo=motivo,
                        resistencia_eq=req_n,
                        corriente_evaluada=i_prelim_n,
                    )
                )

    return resultado
