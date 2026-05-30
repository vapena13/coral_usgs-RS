# Flujo SfM-MVS para im?genes submarinas USGS Eastern Dry Rocks

Este repositorio documenta un flujo de procesamiento fotogram?trico aplicado a un subconjunto del dataset p?blico **USGS SQUID-5 Eastern Dry Rocks 2021**. El trabajo eval?a la reconstrucci?n de fondo marino mediante **Structure from Motion / Multi-View Stereo (SfM-MVS)** en Agisoft Metashape, incorporando una etapa de correcci?n colorim?trica previa y scripts de apoyo para automatizar partes del flujo.

## Objetivo

Evaluar si un subconjunto de im?genes submarinas del sistema SQUID-5 permite generar productos fotogram?tricos consistentes, incluyendo:

- c?maras alineadas y nube dispersa;
- nube densa;
- malla tridimensional;
- modelo digital de elevaci?n (DEM);
- ortomosaico;
- comparaci?n visual y estad?stica entre im?genes originales y corregidas.

## Dataset

Fuente principal:

- U.S. Geological Survey. Eastern Dry Rocks SQUID-5 imagery and derived products, Florida Keys, 2021.
- Data release: https://cmgds.marine.usgs.gov/data-releases/datarelease/10.5066-P93RIIG9/

El conjunto completo contiene 138.733 im?genes TIFF. Para este trabajo se revisaron las l?neas 17 a 24 y se seleccion? un subbloque de 634 im?genes por continuidad espacial, solape entre trayectorias y tama?o manejable.

## Estructura del repositorio

```text
bibliography/        Referencias bibliogr?ficas de apoyo.
docs/                Documentos de informe y ap?ndices locales.
outputs/figures/     Figuras usadas en el informe.
reports/             Reportes PDF y evidencias de procesamiento.
scripts/             Scripts de selecci?n, correcci?n, automatizaci?n y an?lisis.
workflow/            Par?metros y notas del flujo de trabajo.
```

Los productos pesados generados por Metashape, como `.tif`, `.obj`, `.las`, `.psx` y carpetas `.files`, se mantienen fuera de Git mediante `.gitignore`.

## Scripts principales

- `scripts/02_verificar_imagenes.py`  
  Verificaci?n b?sica de im?genes del subconjunto.

- `scripts/03_corregir_orto_usgs.py`  
  Correcci?n colorim?trica aplicada a productos RGB derivados.

- `scripts/04_correccion_imagenes_exif.py`  
  Correcci?n colorim?trica de im?genes individuales preservando metadata EXIF/GPS.

- `scripts/05_run_metashape_workflow.py`  
  Automatizaci?n por etapas del flujo SfM-MVS para im?genes corregidas en Agisoft Metashape.

- `scripts/05_run_metashape_workflow_original.py`  
  Variante del flujo automatizado para im?genes sin correcci?n colorim?trica.

- `scripts/06_generar_histogramas_rgb.py`  
  Generaci?n de histogramas RGB promedio para comparar im?genes originales y corregidas.

## Flujo metodol?gico

El procesamiento combin? etapas manuales y automatizadas:

1. Selecci?n del subbloque EDR 17-24.
2. Correcci?n colorim?trica previa de im?genes RGB.
3. Carga de fotograf?as en Metashape.
4. Alineaci?n SfM y optimizaci?n de c?maras.
5. Construcci?n de mapas de profundidad y nube densa.
6. Construcci?n de malla 3D, DEM y ortomosaico.
7. Exportaci?n de productos y comparaci?n entre flujo sin correcci?n y flujo corregido.

La automatizaci?n en Python se dise?? por checkpoints para mejorar la trazabilidad. El flujo exporta c?maras alineadas en XML, nube densa en LAS y productos intermedios recuperables, reduciendo la p?rdida de trabajo ante fallos de persistencia del proyecto en Metashape.

## Resultados incluidos

En `outputs/figures/` se incluyen figuras de:

- localizaci?n y selecci?n del subconjunto;
- alineaci?n y control de calidad;
- comparaci?n RGB antes/despu?s de correcci?n;
- nube densa, DEM y ortomosaico;
- diagrama de automatizaci?n en Metashape con Python.

En `reports/` se conservan reportes PDF de apoyo generados durante el procesamiento.

## Limitaciones

El procesamiento no incluye validaci?n m?trica absoluta con barras de escala o puntos de control independientes. Por tanto, los productos se interpretan como reconstrucciones de consistencia geom?trica relativa. La automatizaci?n requiere supervisi?n t?cnica en etapas como revisi?n de c?maras alineadas, inspecci?n de productos parciales y validaci?n visual de las salidas.

## Nota de reproducibilidad

Las rutas locales del proyecto se documentan en `workflow/automation_workflow.md` y `workflow/automation_workflow_original.md`. Para ejecutar los scripts de Metashape se requiere usar el int?rprete de Python incluido con Agisoft Metashape Professional.
