# Flujo de automatizacion en Metashape

Este archivo documenta la configuracion usada para automatizar una prueba del subconjunto EDR 17-24 sin ajuste colorimetrico previo. El script asociado es `scripts/05_run_metashape_workflow.py`.

Esta configuracion permite comparar el flujo automatizado sobre las imagenes originales frente al procesamiento con correccion colorimetrica relativa. El nombre del proyecto y la carpeta de resultados incluyen `sin_corregir` para evitar mezclar salidas entre corridas.

## Configuracion

```json
{
  "input_images": "D:/coral_proyecto/SQUID5_EDR_2021_dataset_corregido",
  "project_path": "D:/coral_proyecto/metashape_projects/EDR_17_24_corregido_flujo_final_mvs_v2.psx",
  "output_dir": "D:/coral_proyecto/resultados_informe2/EDR_17_24_corregido_flujo_final_mvs_v2",
  "alignment": {
    "accuracy": "medium",
    "generic_preselection": true,
    "reference_preselection": false,
    "keypoint_limit": 40000,
    "tiepoint_limit": 4000
  },
  "dense_cloud": {
    "quality": "low",
    "filtering": "mild"
  },
  "mesh": {
    "source_data": "dense_cloud",
    "surface_type": "arbitrary",
    "interpolation": true
  },
  "dem": {
    "source_data": "dense_cloud",
    "interpolation": true
  },
  "orthomosaic": {
    "surface": "dem",
    "blending": "mosaic",
    "hole_filling": true
  }
}
```

Nota: este script automatiza las etapas principales del flujo, pero no reemplaza la revisión visual de la alineación ni la depuración manual de tie points. En el procesamiento final del informe, la limpieza de tie points se realizó de forma controlada en Metashape antes de continuar con los productos densos.

## Productos esperados

El script guarda el proyecto de Metashape y exporta, cuando la etapa correspondiente se completa correctamente:

- Nube densa: `dense_cloud.las`
- Malla: `mesh.obj`
- DEM: `dem.tif`
- Ortomosaico: `orthomosaic.tif`

## Ejecucion

Desde la consola de Metashape o usando `metashape.exe -r`:

```powershell
metashape.exe -r scripts/05_run_metashape_workflow.py
```

El script lee la configuracion anterior desde este archivo, por lo que los cambios de rutas o parametros deben hacerse en el bloque JSON de `workflow/automation_workflow.md`.
