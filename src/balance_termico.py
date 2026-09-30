"""Módulo de cálculo de balance térmico y ampacidad bajo norma IEEE Std 738-2012.

Implementa la formulación estática rigurosa para determinar la disipación de calor
por convección (natural y forzada), radiación hacia el entorno y ganancia por radiación solar,
evaluando la capacidad de corriente máxima admisible por subconductor y por haz de fase.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Any, Optional

import numpy as np


@dataclass
class ParametrosAmbientales:
    """Parámetros meteorológicos y ambientales del corredor de transmisión."""

    He: float = 980.0          # Altura sobre el nivel del mar [m]
    Ta: float = 30.0           # Temperatura ambiente de diseño [°C]
    Tc: float = 75.0           # Temperatura máxima de operación del conductor [°C]
    Vw: float = 5.0            # Velocidad de viento transversal de diseño [m/s]
    phi_grados: float = 90.0   # Ángulo viento-conductor [°]
    Qse: float = 4500.0        # Radiación solar incidente global [W/m²]
    alfa: float = 0.5          # Coeficiente de absorción solar (superficie envejecida)
    emisividad: float = 0.5    # Emisividad superficial (superficie envejecida)
    k_aluminio: float = 225.0  # Constante de temperatura del aluminio para corrección de R


@dataclass
class ResultadoBalanceTermico:
    """Resultados detallados del balance térmico según IEEE Std 738-2012."""

    T_film_c: float
    densidad_aire_kg_m3: float
    viscosidad_dinamica_kg_ms: float
    conductividad_termica_w_mk: float
    reynolds: float
    k_angle: float
    resistencia_ac_tc_ohm_m: float
    conveccion_natural_w_m: float
    conveccion_forzada_1_w_m: float
    conveccion_forzada_2_w_m: float
    qc_w_m: float
    qr_w_m: float
    qs_w_m: float
    flujo_neto_disipable_w_m: float
    corriente_admisible_subconductor_A: float
    corriente_fase_A: float
    margen_corriente_norma_A: float
    cumple_criterio_termico: bool
    motivo_descarte: Optional[str] = None


def calcular_balance_termico(
    diametro_exterior_mm: float,
    resistencia_dc_20c_ohm_km: float,
    n_subconductores: int,
    params: ParametrosAmbientales,
    i_requerida_a: float = 2400.0,
    k_material: Optional[float] = None,
) -> ResultadoBalanceTermico:
    """Ejecuta el balance térmico estático bajo IEEE Std 738-2012 para un haz de subconductores.

    Parameters
    ----------
    diametro_exterior_mm : float
        Diámetro exterior real del subconductor en milímetros [mm].
    resistencia_dc_20c_ohm_km : float
        Resistencia óhmica en corriente continua a 20 °C en Ohm/km.
    n_subconductores : int
        Número de subconductores que componen el haz de fase (3 o 4).
    params : ParametrosAmbientales
        Estructura con las condiciones ambientales y térmicas del trazado.
    i_requerida_a : float, optional
        Corriente mínima requerida por fase según norma UPME (defecto: 2400 A).
    k_material : float, optional
        Constante de temperatura del material conductor. Si es None, usa params.k_aluminio.

    Returns
    -------
    ResultadoBalanceTermico
        Contenedor con todas las variables térmicas intermedias y finales calculadas.
    """
    k_mat = k_material if k_material is not None else params.k_aluminio

    # 1. Conversión de unidades a SI
    d = diametro_exterior_mm / 1000.0                 # [m]
    r_dc_20_m = resistencia_dc_20c_ohm_km / 1000.0    # [Ohm/m]

    # 2. Corrección de resistencia a temperatura de operación Tc
    # Rac2 = Rdc20 * ((k + Tc) / (k + 20))
    r_ac2 = r_dc_20_m * ((k_mat + params.Tc) / (k_mat + 20.0))

    # 3. Propiedades del aire a temperatura de película Tfilm = (Tc + Ta) / 2
    t_film = (params.Tc + params.Ta) / 2.0
    t_film_k = t_film + 273.15
    tc_k = params.Tc + 273.15
    ta_k = params.Ta + 273.15

    # Densidad del aire rho_f [kg/m³]
    he = params.He
    rho_f = (1.293 - 1.525e-4 * he + 6.379e-9 * (he**2)) / (1.0 + 0.00367 * t_film)

    # Viscosidad dinámica mu_f [kg/(m·s)]
    mu_f = (1.458e-6 * (t_film_k**1.5)) / (t_film_k + 110.4)

    # Conductividad térmica k_f [W/(m·K)]
    k_f = 2.424e-2 + 7.477e-5 * t_film - 4.407e-9 * (t_film**2)

    # Número de Reynolds
    n_re = (d * rho_f * params.Vw) / mu_f if mu_f > 0 else 0.0

    # Factor de ángulo de incidencia del viento
    phi_rad = math.radians(params.phi_grados)
    k_angle = 1.194 - math.cos(phi_rad) + 0.194 * math.cos(2.0 * phi_rad) + 0.368 * math.sin(2.0 * phi_rad)

    # 4. Pérdidas por convección
    delta_t = max(params.Tc - params.Ta, 0.0)

    # Convección natural qcn [W/m]
    q_cn = 3.645 * (rho_f**0.5) * (d**0.75) * (delta_t**1.25)

    # Convección forzada qc1 y qc2 [W/m]
    q_c1 = (1.01 + 1.35 * (n_re**0.52)) * k_f * k_angle * delta_t
    q_c2 = (0.754 * (n_re**0.6)) * k_f * k_angle * delta_t

    q_c = max(q_cn, q_c1, q_c2)

    # 5. Pérdida por radiación hacia el ambiente qr [W/m]
    q_r = 17.8 * params.emisividad * d * (((tc_k / 100.0)**4) - ((ta_k / 100.0)**4))

    # 6. Ganancia por radiación solar qs [W/m]
    q_s = params.alfa * params.Qse * d

    # 7. Corriente máxima admisible
    flujo_neto = q_c + q_r - q_s

    if flujo_neto <= 0:
        i_ind = 0.0
        i_fase = 0.0
        cumple = False
        motivo = f"Flujo térmico neto disipable no positivo ({flujo_neto:.2f} W/m)"
    else:
        i_ind = math.sqrt(flujo_neto / r_ac2)
        i_fase = float(n_subconductores) * i_ind
        cumple = i_fase >= i_requerida_a
        motivo = None if cumple else f"I_fase={i_fase:.1f} A < {i_requerida_a:.1f} A requerida"

    margen = i_fase - i_requerida_a

    return ResultadoBalanceTermico(
        T_film_c=t_film,
        densidad_aire_kg_m3=rho_f,
        viscosidad_dinamica_kg_ms=mu_f,
        conductividad_termica_w_mk=k_f,
        reynolds=n_re,
        k_angle=k_angle,
        resistencia_ac_tc_ohm_m=r_ac2,
        conveccion_natural_w_m=q_cn,
        conveccion_forzada_1_w_m=q_c1,
        conveccion_forzada_2_w_m=q_c2,
        qc_w_m=q_c,
        qr_w_m=q_r,
        qs_w_m=q_s,
        flujo_neto_disipable_w_m=flujo_neto,
        corriente_admisible_subconductor_A=i_ind,
        corriente_fase_A=i_fase,
        margen_corriente_norma_A=margen,
        cumple_criterio_termico=cumple,
        motivo_descarte=motivo,
    )
