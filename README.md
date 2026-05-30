# Flujo SfM-MVS para imágenes submarinas USGS Eastern Dry Rocks

Este repositorio documenta un flujo de procesamiento fotogramétrico aplicado a un subconjunto del dataset público **USGS SQUID-5 Eastern Dry Rocks 2021**. El trabajo evalúa la reconstrucción de fondo marino mediante **Structure from Motion / Multi-View Stereo (SfM-MVS)** en Agisoft Metashape, incorporando una etapa de corrección colorimétrica previa y scripts de apoyo para automatizar partes del flujo.

## Objetivo

Evaluar si un subconjunto de imágenes submarinas del sistema SQUID-5 permite generar productos fotogramétricos consistentes, incluyendo:

- cámaras alineadas y nube dispersa;
- nube densa;
- malla tridimensional;
- modelo digital de elevación (DEM);
- ortomosaico;
- comparación visual y estadística entre imágenes originales y corregidas.

## Dataset

Fuente principal:

- U.S. Geological Survey. Eastern Dry Rocks SQUID-5 imagery and derived products, Florida Keys, 2021.
- Data release: https://cmgds.marine.usgs.gov/data-releases/datarelease/10.5066-P93RIIG9/

El conjunto completo contiene 138.733 imágenes TIFF. Para este trabajo se revisaron las líneas 17 a 24 y se seleccionó un subbloque de 634 imágenes por continuidad espacial, solape entre trayectorias y tamaño manejable.

## Estructura del repositorio

```text
bibliography/        Referencias bibliográficas de apoyo.
docs/                Documentos de informe y apéndices locales.
outputs/figures/     Figuras usadas en el informe.
reports/             Reportes PDF y evidencias de procesamiento.
scripts/             Scripts de selección, corrección, automatización y análisis.
workflow/            Parámetros y notas del flujo de trabajo.
```

Los productos pesados generados por Metashape, como `.tif`, `.obj`, `.las`, `.psx` y carpetas `.files`, se mantienen fuera de Git mediante `.gitignore`.

## Scripts principales

- `scripts/02_verificar_imagenes.py`  
  Verificación básica de imágenes del subconjunto.

- `scripts/03_corregir_orto_usgs.py`  
  Corrección colorimétrica aplicada a productos RGB derivados.

- `scripts/04_correccion_imagenes_exif.py`  
  Corrección colorimétrica de imágenes individuales preservando metadata EXIF/GPS.

- `scripts/05_run_metashape_workflow.py`  
  Automatización por etapas del flujo SfM-MVS para imágenes corregidas en Agisoft Metashape.

- `scripts/05_run_metashape_workflow_original.py`  
  Variante del flujo automatizado para imágenes sin corrección colorimétrica.

- `scripts/06_generar_histogramas_rgb.py`  
  Generación de histogramas RGB promedio para comparar imágenes originales y corregidas.

## Flujo metodológico

El procesamiento combinó etapas manuales y automatizadas:

1. Selección del subbloque EDR 17-24.
2. Corrección colorimétrica previa de imágenes RGB.
3. Carga de fotografías en Metashape.
4. Alineación SfM y optimización de cámaras.
5. Construcción de mapas de profundidad y nube densa.
6. Construcción de malla 3D, DEM y ortomosaico.
7. Exportación de productos y comparación entre flujo sin corrección y flujo corregido.

La automatización en Python se diseñó por checkpoints para mejorar la trazabilidad. El flujo exporta cámaras alineadas en XML, nube densa en LAS y productos intermedios recuperables, reduciendo la pérdida de trabajo ante fallos de persistencia del proyecto en Metashape.

## Resultados incluidos

En `outputs/figures/` se incluyen figuras de:

- localización y selección del subconjunto;
- alineación y control de calidad;
- comparación RGB antes/después de corrección;
- nube densa, DEM y ortomosaico;
- diagrama de automatización en Metashape con Python.

En `reports/` se conservan reportes PDF de apoyo generados durante el procesamiento.

## Limitaciones

El procesamiento no incluye validación métrica absoluta con barras de escala o puntos de control independientes. Por tanto, los productos se interpretan como reconstrucciones de consistencia geométrica relativa. La automatización requiere supervisión técnica en etapas como revisión de cámaras alineadas, inspección de productos parciales y validación visual de las salidas.

## Nota de reproducibilidad

Las rutas locales del proyecto se documentan en `workflow/automation_workflow.md` y `workflow/automation_workflow_original.md`. Para ejecutar los scripts de Metashape se requiere usar el intérprete de Python incluido con Agisoft Metashape Professional.
