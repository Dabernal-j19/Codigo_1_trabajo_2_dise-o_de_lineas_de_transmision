"""Módulo de exportación de entregables técnicos: Excel, figuras de alta resolución y reporte de auditoría.

Genera los tres entregables normativos exigidos para el proyecto:
1. Consolidado técnico en Excel profesional con hojas de parámetros y resultados.
2. Gráficos de alta resolución (300 DPI) del potencial escalar 2D y perfiles de campo eléctrico.
3. Informe de auditoría y ejecución en texto plano con trazabilidad completa de descartes y cálculos.
"""

from __future__ import annotations

import datetime
import os
import shutil
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # Modo sin interfaz gráfica para ejecución desatendida y servidores
import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm
import numpy as np
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.lector_catalogo import ConductorEntrada, RegistroDescarte
from src.balance_termico import ParametrosAmbientales, ResultadoBalanceTermico
from src.metodo_cargas import ResultadoCSM


@dataclass
class RegistroConductorFinal:
    """Estructura que consolida toda la información técnica de un conductor admisible."""

    conductor: ConductorEntrada
    n_subconductores: int
    balance: ResultadoBalanceTermico
    csm: ResultadoCSM
    veredicto_upme: str = "CUMPLE"


def _aplicar_estilos_encabezado(ws: Any, col_inicio: int, col_fin: int, fila: int = 1) -> None:
    """Aplica formato profesional corporativo a la fila de encabezados."""
    fill_azul = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    font_blanca = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for col in range(col_inicio, col_fin + 1):
        cell = ws.cell(row=fila, column=col)
        cell.fill = fill_azul
        cell.font = font_blanca
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.row_dimensions[fila].height = 32


def _autoajustar_anchos(ws: Any, col_inicio: int, col_fin: int, min_ancho: int = 14) -> None:
    """Ajusta automáticamente los anchos de columna según el contenido."""
    for col in range(col_inicio, col_fin + 1):
        max_len = 0
        for r in range(1, ws.max_row + 1):
            val = str(ws.cell(row=r, column=col).value or "")
            max_len = max(max_len, len(val))
        col_letter = get_column_letter(col)
        ws.column_dimensions[col_letter].width = max(max_len + 4, min_ancho)


def exportar_resultados_excel(
    ruta_salida: str,
    parametros: Dict[str, Any],
    registros: List[RegistroConductorFinal],
) -> None:
    """Genera el libro de cálculo Excel consolidado con pestañas de parámetros y resultados.

    Parameters
    ----------
    ruta_salida : str
        Ruta del archivo Excel principal a crear.
    parametros : dict
        Diccionario con los parámetros ambientales, eléctricos y de modelado.
    registros : list of RegistroConductorFinal
        Lista con los conductores analizados y aprobados.
    """
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    wb = openpyxl.Workbook()

    # -------------------------------------------------------------
    # PESTAÑA 1: Parámetros de Entrada
    # -------------------------------------------------------------
    ws_params = wb.active
    ws_params.title = "Parámetros de Entrada"

    headers_params = [
        "Parámetro",
        "Símbolo",
        "Valor",
        "Unidad",
        "Descripción / Criterio Normativo",
    ]
    ws_params.append(headers_params)

    filas_parametros = [
        ("Tensión Nominal del Sistema", "V_nom", parametros.get("voltaje_sistema_kV", 500.0), "kV", "Línea de Transmisión 500 kV La Virginia - Alférez"),
        ("Tipo de Tensión para CSM", "tipo_V_csm", parametros.get("tipo_voltaje_csm", "fase_tierra"), "Texto", "fase_tierra (500/√3 kV) o fase_fase (500 kV)"),
        ("Capacidad de Corriente Requerida", "I_req", parametros.get("I_requerida_A", 2400.0), "A", "Requerimiento mínimo continuo UPME 04-2014"),
        ("Resistencia Máxima Longitudinal (20°C)", "R_UPME", parametros.get("R_max_UPME_ohm_km", 0.0230), "Ω/km", "Límite superior equivalente por fase UPME 04-2014"),
        ("Separación entre Subconductores", "d_bundle", parametros.get("distancia_haz_mm", 457.2), "mm", "Distancia centro a centro del haz normativo"),
        ("Configuraciones de Haz Evaluadas", "n", str(parametros.get("haces_a_evaluar", [3, 4])), "adimensional", "Haces de 3 y 4 subconductores"),
        ("Altitud Media sobre Nivel del Mar", "He", parametros.get("He", 980.0), "m", "Cota topográfica del trazado La Virginia - Alférez"),
        ("Temperatura Ambiente Máxima de Diseño", "Ta", parametros.get("Ta", 30.0), "°C", "Condición climática crítica del corredor"),
        ("Temperatura Máxima del Conductor", "Tc", parametros.get("Tc", 75.0), "°C", "Límite de operación térmica continua"),
        ("Velocidad de Viento de Diseño", "Vw", parametros.get("Vw", 5.0), "m/s", "Velocidad de viento perpendicular"),
        ("Ángulo Viento-Conductor", "phi", parametros.get("phi_grados", 90.0), "°", "90° = incidencia ortogonal más favorable"),
        ("Radiación Solar Global Incidente", "Qse", parametros.get("Qse", 4500.0), "W/m²", "Radiación solar máxima adoptada"),
        ("Coeficiente de Absorción Solar", "alfa", parametros.get("alfa", 0.5), "adimensional", "Superficie de conductor envejecido"),
        ("Emisividad Superficial", "E", parametros.get("emisividad", 0.5), "adimensional", "Superficie de conductor envejecido"),
        ("Constante Térmica del Conductor (Al)", "k", parametros.get("k_aluminio", 225.0), "°C", "Inverso del coeficiente de resistividad a 0°C"),
        ("Cargas Ficticias por Subconductor", "N_c", parametros.get("cargas_ficticias_por_subconductor", 22), "adimensional", "Discretización angular interna en CSM"),
        ("Relación de Radio de Cargas Internas", "rq/r0", parametros.get("factor_radio_cargas", 0.7), "adimensional", "Posicionamiento radial de cargas ficticias"),
        ("Multiplicador Control Superficie", "M_ctrl", parametros.get("multiplicador_control_superficie", 100), "adimensional", "Puntos de control para cálculo de error superficial"),
        ("Límites de Malla Espacial 2D", "L_malla", str(parametros.get("limites_malla", [-4.0, 4.0, -4.0, 4.0])), "m", "[x_min, x_max, y_min, y_max]"),
        ("Resolución de la Malla Espacial", "Res", parametros.get("resolucion_malla", 500), "puntos", "Matriz 500x500 puntos para V(x,y) y E(x,y)"),
    ]

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )
    font_datos = Font(name="Calibri", size=10)

    for fila in filas_parametros:
        ws_params.append(fila)

    _aplicar_estilos_encabezado(ws_params, 1, len(headers_params), fila=1)

    for r in range(2, ws_params.max_row + 1):
        for c in range(1, len(headers_params) + 1):
            cell = ws_params.cell(row=r, column=c)
            cell.font = font_datos
            cell.border = thin_border
            if c in (1, 2, 5):
                cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")

    _autoajustar_anchos(ws_params, 1, len(headers_params), min_ancho=16)
    ws_params.freeze_panes = "A2"

    # -------------------------------------------------------------
    # PESTAÑA 2: Resultados Técnicos
    # -------------------------------------------------------------
    ws_res = wb.create_sheet(title="Resultados Técnicos")

    headers_res = [
        "Familia de Conductor",
        "Calibre Comercial",
        "Nombre Clave (Code Word)",
        "Haz Evaluado (n)",
        "Diámetro Exterior [mm]",
        "Peso Unitario Conductor [kg/km]",
        "Peso Total Haz por Fase [kg/km]",
        "Carga Rotura Individual [kgf]",
        "Resistencia DC 20°C Individual [Ω/km]",
        "Resistencia Equivalente Haz 20°C [Ω/km]",
        "Convección Disipada qc [W/m]",
        "Radiación Disipada qr [W/m]",
        "Ganancia Solar qs [W/m]",
        "Corriente Admisible Subconductor I_ind [A]",
        "Corriente Total del Haz I_fase [A]",
        "Margen Corriente s/Norma [A]",
        "Error Medio Superficie CSM [%]",
        "Campo Eléctrico Superficial Máx [kV/cm]",
        "Campo Eléctrico Superficial Máx [kV/m]",
        "Veredicto UPME",
    ]
    ws_res.append(headers_res)

    for reg in registros:
        c = reg.conductor
        b = reg.balance
        csm = reg.csm
        n = reg.n_subconductores

        peso_unit = c.peso_kg_km if c.peso_kg_km is not None else "N/A"
        peso_haz = (c.peso_kg_km * n) if c.peso_kg_km is not None else "N/A"
        rotura = c.carga_rotura_kgf if c.carga_rotura_kgf is not None else "N/A"
        req_20 = c.resistencia_dc_20c_ohm_km / float(n)

        fila_dato = [
            c.tipo_conductor,
            c.calibre,
            c.nombre_clave,
            n,
            round(c.diametro_exterior_mm, 2),
            round(peso_unit, 2) if isinstance(peso_unit, (int, float)) else peso_unit,
            round(peso_haz, 2) if isinstance(peso_haz, (int, float)) else peso_haz,
            round(rotura, 1) if isinstance(rotura, (int, float)) else rotura,
            round(c.resistencia_dc_20c_ohm_km, 5),
            round(req_20, 5),
            round(b.qc_w_m, 2),
            round(b.qr_w_m, 2),
            round(b.qs_w_m, 2),
            round(b.corriente_admisible_subconductor_A, 2),
            round(b.corriente_fase_A, 2),
            round(b.margen_corriente_norma_A, 2),
            round(csm.error_medio_superficie_pct, 4),
            round(csm.e_max_superficie_kv_cm, 3),
            round(csm.e_max_superficie_kv_m, 2),
            reg.veredicto_upme,
        ]
        ws_res.append(fila_dato)

    _aplicar_estilos_encabezado(ws_res, 1, len(headers_res), fila=1)

    fill_verde = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    font_verde = Font(name="Calibri", size=10, bold=True, color="375623")

    for r in range(2, ws_res.max_row + 1):
        for col_idx in range(1, len(headers_res) + 1):
            cell = ws_res.cell(row=r, column=col_idx)
            cell.font = font_datos
            cell.border = thin_border
            if col_idx in (1, 2, 3):
                cell.alignment = Alignment(horizontal="left", vertical="center")
            elif col_idx in (4, 20):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="right", vertical="center")

            # Estilo especial para la columna de veredicto
            if col_idx == 20 and str(cell.value) == "CUMPLE":
                cell.fill = fill_verde
                cell.font = font_verde

    _autoajustar_anchos(ws_res, 1, len(headers_res), min_ancho=13)
    ws_res.freeze_panes = "A2"

    wb.save(ruta_salida)


def exportar_figuras(
    carpeta_salida: str,
    registros: List[RegistroConductorFinal],
    dpi: int = 300,
) -> List[str]:
    """Genera las figuras de potencial 2D y perfiles transversales de campo eléctrico.

    Parameters
    ----------
    carpeta_salida : str
        Directorio donde se guardarán las imágenes generadas.
    registros : list of RegistroConductorFinal
        Lista de conductores admisibles simulados.
    dpi : int, optional
        Resolución de exportación de las figuras (defecto: 300 DPI).

    Returns
    -------
    list of str
        Rutas de todos los archivos de imagen creados.
    """
    os.makedirs(carpeta_salida, exist_ok=True)
    rutas_generadas: List[str] = []

    # 1. Figuras individuales de potencial escalar 2D y perfil de campo
    for reg in registros:
        c = reg.conductor
        csm = reg.csm
        n = reg.n_subconductores
        clave_segura = "".join(ch if ch.isalnum() else "_" for ch in c.nombre_clave).strip("_")
        nombre_base = f"{c.tipo_conductor.lower()}_{clave_segura}_n{n}"

        # --- FIGURA 1: Potencial Escalar 2D ---
        fig, ax = plt.subplots(figsize=(8, 7), dpi=dpi)

        # Mapa de contorno con PowerNorm(gamma=0.5) y cmap 'jet'
        v_min = float(np.min(csm.V_malla))
        v_max = float(np.max(csm.V_malla))
        v_min_norm = max(v_min, 1e-3)

        norm = PowerNorm(gamma=0.5, vmin=v_min_norm, vmax=v_max)
        levels = np.linspace(v_min_norm, v_max, 60)

        cf = ax.contourf(
            csm.X_malla,
            csm.Y_malla,
            np.clip(csm.V_malla, v_min_norm, None),
            levels=levels,
            cmap="jet",
            norm=norm,
            extend="both",
        )
        cbar = fig.colorbar(cf, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Potencial Escalar Eléctrico [V]", fontsize=11, fontweight="bold")
        cbar.ax.tick_params(labelsize=9)

        # Dibujar contornos circulares de cada subconductor
        for idx_c, centro in enumerate(csm.centros_conductores):
            circulo = plt.Circle(
                (centro[0], centro[1]),
                csm.radio_conductor_m,
                color="black",
                fill=False,
                linestyle="--",
                linewidth=1.5,
                label="Borde Subconductor" if idx_c == 0 else None,
            )
            ax.add_patch(circulo)

        ax.set_aspect("equal")
        ax.set_xlabel("Coordenada X [m]", fontsize=11, fontweight="bold")
        ax.set_ylabel("Coordenada Y [m]", fontsize=11, fontweight="bold")
        v_kv = round(csm.voltaje_nominal_v / 1000.0, 1)
        ax.set_title(
            f"Distribución de Potencial Escalar Eléctrico (CSM)\n"
            f"Conductor {c.tipo_conductor} {c.calibre} ({c.nombre_clave}) | Haz n={n} | V={v_kv} kV",
            fontsize=12,
            fontweight="bold",
            pad=12,
        )
        ax.grid(True, linestyle=":", alpha=0.6)

        # Zoom centrado en los subconductores para apreciación detallada
        zoom_lim = max(csm.distancia_haz_m * 1.5, 0.6)
        ax.set_xlim(-zoom_lim, zoom_lim)
        ax.set_ylim(-zoom_lim, zoom_lim)
        ax.legend(loc="upper right", fontsize=9)

        fig.tight_layout()
        ruta_pot = os.path.join(carpeta_salida, f"potencial_{nombre_base}.png")
        fig.savefig(ruta_pot, dpi=dpi)
        plt.close(fig)
        rutas_generadas.append(ruta_pot)

        # --- FIGURA 2: Perfil Transversal de Campo Eléctrico ---
        fig_e, ax_e = plt.subplots(figsize=(8, 5), dpi=dpi)
        # Convertir E a kV/m
        e_kv_m = csm.E_trayectoria / 1000.0

        ax_e.plot(
            csm.x_trayectoria,
            e_kv_m,
            color="#C00000",
            linewidth=2.0,
            label=f"|E| Haz n={n} ({c.nombre_clave})",
        )
        ax_e.set_xlabel("Distancia Radial Horizontal x [m]", fontsize=11, fontweight="bold")
        ax_e.set_ylabel("Intensidad de Campo Eléctrico |E| [kV/m]", fontsize=11, fontweight="bold")
        ax_e.set_title(
            f"Perfil Transversal de Campo Eléctrico (Atenuación Lateral)\n"
            f"{c.tipo_conductor} {c.calibre} ({c.nombre_clave}) - Haz {n}x{round(c.diametro_exterior_mm, 1)} mm",
            fontsize=12,
            fontweight="bold",
            pad=12,
        )
        ax_e.grid(True, linestyle=":", alpha=0.6)
        ax_e.legend(loc="upper right", fontsize=10)
        fig_e.tight_layout()

        ruta_perfil = os.path.join(carpeta_salida, f"campo_e_perfil_{nombre_base}.png")
        fig_e.savefig(ruta_perfil, dpi=dpi)
        plt.close(fig_e)
        rutas_generadas.append(ruta_perfil)

    # --- FIGURA 3: Superposición Comparativa de Perfiles de Campo ---
    if len(registros) > 1:
        fig_sup, ax_sup = plt.subplots(figsize=(10, 6), dpi=dpi)
        colores = ["#1F4E79", "#C00000", "#2CA02C", "#FF7F0E", "#9467BD", "#8C564B", "#E377C2", "#17BECF"]

        for idx, reg in enumerate(registros[:8]):
            c = reg.conductor
            csm = reg.csm
            n = reg.n_subconductores
            color = colores[idx % len(colores)]
            ax_sup.plot(
                csm.x_trayectoria,
                csm.E_trayectoria / 1000.0,
                label=f"{c.tipo_conductor} {c.calibre} ({c.nombre_clave}) n={n}",
                linewidth=1.8,
                color=color,
            )

        ax_sup.set_xlabel("Distancia Lateral Horizontal x [m]", fontsize=11, fontweight="bold")
        ax_sup.set_ylabel("Campo Eléctrico |E| [kV/m]", fontsize=11, fontweight="bold")
        ax_sup.set_title(
            "Superposición Comparativa de Atenuación Lateral de Campo Eléctrico\n"
            "Conductores Candidatos Admisibles - Línea 500 kV",
            fontsize=12,
            fontweight="bold",
            pad=12,
        )
        ax_sup.grid(True, linestyle=":", alpha=0.6)
        ax_sup.legend(loc="upper right", fontsize=9)
        fig_sup.tight_layout()

        ruta_sup = os.path.join(carpeta_salida, "superposicion_perfil_campo_e.png")
        fig_sup.savefig(ruta_sup, dpi=dpi)
        plt.close(fig_sup)
        rutas_generadas.append(ruta_sup)

    return rutas_generadas


def exportar_reporte_auditoria(
    ruta_salida: str,
    parametros: Dict[str, Any],
    total_leidos: int,
    descartes_preliminares: List[RegistroDescarte],
    descartes_resistencia: int,
    descartes_corriente: int,
    descartes_ambos: int,
    evaluados_ieee: int,
    descartes_termicos: List[RegistroDescarte],
    registros_finales: List[RegistroConductorFinal],
    tiempo_ejecucion_s: float,
    advertencias: List[str],
) -> None:
    """Genera la bitácora técnica de auditoría y ejecución en formato de texto plano.

    Parameters
    ----------
    ruta_salida : str
        Ruta del archivo de texto a crear.
    parametros : dict
        Parámetros de configuración utilizados.
    total_leidos : int
        Cantidad total de conductores en el catálogo.
    descartes_preliminares : list of RegistroDescarte
        Registros descartados en el filtro rápido inicial.
    descartes_resistencia : int
        Cantidad de descartes por resistencia en filtro inicial.
    descartes_corriente : int
        Cantidad de descartes por corriente en filtro inicial.
    descartes_ambos : int
        Cantidad de descartes por ambas causas en filtro inicial.
    evaluados_ieee : int
        Cantidad de conductores-haz procesados bajo IEEE 738.
    descartes_termicos : list of RegistroDescarte
        Registros que no alcanzaron la capacidad térmica de 2400 A.
    registros_finales : list of RegistroConductorFinal
        Conductores finales aprobados y simulados con CSM.
    tiempo_ejecucion_s : float
        Tiempo total transcurrido en la ejecución.
    advertencias : list of str
        Lista de advertencias emitidas durante el flujo.
    ruta_alternativa : str, optional
        Ruta adicional para duplicar el archivo.
    """
    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lineas: List[str] = []
    lineas.append("=" * 80)
    lineas.append("INFORME TÉCNICO DE AUDITORÍA Y EJECUCIÓN DEL SISTEMA")
    lineas.append("PROYECTO SELECCIÓN DE CONDUCTORES Y SIMULACIÓN ELECTROSTÁTICA (500 kV)")
    lineas.append("LÍNEA DE TRANSMISIÓN SUBESTACIÓN LA VIRGINIA - SUBESTACIÓN ALFÉREZ")
    lineas.append("=" * 80)
    lineas.append(f"Fecha y Hora de Ejecución : {ahora}")
    lineas.append(f"Tiempo Total de Cómputo   : {tiempo_ejecucion_s:.2f} segundos")
    lineas.append("")

    lineas.append("-" * 80)
    lineas.append("1. PARÁMETROS DE DISEÑO Y AMBIENTALES UTILIZADOS")
    lineas.append("-" * 80)
    for k, v in parametros.items():
        lineas.append(f"  * {k:<34} : {v}")
    lineas.append("")

    lineas.append("-" * 80)
    lineas.append("2. RESUMEN ESTADÍSTICO DEL PROCESAMIENTO")
    lineas.append("-" * 80)
    lineas.append(f"  * Total de registros leídos en catálogo       : {total_leidos}")
    haces = parametros.get("haces_a_evaluar", [3, 4])
    total_evaluaciones_posibles = total_leidos * len(haces)
    lineas.append(f"  * Evaluaciones combinadas (conductor-haz)    : {total_evaluaciones_posibles}")
    lineas.append(f"  * Descartados en Filtro Rápido Preliminar    : {len(descartes_preliminares)}")
    lineas.append(f"      - Descarte exclusivo por Resistencia (R_eq > {parametros.get('R_max_UPME_ohm_km', 0.023):.4f} Ω/km) : {descartes_resistencia}")
    lineas.append(f"      - Descarte exclusivo por Corriente (I_prelim < {parametros.get('I_requerida_A', 2400):.0f} A)       : {descartes_corriente}")
    lineas.append(f"      - Descarte por ambas restricciones técnicas                        : {descartes_ambos}")
    lineas.append(f"  * Candidatos analizados con IEEE Std 738-2012 : {evaluados_ieee}")
    lineas.append(f"  * Descartados por Límite Térmico (I_fase < 2400 A) : {len(descartes_termicos)}")
    lineas.append(f"  * Simulaciones Electrostáticas CSM Exitosas   : {len(registros_finales)}")
    lineas.append("")

    if advertencias:
        lineas.append("-" * 80)
        lineas.append("3. ADVERTENCIAS Y NOTAS DE PROCESAMIENTO")
        lineas.append("-" * 80)
        for adv in advertencias:
            lineas.append(f"  [ADVERTENCIA] {adv}")
        lineas.append("")

    lineas.append("-" * 80)
    lineas.append("4. CONDUCTORES QUE CUMPLEN LA NORMATIVA UPME (SELECCIÓN FINAL)")
    lineas.append("-" * 80)
    encabezado_tabla = (
        f"{'Tipo':<6} {'Calibre':<18} {'Code Word':<16} {'Haz':<4} "
        f"{'Diam[mm]':<9} {'Req[Ω/km]':<11} {'Ifase[A]':<10} {'Margen[A]':<10} "
        f"{'ErrCSM[%]':<10} {'Emax[kV/cm]':<12} {'Veredicto':<10}"
    )
    lineas.append(encabezado_tabla)
    lineas.append("-" * len(encabezado_tabla))

    # Ordenar por margen de corriente descendente
    registros_ordenados = sorted(
        registros_finales,
        key=lambda r: r.balance.margen_corriente_norma_A,
        reverse=True,
    )

    for reg in registros_ordenados:
        c = reg.conductor
        b = reg.balance
        csm = reg.csm
        req_20 = c.resistencia_dc_20c_ohm_km / float(reg.n_subconductores)
        lineas.append(
            f"{c.tipo_conductor:<6} {c.calibre:<18} {c.nombre_clave:<16} {reg.n_subconductores:<4} "
            f"{c.diametro_exterior_mm:<9.2f} {req_20:<11.5f} {b.corriente_fase_A:<10.1f} "
            f"{b.margen_corriente_norma_A:<10.1f} {csm.error_medio_superficie_pct:<10.4f} "
            f"{csm.e_max_superficie_kv_cm:<12.3f} {reg.veredicto_upme:<10}"
        )
    lineas.append("")

    lineas.append("-" * 80)
    lineas.append("5. REGISTRO DETALLADO DE CONDUCTORES DESCARTADOS EN FILTRO PREVIO")
    lineas.append("-" * 80)
    lineas.append(f"{'Fila':<5} {'Tipo':<6} {'Calibre':<18} {'Code Word':<16} {'Haz':<4} {'Causa del Descarte'}")
    lineas.append("-" * 80)
    for desc in descartes_preliminares:
        c = desc.conductor
        lineas.append(
            f"{c.fila_origen:<5} {c.tipo_conductor:<6} {c.calibre:<18} {c.nombre_clave:<16} {desc.n_subconductores:<4} {desc.motivo}"
        )
    lineas.append("")

    if descartes_termicos:
        lineas.append("-" * 80)
        lineas.append("6. REGISTRO DE DESCARTES EN ETAPA DE BALANCE TÉRMICO (IEEE 738)")
        lineas.append("-" * 80)
        for desc in descartes_termicos:
            c = desc.conductor
            lineas.append(
                f"  * {c.tipo_conductor} {c.calibre} ({c.nombre_clave}) Haz n={desc.n_subconductores}: {desc.motivo}"
            )
        lineas.append("")

    lineas.append("=" * 80)
    lineas.append("FIN DEL REPORTE DE AUDITORÍA")
    lineas.append("=" * 80)

    contenido = "\n".join(lineas)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(contenido)
