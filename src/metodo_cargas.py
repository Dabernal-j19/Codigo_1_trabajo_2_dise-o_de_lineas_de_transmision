"""Módulo de simulación electrostática mediante el Método de Simulación de Cargas (CSM).

Calcula la distribución de cargas ficticias internas para satisfacer la condición de contorno
de potencial constante en la superficie de subconductores en haz (500 kV), evalúa el error
de ajuste en el contorno y genera la distribución bidimensional del potencial escalar V(x, y)
y el campo eléctrico E(x, y) mediante gradiente numérico y evaluación analítica en superficie.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from config.geometrias import centros_haz


@dataclass
class ResultadoCSM:
    """Contenedor de resultados de la simulación electrostática por CSM."""

    n_subconductores: int
    distancia_haz_m: float
    radio_conductor_m: float
    voltaje_nominal_v: float
    centros_conductores: np.ndarray      # Forma (n, 2)
    cargas_coords: np.ndarray            # Forma (M, 2)
    contornos_coords: np.ndarray         # Forma (M, 2)
    cargas_q: np.ndarray                 # Forma (M,)
    error_medio_superficie_pct: float    # Error porcentual relativo medio en contorno [%]
    error_max_superficie_pct: float      # Error porcentual relativo máximo [%]
    error_absoluto_medio_v: float        # Error absoluto medio [V]
    e_max_superficie_kv_cm: float        # Campo eléctrico superficial máximo [kV/cm]
    e_max_superficie_kv_m: float         # Campo eléctrico superficial máximo [kV/m]
    x_eje: np.ndarray                    # Vector 1D de coordenadas x [m]
    y_eje: np.ndarray                    # Vector 1D de coordenadas y [m]
    X_malla: np.ndarray                  # Malla 2D X [m]
    Y_malla: np.ndarray                  # Malla 2D Y [m]
    V_malla: np.ndarray                  # Potencial escalar 2D [V]
    E_malla: np.ndarray                  # Magnitud de campo eléctrico 2D [V/m]
    x_trayectoria: np.ndarray            # Coordenadas x del perfil transversal [m]
    E_trayectoria: np.ndarray            # Magnitud de E en perfil transversal [V/m]


def simular_csm(
    n_subconductores: int,
    distancia_haz_m: float,
    radio_conductor_m: float,
    voltaje_nominal_v: float,
    n_cargas_por_subconductor: int = 22,
    factor_radio_cargas: float = 0.7,
    multiplicador_control_superficie: int = 100,
    limites_malla: Tuple[float, float, float, float] = (-4.0, 4.0, -4.0, 4.0),
    resolucion_malla: int = 500,
    epsilon0: float = 8.8541878128e-12,
    chunk_malla: int = 50000,
) -> ResultadoCSM:
    """Ejecuta la simulación electrostática completa por Simulación de Cargas.

    Parameters
    ----------
    n_subconductores : int
        Número de subconductores del haz (3 o 4).
    distancia_haz_m : float
        Separación centro a centro del haz [m].
    radio_conductor_m : float
        Radio exterior del subconductor [m].
    voltaje_nominal_v : float
        Potencial eléctrico impuesto a los conductores [V].
    n_cargas_por_subconductor : int, optional
        Número de cargas filiformes ficticias por subconductor (defecto: 22).
    factor_radio_cargas : float, optional
        Relación entre el radio de las cargas internas y el radio exterior (defecto: 0.7).
    multiplicador_control_superficie : int, optional
        Multiplicador para la densidad de puntos de control de error en superficie (defecto: 100).
    limites_malla : tuple of float, optional
        Límites espaciales (x_min, x_max, y_min, y_max) en metros (defecto: (-4, 4, -4, 4)).
    resolucion_malla : int, optional
        Número de puntos por eje en la discretización de la ventana 2D (defecto: 500).
    epsilon0 : float, optional
        Permitividad dieléctrica del vacío [F/m] (defecto: 8.8541878128e-12).
    chunk_malla : int, optional
        Tamaño de bloque para evaluación vectorizada de la malla (defecto: 50000).

    Returns
    -------
    ResultadoCSM
        Estructura completa con cargas calculadas, errores, malla 2D y campos eléctricos.

    Raises
    ------
    ValueError
        Si los parámetros geométricos o de mallado son incongruentes.
    np.linalg.LinAlgError
        Si la matriz de coeficientes de potencial es singular.
    """
    if radio_conductor_m <= 0:
        raise ValueError(f"El radio del conductor debe ser positivo: {radio_conductor_m} m.")
    if distancia_haz_m <= 0:
        raise ValueError(f"La distancia del haz debe ser positiva: {distancia_haz_m} m.")

    # 1. Posicionamiento de los centros del haz
    centros = centros_haz(n_subconductores, distancia_haz_m)

    # 2. Generación de cargas ficticias y puntos de contorno
    angulos = np.linspace(0.0, 2.0 * np.pi, n_cargas_por_subconductor, endpoint=False)
    r_carga = factor_radio_cargas * radio_conductor_m

    lista_cargas = []
    lista_contornos = []

    for xc, yc in centros:
        cargas_k = np.column_stack(
            (xc + r_carga * np.cos(angulos), yc + r_carga * np.sin(angulos))
        )
        contorno_k = np.column_stack(
            (xc + radio_conductor_m * np.cos(angulos), yc + radio_conductor_m * np.sin(angulos))
        )
        lista_cargas.append(cargas_k)
        lista_contornos.append(contorno_k)

    cargas_arr = np.vstack(lista_cargas)        # Forma (M, 2)
    contornos_arr = np.vstack(lista_contornos)  # Forma (M, 2)
    m_total = len(cargas_arr)

    # 3. Construcción vectorizada de la matriz de coeficientes de potencial P
    diff_p = contornos_arr[:, np.newaxis, :] - cargas_arr[np.newaxis, :, :]  # (M, M, 2)
    dist_p = np.linalg.norm(diff_p, axis=2)                                  # (M, M)

    # Prevenir divisiones por cero accidentales
    dist_p = np.maximum(dist_p, 1e-12)
    matriz_p = 1.0 / (4.0 * np.pi * epsilon0 * dist_p)

    # Vector de potenciales impuestos Phi
    phi_vec = np.full(m_total, float(voltaje_nominal_v), dtype=float)

    # 4. Solución del sistema lineal P * Q = Phi
    try:
        q_vec = np.linalg.solve(matriz_p, phi_vec)
    except np.linalg.LinAlgError:
        # Fallback con mínimos cuadrados si la matriz está mal condicionada
        q_vec, _, _, _ = np.linalg.lstsq(matriz_p, phi_vec, rcond=None)

    # 5. Evaluación de precisión en superficie con malla densa de puntos de control
    n_ctrl_sub = multiplicador_control_superficie * n_cargas_por_subconductor
    ang_ctrl = np.linspace(0.0, 2.0 * np.pi, n_ctrl_sub, endpoint=False)

    lista_ctrl = []
    for xc, yc in centros:
        puntos_k = np.column_stack(
            (xc + radio_conductor_m * np.cos(ang_ctrl), yc + radio_conductor_m * np.sin(ang_ctrl))
        )
        lista_ctrl.append(puntos_k)
    puntos_ctrl_arr = np.vstack(lista_ctrl)  # Forma (K, 2)

    # Potencial evaluado en los puntos de control superficiales
    diff_ctrl = puntos_ctrl_arr[:, np.newaxis, :] - cargas_arr[np.newaxis, :, :]  # (K, M, 2)
    dist_ctrl = np.linalg.norm(diff_ctrl, axis=2)                                  # (K, M)
    dist_ctrl = np.maximum(dist_ctrl, 1e-12)

    v_surf = np.sum(q_vec[np.newaxis, :] / (4.0 * np.pi * epsilon0 * dist_ctrl), axis=1)

    # Errores en superficie
    error_abs = np.abs(v_surf - voltaje_nominal_v)
    error_rel_pct = (error_abs / abs(voltaje_nominal_v)) * 100.0 if voltaje_nominal_v != 0 else np.zeros_like(error_abs)

    error_abs_medio = float(np.mean(error_abs))
    error_medio_pct = float(np.mean(error_rel_pct))
    error_max_pct = float(np.max(error_rel_pct))

    # Campo eléctrico superficial analítico en puntos de control
    # E_vector = sum( Q_j * (r - r_j) / (4 * pi * eps0 * |r - r_j|^3) )
    factor_e = q_vec[np.newaxis, :] / (4.0 * np.pi * epsilon0 * (dist_ctrl**3))
    ex_surf = np.sum(factor_e * diff_ctrl[:, :, 0], axis=1)
    ey_surf = np.sum(factor_e * diff_ctrl[:, :, 1], axis=1)
    e_mag_surf = np.sqrt(ex_surf**2 + ey_surf**2)

    e_max_surf_v_m = float(np.max(e_mag_surf))
    e_max_surf_kv_m = e_max_surf_v_m / 1000.0
    e_max_surf_kv_cm = e_max_surf_v_m / 100000.0  # 1 kV/cm = 100 kV/m = 100,000 V/m

    # 6. Cálculo de la malla 2D de potencial escalar V(x, y)
    x_min, x_max, y_min, y_max = limites_malla
    x_lin = np.linspace(x_min, x_max, resolucion_malla)
    y_lin = np.linspace(y_min, y_max, resolucion_malla)
    x_grid, y_grid = np.meshgrid(x_lin, y_lin)

    puntos_malla = np.column_stack((x_grid.ravel(), y_grid.ravel()))
    total_pts = len(puntos_malla)
    v_flat = np.empty(total_pts, dtype=float)

    # Evaluación por chunks para alta velocidad y bajo uso de memoria
    for ini in range(0, total_pts, chunk_malla):
        fin = min(ini + chunk_malla, total_pts)
        pts_chunk = puntos_malla[ini:fin]
        diff_chunk = pts_chunk[:, np.newaxis, :] - cargas_arr[np.newaxis, :, :]
        dist_chunk = np.sqrt(diff_chunk[:, :, 0]**2 + diff_chunk[:, :, 1]**2)
        dist_chunk = np.maximum(dist_chunk, 1e-12)
        v_flat[ini:fin] = np.sum(q_vec[np.newaxis, :] / (4.0 * np.pi * epsilon0 * dist_chunk), axis=1)

    v_grid = v_flat.reshape(x_grid.shape)

    # 7. Cálculo de campo eléctrico mediante gradiente numérico sobre la malla
    dx = x_lin[1] - x_lin[0]
    dy = y_lin[1] - y_lin[0]
    dvy, dvx = np.gradient(v_grid, dy, dx)

    ex_grid = -dvx
    ey_grid = -dvy
    e_grid = np.sqrt(ex_grid**2 + ey_grid**2)

    # 8. Extracción del perfil de campo transversal a lo largo del eje horizontal y = 0
    # Índice de fila más cercana a y = 0
    fila_y0 = int(np.argmin(np.abs(y_lin - 0.0)))
    # Índice de columna donde x >= 0 (centro hacia borde exterior)
    col_x0 = int(np.argmin(np.abs(x_lin - 0.0)))

    x_trayectoria = x_lin[col_x0:]
    e_trayectoria = e_grid[fila_y0, col_x0:]

    return ResultadoCSM(
        n_subconductores=n_subconductores,
        distancia_haz_m=distancia_haz_m,
        radio_conductor_m=radio_conductor_m,
        voltaje_nominal_v=voltaje_nominal_v,
        centros_conductores=centros,
        cargas_coords=cargas_arr,
        contornos_coords=contornos_arr,
        cargas_q=q_vec,
        error_medio_superficie_pct=error_medio_pct,
        error_max_superficie_pct=error_max_pct,
        error_absoluto_medio_v=error_abs_medio,
        e_max_superficie_kv_cm=e_max_surf_kv_cm,
        e_max_superficie_kv_m=e_max_surf_kv_m,
        x_eje=x_lin,
        y_eje=y_lin,
        X_malla=x_grid,
        Y_malla=y_grid,
        V_malla=v_grid,
        E_malla=e_grid,
        x_trayectoria=x_trayectoria,
        E_trayectoria=e_trayectoria,
    )
