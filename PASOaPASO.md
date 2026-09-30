# Guía Operativa Paso a Paso (PASOaPASO.md)
### Sistema Modular de Selección de Conductores y Simulación Electrostática (500 kV)

Esta guía describe de manera exhaustiva y práctica cómo utilizar, configurar, auditar y adaptar la herramienta para cualquier nuevo análisis de ingeniería de líneas de transmisión de alta y extra alta tensión.

---

## Índice
1. [Preparación del Entorno](#1-preparación-del-entorno)
2. [Paso 1: Configurar las Variables de Entrada (`config/parametros_entrada.json`)](#2-paso-1-configurar-las-variables-de-entrada-configparametros_entradajson)
3. [Paso 2: Alimentar o Modificar el Catálogo de Conductores (`catalogos/`)](#3-paso-2-alimentar-o-modificar-el-catálogo-de-conductores-catalogos)
4. [Paso 3: Ejecución del Flujo de Ingeniería](#4-paso-3-ejecución-del-flujo-de-ingeniería)
5. [Paso 4: Interpretación de los Entregables Generados](#5-paso-4-interpretación-de-los-entregables-generados)
6. [Paso 5: Casos Prácticos de Aplicación](#6-paso-5-casos-prácticos-de-aplicación)
   - [Caso A: Condición Meteorológica Crítica (Viento Calmo)](#caso-a-condición-meteorológica-crítica-viento-calmo)
   - [Caso B: Evaluación para Línea a 230 kV o Tensión Diferente](#caso-b-evaluación-para-línea-a-230-kv-o-tensión-diferente)
   - [Caso C: Incorporación de Conductores de Alta Temperatura (ACSS / ACCC)](#caso-c-incorporación-de-conductores-de-alta-temperatura-acss--accc)
   - [Caso D: Variación de la Separación del Haz ($d_{\text{bundle}}$)](#caso-d-variación-de-la-separación-del-haz-d_textbundle)
7. [Paso 6: Validación y Pruebas Unitarias](#7-paso-6-validación-y-pruebas-unitarias)
8. [Resolución de Problemas Frecuentes (FAQ / Troubleshooting)](#8-resolución-de-problemas-frecuentes-faq--troubleshooting)

---

## 1. Preparación del Entorno

### 1.1. Verificar la Instalación de Python
Abre una terminal de PowerShell o CMD y comprueba la versión instalada:
```powershell
python --version
```
*Se requiere Python 3.9 o superior.*

### 1.2. Ubicarse en el Directorio del Proyecto
```powershell
# Ubicarse en la carpeta raíz del proyecto (donde se encuentra main.py)
cd ruta/al/proyecto_seleccion_conductores
```

### 1.3. Instalar Dependencias
Si no las tienes instaladas previamente, ejecuta:
```powershell
pip install -r requirements.txt
```
Las librerías principales son: `pandas`, `openpyxl`, `numpy`, `matplotlib` y `scipy`.

### 1.4. Validar el Estado Inicial con las Pruebas Unitarias
Antes de realizar cualquier modificación, verifica que el núcleo matemático funcione correctamente:
```powershell
python tests/test_sistema.py
```
*Salida esperada: `Ran 5 tests in 0.17s ... OK`.*

---

## 2. Paso 1: Configurar las Variables de Entrada (`config/parametros_entrada.json`)

El archivo [`config/parametros_entrada.json`](config/parametros_entrada.json) concentra todas las hipótesis físicas, ambientales, eléctricas y numéricas del modelo. No es necesario modificar ninguna línea de código Python para alterar estas condiciones.

### 2.1. Tabla de Parámetros Configurables

| Clave JSON | Significado Físico / Normativo | Unidad | Valor por Defecto | Impacto en el Modelo |
| :--- | :--- | :---: | :---: | :--- |
| `He` | Altitud sobre el nivel del mar | m | `980.0` | Afecta la densidad del aire $\rho_f$ y la convección. |
| `Ta` | Temperatura ambiente máxima de diseño | °C | `30.0` | Define el salto térmico $(T_c - T_a)$ y la radiación hacia el entorno. |
| `Tc` | Temperatura máxima admisible del conductor | °C | `75.0` | Límite térmico continuo. Afecta la resistencia corregida $R_{\text{ac2}}$. |
| `Vw` | Velocidad transversal del viento | m/s | `5.0` | Impacto directo en el número de Reynolds $N_{\text{RE}}$ y la convección forzada $q_c$. |
| `phi_grados` | Ángulo entre la dirección del viento y el cable | grados | `90.0` | $90^\circ$ = viento ortogonal (máxima convección forzada). |
| `Qse` | Radiación solar incidente global | W/m² | `4500.0` | Ganancia solar $q_s$. Puede ajustarse a valores como $1000$ o $1200\text{ W/m}^2$. |
| `alfa` | Coeficiente de absorción solar del cable | adim. | `0.5` | Superficie envejecida típica ($0.5$). Cables nuevos: $\sim 0.23$. |
| `emisividad` | Emisividad superficial del cable | adim. | `0.5` | Disipación por radiación $q_r$. Envejecido: $0.5$. |
| `k_aluminio` | Constante térmica para corrección de resistencia | °C | `225.0` | Inverso del coeficiente térmico a $0\ ^\circ\text{C}$ para aluminio ($225.0$ a $228.1$). |
| `voltaje_sistema_kV` | Tensión nominal de línea del sistema | kV | `500.0` | Tensión base para la simulación electrostática. |
| `tipo_voltaje_csm` | Tipo de potencial aplicado al haz | texto | `"fase_tierra"` | `"fase_tierra"` aplica $500/\sqrt{3}\text{ kV}$; `"fase_fase"` aplica $500\text{ kV}$. |
| `distancia_haz_mm` | Separación centro a centro de los subconductores | mm | `457.2` | Fija la geometría espacial del haz ($d_{\text{bundle}}$). |
| `haces_a_evaluar` | Lista de números de subconductores a evaluar | lista | `[3, 4]` | Evalúa haces triangulares ($n=3$) y cuadrados ($n=4$). |
| `I_requerida_A` | Capacidad de corriente mínima por fase (UPME) | A | `2400.0` | Límite normativo inferior para filtro preliminar y térmico. |
| `R_max_UPME_ohm_km` | Resistencia DC equivalente máxima del haz a 20 °C | $\Omega$/km | `0.0230` | Límite normativo superior para el paralelo del haz. |
| `cargas_ficticias_por_subconductor` | Número de cargas filiformes ficticias ($N_c$) | adim. | `22` | Precisión de discretización angular interna en CSM. |
| `factor_radio_cargas` | Radio relativo de las cargas internas ($r_q / r_0$) | adim. | `0.7` | Estabilidad matemática de la matriz $P$ en CSM ($0.5$ a $0.8$). |
| `multiplicador_control_superficie` | Densidad de puntos para error en borde | adim. | `100` | Evalúa $100 \times N_c = 2200$ puntos por subconductor. |
| `limites_malla` | Ventana espacial 2D `[xmin, xmax, ymin, ymax]` | m | `[-4.0, 4.0, -4.0, 4.0]` | Dimensión del área de simulación de campo y potencial. |
| `resolucion_malla` | Cantidad de divisiones por eje | puntos | `500` | Genera una matriz de cálculo de $500 \times 500 = 250,000$ puntos. |
| `dpi_figuras` | Resolución de los gráficos generados | DPI | `300` | Calidad de publicación técnica y reportes formales. |

---

## 3. Paso 2: Alimentar o Modificar el Catálogo de Conductores (`catalogos/`)

El catálogo se encuentra en: [`catalogos/plantilla_catalogo_conductores.xlsx`](catalogos/plantilla_catalogo_conductores.xlsx).

### 3.1. Estructura de la Plantilla
La fila 1 contiene los encabezados planos estandarizados (sin celdas combinadas ni formatos decorativos incompatibles):

| Columna | Nombre de Cabecera | Tipo de Dato | Obligatorio | Descripción |
| :---: | :--- | :---: | :---: | :--- |
| **A** | `tipo_conductor` | Texto | Sí | Tecnología del conductor (`ACSR`, `ACAR`, `AAAC`, `ACSS`). |
| **B** | `calibre` | Texto | Sí | Calibre comercial (ej. `900 kcmil`, `1431 kcmil`, `636 kcmil`). |
| **C** | `nombre_clave` | Texto | Sí | Code Word de catálogo (ej. `Ruddy`, `Bobolink`, `Rook`). |
| **D** | `diametro_exterior_mm` | Numérico | Sí | Diámetro exterior real en milímetros ($d$). |
| **E** | `area_aluminio_mm2` | Numérico | No | Área de la sección conductora en mm² (informativa). |
| **F** | `area_acero_mm2` | Numérico | No | Área de refuerzo mecánico en mm² (informativa). |
| **G** | `resistencia_dc_20c_ohm_km` | Numérico | Sí | Resistencia DC a 20 °C del conductor individual en $\Omega$/km. |
| **H** | `ampacidad_catalogo_a` | Numérico | Sí | Capacidad nominal del catálogo del fabricante en Amperios. |
| **I** | `peso_kg_km` | Numérico | No | Masa lineal unitaria del conductor en kg/km. |
| **J** | `carga_rotura_kgf` | Numérico | No | Tensión mecánica de rotura mínima individual en kgf. |

### 3.2. Reglas para Añadir Nuevos Conductores
1. **Abre el archivo en Excel:** Puedes editarlo con Microsoft Excel, LibreOffice Calc o cualquier editor de hojas de cálculo.
2. **Añade una fila al final:** Coloca el tipo de conductor, calibre, nombre clave, diámetro exterior en mm, resistencia DC a 20 °C en $\Omega$/km y la ampacidad del fabricante.
3. **Puntos decimales:** Usa el formato numérico habitual de tu versión de Excel. El lector de Python está programado para aceptar números nativos, strings con coma decimal (`0,064`) o con punto decimal (`0.064`).
4. **Guarda el archivo:** Mantén la extensión `.xlsx` y el mismo nombre o especifica una nueva ruta mediante el argumento `--catalogo`.

---

## 4. Paso 3: Ejecución del Flujo de Ingeniería

### 4.1. Ejecución Estándar (Flujo Completo)
Abre la consola de comandos en la carpeta del proyecto y ejecuta:
```powershell
python main.py
```
Esta orden ejecuta:
1. Lectura del archivo `config/parametros_entrada.json`.
2. Validación de columnas y tipos en `plantilla_catalogo_conductores.xlsx`.
3. Filtrado rápido preliminar ($R_{\text{eq}} \le 0.0230\ \Omega/\text{km}$ e $I_{\text{prelim}} \ge 2400\text{ A}$).
4. Balance térmico estático según **IEEE Std 738-2012** para cada candidato admitido.
5. Verificación de corriente continua calculada ($I_{\text{fase}} \ge 2400\text{ A}$).
6. Simulación electrostática **CSM** (cargas ficticias, error en borde, malla 2D y campo transversal).
7. Exportación del Excel consolidado, gráficos de 300 DPI y reporte de auditoría.

### 4.2. Opciones de Línea de Comandos (CLI)
El script `main.py` incluye argumentos avanzados para mayor versatilidad:

| Argumento | Descripción | Ejemplo de Uso |
| :--- | :--- | :--- |
| `--config <ruta>` | Utiliza un archivo JSON de parámetros alternativo. | `python main.py --config mis_parametros.json` |
| `--catalogo <ruta>` | Utiliza un catálogo Excel diferente. | `python main.py --catalogo nuevo_catalogo.xlsx` |
| `--output-dir <ruta>` | Define la carpeta donde se depositarán los resultados. | `python main.py --output-dir resultados_corrida_2/` |
| `--sin-figuras` | Omite la generación de imágenes PNG para cálculo ultrarrápido (< 2 segundos). | `python main.py --sin-figuras` |

---

## 5. Paso 4: Interpretación de los Entregables Generados

Todos los entregables se generan de forma automática en la carpeta `output/`:

### 5.1. Libro Excel Consolidado (`output/resultados_conductores.xlsx`)
Consta de dos hojas estructuradas con formato visual profesional:
* **Hoja "Parámetros de Entrada":** Registra con trazabilidad jurídica y técnica los 20 parámetros ambientales, geométricos y numéricos empleados en la corrida.
* **Hoja "Resultados Técnicos":** Lista detallada de los conductores que superaron la totalidad de los filtros técnicos, con 20 columnas que abarcan:
  1. Familia, calibre y nombre clave.
  2. Configuración de haz ($n=3$ o $n=4$).
  3. Dimensiones y peso individual y total del haz por fase ($kg/km$).
  4. Carga de rotura individual ($kgf$).
  5. Resistencia DC individual y equivalente del haz ($\Omega/km$).
  6. Disipaciones térmicas: convección ($q_c$), radiación ($q_r$) y absorción solar ($q_s$) en $W/m$.
  7. Capacidad de corriente por subconductor ($I_{\text{ind}}$) y por haz ($I_{\text{fase}}$) en Amperios.
  8. Margen térmico sobre norma UPME ($I_{\text{fase}} - 2400\text{ A}$).
  9. Error porcentual medio superficial del CSM ($\%$) y campo eléctrico superficial máximo ($kV/cm$ y $kV/m$).
  10. Veredicto normativo final (`CUMPLE`).

### 5.2. Carpeta de Gráficos (`output/figuras_potencial/`)
* **Mapas 2D de Potencial Escalar (`potencial_<tipo>_<clave>_n<haz>.png`):**
  * Exportados a 300 DPI con escala no lineal `PowerNorm(gamma=0.5)` y mapa de colores `jet`.
  * Visualizan las líneas equipotenciales cerradas y la geometría de los subconductores en línea discontinua negra.
* **Perfiles de Campo Transversal (`campo_e_perfil_<tipo>_<clave>_n<haz>.png`):**
  * Representan la magnitud del campo eléctrico $|E|$ a lo largo del eje horizontal $x$ ($y=0$), mostrando la atenuación hacia el borde de la servidumbre.
* **Gráfico de Superposición (`superposicion_perfil_campo_e.png`):**
  * Curva consolidada que compara la atenuación lateral de campo eléctrico entre los conductores más representativos.

### 5.3. Informe de Auditoría y Ejecución (`output/reporte_ejecucion.txt`)
Documento de texto plano estructurado que certifica:
1. Timestamp exacto y tiempo total de procesamiento.
2. Parámetros de diseño.
3. Resumen estadístico: total leídos, descartes preliminares desglosados (por $R_{\text{eq}}$, por $I_{\text{prelim}}$ o por ambos), evaluados con IEEE 738 y aprobados.
4. Tabla ejecutiva de conductores que cumplen.
5. Bitácora pormenorizada de todos los conductores descartados indicando fila de Excel y motivo numérico exacto.

---

## 6. Paso 5: Casos Prácticos de Aplicación

A continuación se presentan guías paso a paso para reejecutar el análisis ante variaciones habituales de ingeniería:

---

### Caso A: Condición Meteorológica Crítica (Viento Calmo)
**Objetivo:** Analizar el comportamiento térmico ante una condición ambiental adversa sin viento favorable ($V_w = 0.61\text{ m/s}$) y con radiación solar moderada ($Q_{se} = 1000\text{ W/m}^2$).

1. Abre `config/parametros_entrada.json`.
2. Modifica los campos:
   ```json
   "Vw": 0.61,
   "Qse": 1000.0
   ```
3. Guarda el archivo.
4. Ejecuta:
   ```powershell
   python main.py
   ```
5. **Observación esperada:** Al disminuir la velocidad del viento de $5.0\text{ m/s}$ a $0.61\text{ m/s}$, la convección forzada disminuye drásticamente. Algunos conductores con menor calibre que antes cumplían podrían ser descartados en la etapa de balance térmico por no alcanzar los $2400\text{ A}$, quedando únicamente los calibres más robustos.

---

### Caso B: Evaluación para Línea a 230 kV o Tensión Diferente
**Objetivo:** Adaptar el software para una línea a 230 kV con haz de 2 subconductores ($n=2$) o 765 kV con haz de 6 ($n=6$).

1. Abre `config/geometrias.py`: si requieres soportar $n=2$, puedes agregar la disposición horizontal o vertical en la función `centros_haz`.
2. Abre `config/parametros_entrada.json`.
3. Ajusta las variables eléctricas y normativas:
   ```json
   "voltaje_sistema_kV": 230.0,
   "I_requerida_A": 1200.0,
   "R_max_UPME_ohm_km": 0.050,
   "haces_a_evaluar": [3, 4]
   ```
4. Guarda y reejecuta:
   ```powershell
   python main.py
   ```

---

### Caso C: Incorporación de Conductores de Alta Temperatura (ACSS / ACCC)
**Objetivo:** Evaluar conductores especiales de alta temperatura y baja flecha (HTLS) que operan continuamente a $150\ ^\circ\text{C}$ o $180\ ^\circ\text{C}$.

1. Abre `config/parametros_entrada.json` y eleva la temperatura máxima de diseño:
   ```json
   "Tc": 150.0
   ```
2. Abre `catalogos/plantilla_catalogo_conductores.xlsx`.
3. Añade una fila para el conductor ACSS (ejemplo: `ACSS 1431 kcmil Bobolink`, $d = 36.24\text{ mm}$, $R_{\text{dc,20}} = 0.0400\ \Omega/\text{km}$, $I_{\text{cat}} = 1800\text{ A}$).
4. Guarda el archivo Excel.
5. Ejecuta:
   ```powershell
   python main.py
   ```
6. El balance térmico corregirá automáticamente la resistencia a $150\ ^\circ\text{C}$ y evaluará la disipación convectiva con el mayor gradiente $(150 - 30 = 120\ ^\circ\text{C})$.

---

### Caso D: Variación de la Separación del Haz ($d_{\text{bundle}}$)
**Objetivo:** Estudiar el impacto electrostático de modificar la separación entre subconductores desde $400\text{ mm}$ hasta $500\text{ mm}$.

1. Abre `config/parametros_entrada.json`.
2. Modifica el campo:
   ```json
   "distancia_haz_mm": 500.0
   ```
3. Guarda y ejecuta:
   ```powershell
   python main.py
   ```
4. Revisa en la columna de la hoja de resultados el campo superficial máximo ($E_{\text{max}}$) y comprueba cómo la mayor distancia de haz modifica la concentración de campo en la superficie externa de los subconductores.

---

## 7. Paso 6: Validación y Pruebas Unitarias

El proyecto incluye una suite automatizada de pruebas en [`tests/test_sistema.py`](tests/test_sistema.py) para asegurar que futuras modificaciones no degraden la exactitud matemática ni la estabilidad del sistema:

* **`test_haz_n3_equilatero`:** Verifica que los 3 vértices formen un triángulo equilátero perfecto de lado $d_{\text{bundle}}$ con centroide en $(0, 0)$.
* **`test_haz_n4_cuadrado`:** Verifica que los 4 centros formen un cuadrado de lado $d_{\text{bundle}}$ centrado en el origen.
* **`test_parametros_invalidos`:** Verifica el rechazo de geometrías inconsistentes o distancias negativas.
* **`test_balance_termico_ruddy`:** Comprueba que las pérdidas por convección, radiación y la corriente admisible bajo IEEE 738 sean físicamente coherentes.
* **`test_precision_csm`:** Confirma que el error medio del potencial superficial en el CSM sea estrictamente inferior al $0.05\%$.

Para ejecutar todas las pruebas:
```powershell
python tests/test_sistema.py
```

---

## 8. Resolución de Problemas Frecuentes (FAQ / Troubleshooting)

### P1: Modifiqué el archivo Excel y ahora obtengo `KeyError` o error de columnas obligatorias.
**Solución:** Verifica que la fila 1 contenga exactamente los nombres estandarizados en minúsculas: `tipo_conductor`, `calibre`, `nombre_clave`, `diametro_exterior_mm`, `resistencia_dc_20c_ohm_km`, `ampacidad_catalogo_a`. No dejes filas vacías intermedias antes de los encabezados.

### P2: ¿Por qué la corrida tarda más de 1 minuto en completarse?
**Solución:** Cada uno de los 54 conductores aprobados genera 2 figuras de alta resolución ($300\text{ DPI}$) evaluando mallas de $500 \times 500$ puntos (109 imágenes en total). Si requieres resultados inmediatos (menos de 2 segundos), ejecuta con la bandera de modo rápido:
```powershell
python main.py --sin-figuras
```

### P3: ¿Cómo cambio la unidad de los gráficos de campo de kV/m a kV/cm?
**Solución:** En `src/exportador.py`, la función `exportar_figuras` grafica por defecto en $kV/m$ ($1\text{ kV/cm} = 100\text{ kV/m}$). Si prefieres $kV/cm$, simplemente divide `e_kv_m` por $100.0$ y ajusta la etiqueta del eje Y a `[kV/cm]`.

### P4: La terminal de Windows muestra caracteres extraños al imprimir tablas.
**Solución:** Todos los textos de consola han sido diseñados en ASCII compatible con páginas de código de Windows (`cp1252`). Los archivos de reporte (`.txt` y `.xlsx`) se guardan siempre en codificación estándar `UTF-8` universal.

---
*Fin del documento operativo PASOaPASO.md.*
