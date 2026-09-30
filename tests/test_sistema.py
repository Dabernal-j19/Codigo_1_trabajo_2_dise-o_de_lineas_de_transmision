"""Suite de pruebas unitarias y de integración del sistema de conductores y simulación CSM."""

import os
import sys
import unittest
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config.geometrias import centros_haz
from src.balance_termico import ParametrosAmbientales, calcular_balance_termico
from src.metodo_cargas import simular_csm


class TestGeometrias(unittest.TestCase):
    """Pruebas para el cálculo de coordenadas de haces."""

    def test_haz_n3_equilatero(self):
        d_m = 0.4572
        centros = centros_haz(3, d_m)
        self.assertEqual(centros.shape, (3, 2))

        # El centroide debe ser (0, 0)
        np.testing.assert_allclose(np.mean(centros, axis=0), [0.0, 0.0], atol=1e-12)

        # La distancia entre todos los pares de vértices debe ser d_m
        d01 = np.linalg.norm(centros[0] - centros[1])
        d12 = np.linalg.norm(centros[1] - centros[2])
        d20 = np.linalg.norm(centros[2] - centros[0])
        np.testing.assert_allclose([d01, d12, d20], [d_m, d_m, d_m], rtol=1e-6)

    def test_haz_n4_cuadrado(self):
        d_m = 0.4572
        centros = centros_haz(4, d_m)
        self.assertEqual(centros.shape, (4, 2))

        # Centroide en el origen
        np.testing.assert_allclose(np.mean(centros, axis=0), [0.0, 0.0], atol=1e-12)

        # Distancia entre lados adyacentes = d_m
        d01 = np.linalg.norm(centros[0] - centros[1])
        d12 = np.linalg.norm(centros[1] - centros[2])
        d23 = np.linalg.norm(centros[2] - centros[3])
        d30 = np.linalg.norm(centros[3] - centros[0])
        np.testing.assert_allclose([d01, d12, d23, d30], [d_m, d_m, d_m, d_m], rtol=1e-6)

    def test_parametros_invalidos(self):
        with self.assertRaises(ValueError):
            centros_haz(2, 0.4572)
        with self.assertRaises(ValueError):
            centros_haz(3, -0.1)


class TestBalanceTermico(unittest.TestCase):
    """Pruebas para el cálculo de ampacidad IEEE Std 738-2012."""

    def test_balance_termico_ruddy(self):
        params = ParametrosAmbientales(
            He=980.0,
            Ta=30.0,
            Tc=75.0,
            Vw=5.0,
            phi_grados=90.0,
            Qse=4500.0,
            alfa=0.5,
            emisividad=0.5,
            k_aluminio=225.0,
        )
        res = calcular_balance_termico(
            diametro_exterior_mm=28.74,
            resistencia_dc_20c_ohm_km=0.064,
            n_subconductores=4,
            params=params,
            i_requerida_a=2400.0,
        )
        self.assertTrue(res.cumple_criterio_termico)
        self.assertGreater(res.corriente_fase_A, 5000.0)
        self.assertGreater(res.qc_w_m, 0.0)
        self.assertGreater(res.qr_w_m, 0.0)
        self.assertGreater(res.qs_w_m, 0.0)


class TestCSM(unittest.TestCase):
    """Pruebas para el Método de Simulación de Cargas."""

    def test_precision_csm(self):
        d_m = 0.4572
        r_cond = 0.02874 / 2.0
        v_nom = 288675.13

        res = simular_csm(
            n_subconductores=3,
            distancia_haz_m=d_m,
            radio_conductor_m=r_cond,
            voltaje_nominal_v=v_nom,
            n_cargas_por_subconductor=22,
            factor_radio_cargas=0.7,
            multiplicador_control_superficie=50,
            limites_malla=(-2.0, 2.0, -2.0, 2.0),
            resolucion_malla=100,
        )

        # El error medio en superficie debe ser menor al 0.05%
        self.assertLess(res.error_medio_superficie_pct, 0.05)
        # Campo eléctrico superficial positivo y razonable
        self.assertGreater(res.e_max_superficie_kv_cm, 50.0)
        self.assertEqual(res.V_malla.shape, (100, 100))


if __name__ == "__main__":
    unittest.main()
