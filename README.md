# Underwater photogrammetry workflow on USGS Eastern Dry Rocks imagery

Este repositorio documenta un flujo de trabajo fotogramétrico basado en SfM/MVS en Agisoft Metashape aplicado a un subconjunto del dataset público USGS Eastern Dry Rocks (2021). El objetivo fue evaluar la factibilidad de generar nube de puntos, malla 3D, DEM y ortomosaico a partir de imágenes submarinas multivista, así como explorar la compatibilidad del flujo automatizado propuesto por ReefShape.

## Dataset
Se utilizó el data release del USGS:
https://cmgds.marine.usgs.gov/data-releases/datarelease/10.5066-P93RIIG9/

## Subconjunto trabajado
Se seleccionó un subtramo representativo correspondiente principalmente a las líneas 17 y 18, y se realizaron pruebas adicionales con un subconjunto multitrayectoria de las líneas 17 a 24.

## Flujo general
1. Selección espacial de imágenes a partir de coordenadas XY
2. Organización del subdataset
3. Alineación de imágenes en Metashape
4. Optimización de cámaras y limpieza de tie points
5. Generación de point cloud y mesh
6. Generación de DEM y ortomosaico
7. Prueba exploratoria de ReefShape

## Resultados
- Modelo 3D de subtramo representativo
- DEM de prueba
- Ortomosaico de subtramo
- Evaluación de limitaciones de ensamblaje entre chunks

## Limitaciones
La automatización completa mediante ReefShape no fue reproducible para el conjunto de datos ampliado debido a restricciones de almacenamiento temporal, complejidad geométrica del bloque y problemas de boundary/compatibilidad del script.