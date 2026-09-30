"""Módulo de geometrías de haces de subconductores para líneas de transmisión.

Define la ubicación espacial (coordenadas x, y en metros) de los centros de los subconductores
para configuraciones de haz de 3 subconductores (triángulo equilátero) y de 4 subconductores
(cuadrado regular), con centro de simetría en el origen (0, 0).
"""

from __future__ import annotations
import numpy as np


def centros_haz(n_subconductores: int, distancia_m: float) -> np.ndarray:
    """Calcula las coordenadas (x, y) de los centros de los subconductores en el haz.

    Parameters
    ----------
    n_subconductores : int
        Número de subconductores del haz. Admite 3 (triángulo equilátero) o 4 (cuadrado regular).
    distancia_m : float
        Separación centro a centro entre subconductores adyacentes del haz [m].

    Returns
    -------
    np.ndarray
        Matriz de forma (n_subconductores, 2) con las coordenadas (x, y) de cada centro [m].

    Raises
    ------
    ValueError
        Si n_subconductores no es 3 o 4, o si distancia_m <= 0.
    """
    if n_subconductores not in (3, 4):
        raise ValueError(
            f"Configuración de haz no soportada: n = {n_subconductores}. Solo se admiten n=3 o n=4."
        )
    if distancia_m <= 0:
        raise ValueError(
            f"La separación entre subconductores debe ser positiva: distancia_m = {distancia_m} m."
        )

    if n_subconductores == 3:
        # Triángulo equilátero de lado L = distancia_m
        # Radio del círculo circunscrito: r_circ = L / sqrt(3)
        # Vértices en 90°, 210° y 330°
        r_circ = distancia_m / np.sqrt(3.0)
        angulos_rad = np.deg2rad([90.0, 210.0, 330.0])
        x = r_circ * np.cos(angulos_rad)
        y = r_circ * np.sin(angulos_rad)
        return np.column_stack((x, y))

    # n == 4: Cuadrado regular de lado L = distancia_m
    # Semilado a = distancia_m / 2
    # Vértices: (+a, +a), (-a, +a), (-a, -a), (+a, -a)
    a = distancia_m / 2.0
    return np.array(
        [
            [+a, +a],
            [-a, +a],
            [-a, -a],
            [+a, -a],
        ],
        dtype=float,
    )
