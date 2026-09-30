"""Orquestador principal del Sistema Modular de Selección de Conductores y Simulación Electrostática (500 kV).

Ejecuta el flujo completo de ingeniería:
1. Carga de parámetros configurables (ambientales, eléctricos y numéricos).
2. Lectura y validación del catálogo estándar en Excel.
3. Filtro preliminar de resistencia equivalente UPME (R_eq <= 0.0230 Ohm/km) y corriente nominal preliminar.
4. Balance térmico riguroso bajo norma IEEE Std 738-2012 y verificación de ampacidad crítica (I_fase >= 2400 A).
5. Simulación electrostática mediante el Método de Simulación de Cargas (CSM), error de contorno y campos eléctricos.
6. Exportación de libro Excel consolidado, gráficos de alta resolución (300 DPI) y bitácora de auditoría.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List

# Garantizar que el directorio raíz del proyecto esté en el PYTHONPATH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.lector_catalogo import (
    CandidatoHaz,
    ConductorEntrada,
    RegistroDescarte,
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
    exportar_figuras,
    exportar_reporte_auditoria,
    exportar_resultados_excel,
)


def resolver_ruta(ruta: Optional[str], base: str = BASE_DIR) -> Optional[str]:
    """Resuelve una ruta relativa con respecto al directorio de trabajo o a la raíz del proyecto."""
    if not ruta:
        return None
    if os.path.isabs(ruta):
        return ruta
    # 1. Si existe relativo al directorio de trabajo actual (CWD)
    if os.path.exists(ruta):
        return os.path.abspath(ruta)
    # 2. Si no, resolver relativo a BASE_DIR
    return os.path.normpath(os.path.join(base, ruta))


def ruta_relativa_amigable(ruta: str, base: str = BASE_DIR) -> str:
    """Devuelve una representación de ruta relativa limpia y portable para visualización."""
    try:
        rel = os.path.relpath(ruta, start=os.getcwd())
        if rel.count("..") > 2:
            rel = os.path.relpath(ruta, start=base)
        return rel.replace("\\", "/")
    except Exception:
        return ruta.replace("\\", "/")


def cargar_configuracion(ruta_config: Optional[str] = None) -> Dict[str, Any]:
    """Carga los parámetros del archivo JSON de configuración.

    Parameters
    ----------
    ruta_config : str, optional
        Ruta personalizada al archivo de configuración. Si es None, busca en config/.

    Returns
    -------
    dict
        Diccionario con las variables de configuración.
    """
    if ruta_config:
        path_usado = resolver_ruta(ruta_config)
        if not path_usado or not os.path.exists(path_usado):
            raise FileNotFoundError(f"No se encontró el archivo de configuración en: '{ruta_config}'")
    else:
        path_usado = os.path.join(BASE_DIR, "config", "parametros_entrada.json")
        if not os.path.exists(path_usado):
            raise FileNotFoundError(f"No se encontró el archivo de parámetros en: '{path_usado}'")

    with open(path_usado, "r", encoding="utf-8") as f:
        config = json.load(f)

    return config


def main() -> int:
    """Punto de entrada principal para la ejecución de la herramienta."""
    parser = argparse.ArgumentParser(
        description="Sistema Modular de Selección de Conductores y Simulación Electrostática (500 kV)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Ruta al archivo JSON de parámetros de configuración (relativa o absoluta).",
    )
    parser.add_argument(
        "--catalogo",
        type=str,
        default="catalogos/plantilla_catalogo_conductores.xlsx",
        help="Ruta al archivo Excel de la plantilla de conductores (relativa o absoluta).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directorio de destino para reportes y figuras (relativo o absoluto).",
    )
    parser.add_argument(
        "--sin-figuras",
        action="store_true",
        help="Si se especifica, omite la generación de gráficos PNG para acelerar la corrida.",
    )

    args = parser.parse_args()

    ruta_catalogo = resolver_ruta(args.catalogo)
    dir_output = resolver_ruta(args.output_dir)

    t_inicio = time.time()
    print("=" * 80)
    print("SISTEMA MODULAR DE SELECCIÓN DE CONDUCTORES Y SIMULACIÓN ELECTROSTÁTICA (500 kV)")
    print("Línea de Transmisión: S/E La Virginia - S/E Alférez | Criterio UPME 04-2014")
    print("=" * 80)

    # 1. Cargar Configuración
    try:
        cfg = cargar_configuracion(args.config)
        print(f"[1/5] Configuración cargada exitosamente.")
    except Exception as exc:
        print(f"[ERROR] Falla al cargar configuración: {exc}", file=sys.stderr)
        return 1

    r_max_upme = float(cfg.get("R_max_UPME_ohm_km", 0.0230))
    i_req = float(cfg.get("I_requerida_A", 2400.0))
    haces_evaluar = list(cfg.get("haces_a_evaluar", [3, 4]))
    dist_bundle_m = float(cfg.get("distancia_haz_mm", 457.2)) / 1000.0
    v_sistema_kv = float(cfg.get("voltaje_sistema_kV", 500.0))
    tipo_v = str(cfg.get("tipo_voltaje_csm", "fase_tierra")).strip().lower()

    # Cálculo del voltaje a aplicar en CSM
    if tipo_v in ("fase_tierra", "fase-tierra", "fn", "fase_neutro"):
        voltaje_csm_v = (v_sistema_kv * 1000.0) / (3.0**0.5)
        desc_v = f"{v_sistema_kv}/sqrt(3) kV = {voltaje_csm_v/1000.0:.2f} kV (Fase-Tierra)"
    else:
        voltaje_csm_v = v_sistema_kv * 1000.0
        desc_v = f"{v_sistema_kv} kV (Fase-Fase)"

    params_amb = ParametrosAmbientales(
        He=float(cfg.get("He", 980.0)),
        Ta=float(cfg.get("Ta", 30.0)),
        Tc=float(cfg.get("Tc", 75.0)),
        Vw=float(cfg.get("Vw", 5.0)),
        phi_grados=float(cfg.get("phi_grados", 90.0)),
        Qse=float(cfg.get("Qse", 4500.0)),
        alfa=float(cfg.get("alfa", 0.5)),
        emisividad=float(cfg.get("emisividad", 0.5)),
        k_aluminio=float(cfg.get("k_aluminio", 225.0)),
    )

    # 2. Cargar Catálogo y Filtro Rápido
    print(f"[2/5] Leyendo catálogo ('{ruta_relativa_amigable(ruta_catalogo)}') y ejecutando filtro preliminar...")
    try:
        res_lectura = leer_y_filtrar_catalogo(
            ruta_archivo=ruta_catalogo,
            haces_a_evaluar=haces_evaluar,
            r_max_upme_ohm_km=r_max_upme,
            i_requerida_a=i_req,
        )
    except Exception as exc:
        print(f"[ERROR] Error al procesar catálogo: {exc}", file=sys.stderr)
        return 1

    total_leidos = res_lectura.total_conductores_leidos
    candidatos_filtro = res_lectura.candidatos_admitidos
    descartes_filtro = res_lectura.descartes

    print(
        f"      * Total de conductores leídos: {total_leidos}\n"
        f"      * Evaluaciones haz ({haces_evaluar}): {total_leidos * len(haces_evaluar)}\n"
        f"      * Descartes en filtro preliminar: {len(descartes_filtro)}\n"
        f"      * Candidatos admitidos a balance térmico: {len(candidatos_filtro)}"
    )

    # 3. Balance Térmico IEEE Std 738-2012
    print(f"[3/5] Calculando balance térmico estático IEEE Std 738-2012...")
    candidatos_aprobados_termico: List[Tuple[CandidatoHaz, ResultadoBalanceTermico]] = []
    descartes_termicos: List[RegistroDescarte] = []

    for cand in candidatos_filtro:
        cond = cand.conductor
        n = cand.n_subconductores
        bal = calcular_balance_termico(
            diametro_exterior_mm=cond.diametro_exterior_mm,
            resistencia_dc_20c_ohm_km=cond.resistencia_dc_20c_ohm_km,
            n_subconductores=n,
            params=params_amb,
            i_requerida_a=i_req,
        )
        if bal.cumple_criterio_termico:
            candidatos_aprobados_termico.append((cand, bal))
        else:
            descartes_termicos.append(
                RegistroDescarte(
                    conductor=cond,
                    n_subconductores=n,
                    etapa="balance_termico",
                    motivo=bal.motivo_descarte or f"I_fase={bal.corriente_fase_A:.1f} A < {i_req} A",
                    resistencia_eq=cond.resistencia_dc_20c_ohm_km / float(n),
                    corriente_evaluada=bal.corriente_fase_A,
                )
            )

    print(
        f"      * Evaluados con IEEE 738: {len(candidatos_filtro)}\n"
        f"      * Descartados por ampacidad térmica: {len(descartes_termicos)}\n"
        f"      * Candidatos que cumplen criterio térmico (I >= {i_req:.0f} A): {len(candidatos_aprobados_termico)}"
    )

    # 4. Simulación Electrostática por Método de Simulación de Cargas (CSM)
    print(f"[4/5] Ejecutando simulación electrostática (CSM)...")
    print(f"      * Tensión aplicada: {desc_v}")
    print(f"      * Separación de haz: {dist_bundle_m*1000:.1f} mm")

    n_cargas = int(cfg.get("cargas_ficticias_por_subconductor", 22))
    factor_rq = float(cfg.get("factor_radio_cargas", 0.7))
    mult_ctrl = int(cfg.get("multiplicador_control_superficie", 100))
    limites_malla = tuple(cfg.get("limites_malla", [-4.0, 4.0, -4.0, 4.0]))
    res_malla = int(cfg.get("resolucion_malla", 500))
    dpi_fig = int(cfg.get("dpi_figuras", 300))

    registros_finales: List[RegistroConductorFinal] = []

    for cand, bal in candidatos_aprobados_termico:
        cond = cand.conductor
        n = cand.n_subconductores
        r_cond_m = cond.radio_m

        try:
            res_csm = simular_csm(
                n_subconductores=n,
                distancia_haz_m=dist_bundle_m,
                radio_conductor_m=r_cond_m,
                voltaje_nominal_v=voltaje_csm_v,
                n_cargas_por_subconductor=n_cargas,
                factor_radio_cargas=factor_rq,
                multiplicador_control_superficie=mult_ctrl,
                limites_malla=limites_malla,
                resolucion_malla=res_malla,
            )
            registros_finales.append(
                RegistroConductorFinal(
                    conductor=cond,
                    n_subconductores=n,
                    balance=bal,
                    csm=res_csm,
                    veredicto_upme="CUMPLE",
                )
            )
        except Exception as exc:
            print(
                f"[WARN] Error en CSM para {cond.calibre} ({cond.nombre_clave}) n={n}: {exc}",
                file=sys.stderr,
            )
            res_lectura.advertencias.append(
                f"Falla en simulación CSM para {cond.calibre} {cond.nombre_clave} n={n}: {exc}"
            )

    print(f"      * Simulaciones CSM completadas exitosamente: {len(registros_finales)}")

    # 5. Exportación de Entregables
    print(f"[5/5] Exportando entregables técnicos a '{ruta_relativa_amigable(dir_output)}'...")
    os.makedirs(dir_output, exist_ok=True)
    dir_figuras = os.path.join(dir_output, "figuras_potencial")

    # Exportar Excel de resultados
    ruta_excel = os.path.join(dir_output, "resultados_conductores.xlsx")
    exportar_resultados_excel(
        ruta_salida=ruta_excel,
        parametros=cfg,
        registros=registros_finales,
    )
    print(f"      [OK] Archivo Excel guardado en: {ruta_relativa_amigable(ruta_excel)}")

    # Exportar Figuras
    if not args.sin_figuras and registros_finales:
        rutas_imgs = exportar_figuras(
            carpeta_salida=dir_figuras,
            registros=registros_finales,
            dpi=dpi_fig,
        )
        print(f"      [OK] {len(rutas_imgs)} imágenes generadas en: {ruta_relativa_amigable(dir_figuras)}")
    else:
        print(f"      [INFO] Generación de figuras omitida.")

    t_total = time.time() - t_inicio

    # Exportar Reporte de Ejecución y Auditoría
    ruta_reporte = os.path.join(dir_output, "reporte_ejecucion.txt")
    exportar_reporte_auditoria(
        ruta_salida=ruta_reporte,
        parametros=cfg,
        total_leidos=total_leidos,
        descartes_preliminares=descartes_filtro,
        descartes_resistencia=res_lectura.descartes_resistencia,
        descartes_corriente=res_lectura.descartes_corriente,
        descartes_ambos=res_lectura.descartes_ambos,
        evaluados_ieee=len(candidatos_filtro),
        descartes_termicos=descartes_termicos,
        registros_finales=registros_finales,
        tiempo_ejecucion_s=t_total,
        advertencias=res_lectura.advertencias,
    )
    print(f"      [OK] Reporte de ejecución escrito en: {ruta_relativa_amigable(ruta_reporte)}")

    # Resumen Ejecutivo en Consola
    print("\n" + "=" * 80)
    print("RESUMEN EJECUTIVO - CONDUCTORES SELECCIONADOS QUE CUMPLEN UPME 04-2014")
    print("=" * 80)
    print(
        f"{'Tipo':<6} {'Calibre':<18} {'Code Word':<16} {'Haz':<4} "
        f"{'Req[Ohm/km]':<11} {'Ifase[A]':<10} {'Margen[A]':<10} "
        f"{'ErrCSM[%]':<10} {'Emax[kV/cm]':<12} {'Veredicto':<10}"
    )
    print("-" * 105)

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
        print(
            f"{c.tipo_conductor:<6} {c.calibre:<18} {c.nombre_clave:<16} {reg.n_subconductores:<4} "
            f"{req_20:<11.5f} {b.corriente_fase_A:<10.1f} {b.margen_corriente_norma_A:<10.1f} "
            f"{csm.error_medio_superficie_pct:<10.4f} {csm.e_max_superficie_kv_cm:<12.3f} {reg.veredicto_upme:<10}"
        )
    print("=" * 80)
    print(f"TIEMPO TOTAL DE EJECUCIÓN: {t_total:.2f} segundos")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
