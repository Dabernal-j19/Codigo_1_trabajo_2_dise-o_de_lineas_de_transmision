# Sistema Modular de Selección de Conductores y Simulación Electrostática (500 kV)
### Línea de Transmisión S/E La Virginia – S/E Alférez | Convocatoria UPME 04-2014

---

## 1. Visión General del Proyecto

Este software científico en Python implementa una **herramienta de ingeniería desacoplada, modular y de alto desempeño** para automatizar el diseño técnico y electrostático de líneas aéreas de transmisión de extra alta tensión (500 kV). 

El sistema integra de forma integral:
1. **Lectura y validación estandarizada** de catálogos comerciales heterogéneos de conductores eléctricos en formato Excel (`.xlsx`).
2. **Filtrado previo normativo** según los términos de referencia de la **Convocatoria UPME 04-2014**.
3. **Cálculo de balance térmico y ampacidad en régimen permanente** bajo la norma internacional **IEEE Std 738-2012**.
4. **Simulación electrostática bidimensional** de la distribución de potencial escalar y campo eléctrico superficial mediante el **Método de Simulación de Cargas (CSM)**.
5. **Generación automática de entregables ejecutivos**: libros de cálculo en Excel con formato corporativo, gráficos vectoriales de alta resolución (300 DPI) y bitácoras detalladas de auditoría técnica.

---

## 2. Marco Normativo y Criterios de Diseño (UPME 04-2014)

El proyecto corresponde al enlace de transmisión a 500 kV entre la **Subestación La Virginia (Risaralda)** y la **Subestación Alférez (Valle del Cauca)**, atravesando zonas con altitudes variables y condiciones meteorológicas tropicales críticas. El diseño obedece estrictamente a las exigencias regulatorias:

* **Capacidad de Corriente por Fase ($I_{\text{req}}$):** No inferior a **$2400\text{ A}$ continuos** en las condiciones ambientales más exigentes de la ruta.
* **Resistencia Eléctrica Máxima Longitudinal a 20 °C ($R_{\text{UPME}}$):**
  $$R_{\text{UPME}} \le 0.0230\ \Omega/\text{km} = 0.0230\times 10^{-3}\ \Omega/\text{m}$$
  Para un haz de $n$ subconductores en paralelo por fase:
  $$R_{\text{eq}, n} = \frac{R_{\text{dc,20}}}{n}$$
* **Configuraciones de Haz Permitidas:** Haces de 3 subconductores ($n = 3$) o 4 subconductores ($n = 4$).
* **Separación de Subconductores ($d_{\text{bundle}}$):** Valor predeterminado de **$457.2\text{ mm}$ ($18''$)**, totalmente parametrizable.
* **Geometría Espacial del Haz (Centrado en $(0, 0)$):**
  * **Haz de 3 subconductores ($n=3$):** Triángulo equilátero con radio circunscrito $r_{\text{circ}} = \frac{d_{\text{bundle}}}{\sqrt{3}}$ y ángulos $\theta \in \{90^\circ, 210^\circ, 330^\circ\}$.
  * **Haz de 4 subconductores ($n=4$):** Cuadrado regular de lado $d_{\text{bundle}}$ y semilado $a = \frac{d_{\text{bundle}}}{2}$, con vértices en $(+a, +a)$, $(-a, +a)$, $(-a, -a)$, $(+a, -a)$.

---

## 3. Formulación Técnica y Matemática

### 3.1. Filtro Preliminar de Catálogo
Para cada conductor del catálogo y cada configuración de haz ($n \in \{3, 4\}$), se calculan los valores preliminares:
$$R_{\text{eq}, n} = \frac{R_{\text{dc,20}}}{n} \quad [\Omega/\text{km}], \qquad I_{\text{prelim}, n} = n \times I_{\text{cat}} \quad [\text{A}]$$

**Criterio de descarte inmediato:** Se admite a cálculo térmico únicamente si satisface:
$$R_{\text{eq}, n} \le 0.0230\ \Omega/\text{km} \quad \text{y} \quad I_{\text{prelim}, n} \ge 2400\text{ A}$$
Cualquier conductor que no cumpla ambas restricciones queda descartado de inmediato con registro exacto de la causa.

### 3.2. Balance Térmico Estático (IEEE Std 738-2012)
Para los conductores admitidos, se evalúa el equilibrio térmico por unidad de longitud ($W/m$):
$$q_c + q_r = q_s + I_{\text{ind}}^2 \cdot R_{\text{ac2}}$$

1. **Corrección de resistencia por temperatura:**
   $$R_{\text{ac2}} = R_{\text{dc,20\_m}} \times \left( \frac{k + T_c}{k + 20} \right)$$
   donde $k = 225.0$ para aluminio y $T_c = 75\ ^\circ\text{C}$.
2. **Propiedades termofísicas del aire a temperatura de película $T_{\text{film}} = \frac{T_c + T_a}{2}$:**
   * Densidad: $\rho_f = \frac{1.293 - 1.525\times 10^{-4} H_e + 6.379\times 10^{-9} H_e^2}{1 + 0.00367 T_{\text{film}}}$
   * Viscosidad dinámica: $\mu_f = \frac{1.458\times 10^{-6} (T_{\text{film}} + 273.15)^{1.5}}{T_{\text{film}} + 273.15 + 110.4}$
   * Conductividad térmica: $k_f = 2.424\times 10^{-2} + 7.477\times 10^{-5} T_{\text{film}} - 4.407\times 10^{-9} T_{\text{film}}^2$
   * Reynolds: $N_{\text{RE}} = \frac{d \cdot \rho_f \cdot V_w}{\mu_f}$
   * Factor direccional del viento: $k_{\text{angle}} = 1.194 - \cos(\phi) + 0.194 \cos(2\phi) + 0.368 \sin(2\phi)$
3. **Pérdidas de calor:**
   * Convección natural: $q_{cn} = 3.645 \cdot \rho_f^{0.5} \cdot d^{0.75} \cdot (T_c - T_a)^{1.25}$
   * Convección forzada: $q_{c1} = (1.01 + 1.35 N_{\text{RE}}^{0.52}) k_f k_{\text{angle}} (T_c - T_a)$, $q_{c2} = 0.754 N_{\text{RE}}^{0.6} k_f k_{\text{angle}} (T_c - T_a)$
   * Convección efectiva: $q_c = \max(q_{cn}, q_{c1}, q_{c2})$
   * Radiación: $q_r = 17.8 \cdot \varepsilon \cdot d \cdot \left[ \left(\frac{T_c + 273.15}{100}\right)^4 - \left(\frac{T_a + 273.15}{100}\right)^4 \right]$
4. **Ganancia solar:**
   $$q_s = \alpha \cdot Q_{se} \cdot d$$
5. **Ampacidad del haz:**
   $$I_{\text{ind}} = \sqrt{\frac{q_c + q_r - q_s}{R_{\text{ac2}}}}, \qquad I_{\text{fase}} = n \times I_{\text{ind}}$$
   Si $I_{\text{fase}} < 2400\text{ A}$, el conductor no cumple con el régimen continuo y se descarta.

### 3.3. Simulación Electrostática por Simulación de Cargas (CSM)
Para cada conductor y haz admisible:
1. Se posicionan los centros de los subconductores $(x_c, y_c)$.
2. En cada subconductor se sitúan $N_c = 22$ cargas ficticias a un radio interno $r_q = 0.7 \cdot r_{\text{cond}}$ y $N_c$ puntos de contorno en la superficie real $r_0 = r_{\text{cond}}$.
3. Se construye la matriz de coeficientes de potencial $P \in \mathbb{R}^{M \times M}$ ($M = n \times N_c$):
   $$P_{ij} = \frac{1}{4\pi\varepsilon_0 \|\vec{r}_{i,\text{contorno}} - \vec{r}_{j,\text{carga}}\|}$$
4. Se resuelve el sistema lineal para el vector de cargas ficticias $Q$:
   $$P \cdot Q = \Phi$$
5. **Evaluación de error en borde:** Se calcula el potencial en una malla densa de puntos de control superficial ($100 \times N_c = 2200$ puntos por subconductor), extrayendo el error porcentual relativo medio y máximo.
6. **Malla 2D de potencial y campo eléctrico:** Sobre una ventana de $8\times 8\text{ m}$ con grilla de $500\times 500$ puntos, se evalúa $V(x, y)$ de forma vectorizada por bloques y se calcula numéricamente:
   $$\vec{E}(x, y) = -\nabla V(x, y) \implies E_x = -\frac{\partial V}{\partial x}, \quad E_y = -\frac{\partial V}{\partial y}, \quad E = \sqrt{E_x^2 + E_y^2}$$
7. **Campo eléctrico superficial máximo ($E_{\text{max}}$):** Se evalúa analíticamente sobre los puntos de superficie mediante superposición directa:
   $$\vec{E}(\vec{r}) = \sum_{j=1}^M \frac{Q_j (\vec{r} - \vec{r}_j)}{4\pi\varepsilon_0 \|\vec{r} - \vec{r}_j\|^3}$$

---

## 4. Arquitectura del Software

```text
proyecto_seleccion_conductores/
│
├── config/
│   ├── __init__.py
│   ├── parametros_entrada.json         # Archivo central de variables ambientales y de diseño
│   └── geometrias.py                   # Funciones generadoras de centros para haces n=3 y n=4
│
├── catalogos/
│   └── plantilla_catalogo_conductores.xlsx  # Plantilla limpia estandarizada (56 conductores ACSR/ACAR)
│
├── src/
│   ├── __init__.py
│   ├── lector_catalogo.py              # Validación, sanitización y filtro previo UPME
│   ├── balance_termico.py              # Balance térmico estático IEEE Std 738-2012
│   ├── metodo_cargas.py                # CSM: cargas ficticias, matriz P, potencial V y campo E
│   └── exportador.py                   # Generación de Excel, gráficos a 300 DPI y reporte de ejecución
│
├── tests/
│   ├── __init__.py
│   └── test_sistema.py                 # Suite de pruebas unitarias automatizadas
│
├── output/
│   ├── resultados_conductores.xlsx      # Entregable 1: Excel consolidado (Parámetros + Resultados Técnicos)
│   ├── reporte_ejecucion.txt            # Entregable 3: Bitácora detallada de auditoría y ejecución
│   └── figuras_potencial/               # Entregable 2: 109 gráficos en alta resolución (300 DPI)
│       ├── potencial_*.png              # Mapas 2D de potencial con PowerNorm(gamma=0.5)
│       ├── campo_e_perfil_*.png         # Perfiles transversales de campo eléctrico E(x)
│       └── superposicion_perfil_campo_e.png  # Comparativa de atenuación lateral de campo
│
├── main.py                             # Orquestador CLI del flujo integral
└── requirements.txt                    # Dependencias científicas requeridas
```

---

## 5. Requisitos e Instalación

### Requisitos de Software
* Python 3.9 o superior (probado y optimizado en Python 3.10 / 3.11 / 3.14).
* Librerías científicas listadas en `requirements.txt`:
  * `pandas >= 2.0.0`
  * `openpyxl >= 3.1.0`
  * `numpy >= 1.24.0`
  * `matplotlib >= 3.7.0`
  * `scipy >= 1.10.0`

### Instalación de Dependencias
```powershell
pip install -r requirements.txt
```

---

## 6. Guía Rápida de Ejecución

### 1. Ejecutar el Flujo Completo
```powershell
python main.py
```
El sistema ejecutará todas las etapas, imprimirá en consola el resumen ejecutivo y guardará todos los entregables en la carpeta `output/`.

### 2. Ejecutar sin Generación de Gráficos (Modo Rápido)
```powershell
python main.py --sin-figuras
```

### 3. Especificar Archivo de Configuración o Catálogo Alternativo
```powershell
python main.py --config config/parametros_entrada.json --catalogo catalogos/plantilla_catalogo_conductores.xlsx --output-dir output/
```

### 4. Ejecutar la Suite de Pruebas Unitarias
```powershell
python tests/test_sistema.py
```

---

## 7. Resultados Técnicos Destacados

Al procesar los 56 conductores comerciales del catálogo de referencia:
* **Total de evaluaciones posibles:** $56 \times 2 = 112$ combinaciones conductor-haz.
* **Descartados en filtro preliminar:** 58 combinaciones (15 por exceder resistencia equivalente y 43 por no satisfacer ni resistencia ni corriente preliminar).
* **Conductores evaluados con IEEE 738:** 54 configuraciones.
* **Conductores que cumplen UPME 04-2014:** 54 configuraciones admitidas.
* **Precisión electrostática del CSM:** Error porcentual relativo medio superficial de **$0.010\%$**, con un campo máximo superficial en el rango de $194$ a $317\text{ kV/cm}$.

### Comparativa de Conductores Clave
| Conductor | Calibre | Haz ($n$) | $d$ [mm] | $R_{\text{eq}}$ [$\Omega$/km] | $I_{\text{fase}}$ [A] | Margen [A] | Error CSM [\%] | $E_{\text{max}}$ [kV/cm] | Veredicto UPME |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ACSR Falcon** | 1590 KCMIL | 4 | 39.23 | 0.00900 | 7809.1 | +5409.1 | 0.0100 | 194.66 | **CUMPLE** |
| **ACSR Bobolink** | 1431 KCMIL | 4 | 36.24 | 0.01000 | 7278.8 | +4878.8 | 0.0101 | 211.95 | **CUMPLE** |
| **ACSR Bobolink** | 1431 KCMIL | 3 | 36.24 | 0.01333 | 5459.1 | +3059.1 | 0.0103 | 216.53 | **CUMPLE** |
| **ACSR Ruddy** | 900 KCMIL | 4 | 28.74 | 0.01600 | 5456.9 | +3056.9 | 0.0103 | 271.33 | **CUMPLE** |
| **ACSR Ruddy** | 900 KCMIL | 3 | 28.74 | 0.02133 | 4092.7 | +1692.7 | 0.0105 | 276.09 | **CUMPLE** |
| **ACAR (18/19)** | 950 kcmil | 4 | 28.49 | 0.01650 | 5362.7 | +2962.7 | 0.0103 | 273.85 | **CUMPLE** |
| **ACAR (18/19)** | 950 kcmil | 3 | 28.49 | 0.02200 | 4022.0 | +1622.0 | 0.0105 | 278.61 | **CUMPLE** |
| **ACSR Rook** | 636 KCMIL | 4 | 24.81 | 0.02250 | 4444.9 | +2044.9 | 0.0104 | 316.92 | **CUMPLE** |

> **Nota técnica:** El conductor **ACSR Rook (636 KCMIL)** con haz de 3 subconductores ($n=3$) presenta $R_{\text{eq}, 3} = 0.0300\ \Omega/\text{km} > 0.0230\ \Omega/\text{km}$, por lo que queda correctamente descartado en el filtro inicial, cumpliendo exactamente con las conclusiones de la memoria técnica de diseño.
