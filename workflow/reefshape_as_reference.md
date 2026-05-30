# ReefShape como referencia metodologica

Este proyecto toma ReefShape como referencia conceptual para estructurar un flujo reproducible de fotogrametria submarina, pero no depende de una ejecucion completa de ReefShape para generar los productos finales. La comparacion se usa para ordenar las etapas, documentar parametros y contrastar los resultados obtenidos manualmente en Agisoft Metashape.

## Rol dentro del proyecto

ReefShape se considera una guia de automatizacion para procesos SfM/MVS aplicados a arrecifes. En este repositorio se usa como referencia para:

- Definir una secuencia estandar de procesamiento: alineacion, nube densa, malla, DEM y ortomosaico.
- Mantener parametros explicitos para que las pruebas puedan repetirse.
- Comparar el flujo automatizado con el flujo manual realizado en Metashape.
- Identificar limitaciones practicas al procesar bloques submarinos multitrayectoria.

## Equivalencia con el flujo en Metashape

| Etapa de ReefShape | Etapa equivalente en este proyecto | Producto esperado |
| --- | --- | --- |
| Ingesta de imagenes | Carga del subconjunto USGS corregido | Chunk con fotografias |
| Feature matching | Alineacion de camaras | Camaras orientadas y tie points |
| Dense reconstruction | Construccion de nube densa | Nube de puntos densa |
| Surface reconstruction | Malla 3D desde nube densa | Modelo 3D texturizable |
| Elevation model | DEM desde nube densa | Modelo digital de elevacion |
| Orthoprojection | Ortomosaico sobre DEM | Ortoimagen georreferenciada |

## Decisiones adoptadas

Para el conjunto de imagenes EDR 17-24 se prioriza un procesamiento de calidad media, porque el bloque ampliado aumenta el consumo de memoria y almacenamiento temporal. La seleccion de parametros busca balancear reproducibilidad, tiempo de procesamiento y estabilidad del proyecto.

El ajuste previo aplicado a las imagenes se describe como correccion colorimetrica relativa. No se apoya en cartas de color ni en una referencia fisica medida en campo; por tanto, se entiende como una compensacion visual basada en estimaciones de perdida de color bajo el agua y balance de blancos.

Parametros base:

- Accuracy: `medium`
- Generic preselection: activado
- Reference preselection: activado
- Key point limit: `40000`
- Tie point limit: `4000`
- Dense cloud quality: `medium`
- Dense cloud filtering: `mild`
- Mesh source: `dense_cloud`
- DEM source: `dense_cloud`
- Orthomosaic surface: `dem`

## Limitaciones observadas

La automatizacion completa inspirada en ReefShape puede fallar si el bloque supera la capacidad de almacenamiento temporal, si existen discontinuidades geometricas entre trayectorias o si los limites del area no se interpretan correctamente por el script. Por eso el flujo automatizado propuesto en este repositorio debe entenderse como una version controlada y reproducible del procesamiento, no como una sustitucion directa del flujo manual de validacion.

## Uso recomendado

1. Corregir colorimétricamente las imágenes de entrada mediante una normalización relativa.
2. Verificar que las imagenes corregidas conserven metadatos utiles.
3. Ejecutar `scripts/05_run_metashape_workflow.py` desde Metashape.
4. Revisar visualmente la alineacion y limpiar tie points si es necesario.
5. Validar DEM, ortomosaico y malla antes de usarlos en el informe.
