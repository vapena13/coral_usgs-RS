"""
Prototipo de automatizacion por etapas para Agisoft Metashape.

Version ajustada para el proyecto SQUID-5 / Eastern Dry Rocks.

Idea del flujo:
1. Crear proyecto con fotos.
2. Alinear y optimizar camaras.
3. Exportar camaras alineadas.
4. Crear un proyecto limpio e importar esas camaras.
5. Construir mapas de profundidad.
6. Construir nube densa.
7. Exportar nube densa a LAS y recuperarla en un proyecto limpio.
8. Construir malla, DEM y ortomosaico desde el checkpoint recuperado.

El objetivo de esta version es completar el flujo por etapas, evitando depender
de un unico PSX largo. Cada producto critico se guarda como checkpoint y, cuando
es posible, tambien se exporta a un archivo recuperable.

Uso desde Metashape:
    Tools > Run Script...
    scripts/05_run_metashape_workflow.py

El script lee el bloque JSON de:
    workflow/automation_workflow.md
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path

try:
    import Metashape
except ImportError:
    raise RuntimeError(
        "Este script debe ejecutarse con el Python incluido en Agisoft Metashape."
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "workflow" / "automation_workflow.md"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".tif", ".tiff", ".png"}


# ---------------------------------------------------------
# Compatibilidad entre versiones de Metashape
# ---------------------------------------------------------
def ms_attr(name, fallback=None):
    return getattr(Metashape, name, fallback)


# matchPhotos downscale:
# Highest=0, High=1, Medium=2, Low=4, Lowest=8
ACCURACY_MAP = {
    "highest": 0,
    "high": 1,
    "medium": 2,
    "low": 4,
    "lowest": 8,
}

QUALITY_MAP = {
    "ultra": ms_attr("UltraQuality", 1),
    "high": ms_attr("HighQuality", 2),
    "medium": ms_attr("MediumQuality", 4),
    "low": ms_attr("LowQuality", 8),
    "lowest": ms_attr("LowestQuality", 16),
}

FILTERING_MAP = {
    "mild": ms_attr("MildFiltering", 1),
    "moderate": ms_attr("ModerateFiltering", 2),
    "aggressive": ms_attr("AggressiveFiltering", 3),
    "disabled": ms_attr("NoFiltering", 0),
}

DENSE_SOURCE_DATA = ms_attr("DenseCloudData", None)
POINT_CLOUD_DATA = ms_attr("PointCloudData", None)
DEPTH_MAPS_DATA = ms_attr("DepthMapsData", None)
MODEL_DATA = ms_attr("ModelData", None)
ELEVATION_DATA = ms_attr("ElevationData", None)
ORTHOMOSAIC_DATA = ms_attr("OrthomosaicData", None)

SOURCE_DATA_MAP = {
    "dense_cloud": DENSE_SOURCE_DATA,
    "model": MODEL_DATA,
    "dem": ELEVATION_DATA,
}

SURFACE_TYPE_MAP = {
    "arbitrary": ms_attr("Arbitrary", 0),
    "height_field": ms_attr("HeightField", 1),
}

ENABLED_INTERPOLATION = ms_attr("EnabledInterpolation", 1)
DISABLED_INTERPOLATION = ms_attr("DisabledInterpolation", 0)

BLENDING_MAP = {
    "mosaic": ms_attr("MosaicBlending", 0),
    "average": ms_attr("AverageBlending", 1),
    "disabled": ms_attr("DisabledBlending", 2),
}


def load_config(path):
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        raise ValueError("No se encontro un bloque JSON en {}".format(path))
    return json.loads(match.group(1))


def list_images(input_dir):
    images = sorted(
        p for p in input_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not images:
        raise IOError("No se encontraron imagenes en {}".format(input_dir))
    return [str(p) for p in images]


def active_document(clear=True):
    if hasattr(Metashape, "app") and getattr(Metashape.app, "document", None):
        doc = Metashape.app.document
        if clear:
            doc.clear()
        return doc
    return Metashape.Document()


def save_project(document, project_path):
    project_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(project_path))


def open_project_chunk(project_path):
    document = active_document(clear=True)
    document.open(str(project_path))
    if not document.chunks:
        raise RuntimeError("El proyecto no contiene chunks: {}".format(project_path))
    chunk = document.chunk or document.chunks[0]
    return document, chunk


def camera_is_aligned(camera):
    return getattr(camera, "transform", None) is not None


def count_aligned_cameras(chunk):
    return sum(1 for camera in chunk.cameras if camera_is_aligned(camera))


def count_enabled_cameras(chunk):
    return sum(1 for camera in chunk.cameras if getattr(camera, "enabled", True))


def prepare_cameras_for_processing(chunk):
    aligned = count_aligned_cameras(chunk)
    enabled = count_enabled_cameras(chunk)
    print(
        "Camaras antes de MVS: alineadas {}/{}; habilitadas {}/{}".format(
            aligned,
            len(chunk.cameras),
            enabled,
            len(chunk.cameras),
        )
    )

    for camera in chunk.cameras:
        if camera_is_aligned(camera):
            try:
                camera.enabled = True
            except Exception:
                pass
            try:
                camera.selected = True
            except Exception:
                pass

    return aligned


def write_alignment_check(chunk, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["camera", "aligned"])
        for camera in chunk.cameras:
            writer.writerow([camera.label, int(camera_is_aligned(camera))])


def write_status(output_path, rows):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["stage", "status", "value", "note"])
        writer.writerows(rows)


def export_aligned_cameras(chunk, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        chunk.exportCameras(path=str(output_path))
    except TypeError:
        chunk.exportCameras(str(output_path))


def import_aligned_cameras(chunk, input_path):
    try:
        chunk.importCameras(path=str(input_path))
    except TypeError:
        chunk.importCameras(str(input_path))


def add_photos_chunk(document, images, label):
    chunk = document.addChunk()
    chunk.label = label
    chunk.crs = Metashape.CoordinateSystem("EPSG::4326")
    chunk.addPhotos(images)
    return chunk


def stage_paths(config_project_path, config_output_dir):
    """
    Crea rutas nuevas por corrida para evitar bloqueos de PSX anteriores.
    """
    project_path = Path(config_project_path)
    output_dir = Path(config_output_dir)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = "{}_{}".format(project_path.stem, run_id)
    project_dir = project_path.parent
    run_output = output_dir / stem

    return {
        "run_id": run_id,
        "photos_project": project_dir / "{}_01_photos.psx".format(stem),
        "aligned_project": project_dir / "{}_02_aligned.psx".format(stem),
        "imported_project": project_dir / "{}_03_imported_alignment.psx".format(stem),
        "sparse_project": project_dir / "{}_04_sparse_points.psx".format(stem),
        "depth_project": project_dir / "{}_05_depth_maps.psx".format(stem),
        "dense_project": project_dir / "{}_06_dense_cloud.psx".format(stem),
        "recovered_project": project_dir / "{}_07_recovered_from_las.psx".format(stem),
        "mesh_project": project_dir / "{}_08_mesh.psx".format(stem),
        "dem_project": project_dir / "{}_09_dem.psx".format(stem),
        "ortho_project": project_dir / "{}_10_orthomosaic.psx".format(stem),
        "output_dir": run_output,
        "alignment_check": run_output / "alignment_check.csv",
        "alignment_check_imported": run_output / "alignment_check_imported.csv",
        "aligned_cameras": run_output / "aligned_cameras.xml",
        "dense_cloud_las": run_output / "dense_cloud.las",
        "mesh_obj": run_output / "mesh.obj",
        "dem_tif": run_output / "dem.tif",
        "orthomosaic_tif": run_output / "orthomosaic.tif",
        "status": run_output / "automation_status.csv",
    }


def align_cameras_compatible(chunk, alignment):
    print("Alineando camaras...")

    try:
        chunk.matchPhotos(
            downscale=ACCURACY_MAP[alignment["accuracy"]],
            generic_preselection=alignment["generic_preselection"],
            reference_preselection=alignment["reference_preselection"],
            keypoint_limit=alignment["keypoint_limit"],
            tiepoint_limit=alignment["tiepoint_limit"],
        )
    except TypeError:
        # Algunas versiones antiguas usan accuracy en lugar de downscale.
        chunk.matchPhotos(
            accuracy=ACCURACY_MAP[alignment["accuracy"]],
            generic_preselection=alignment["generic_preselection"],
            reference_preselection=alignment["reference_preselection"],
            keypoint_limit=alignment["keypoint_limit"],
            tiepoint_limit=alignment["tiepoint_limit"],
        )

    chunk.alignCameras()
    aligned = count_aligned_cameras(chunk)
    print("Camaras alineadas: {}/{}".format(aligned, len(chunk.cameras)))

    if aligned == 0 and alignment.get("reference_preselection", False):
        print("No se alinearon camaras. Reintentando sin reference_preselection...")
        chunk.matchPhotos(
            downscale=ACCURACY_MAP[alignment["accuracy"]],
            generic_preselection=alignment["generic_preselection"],
            reference_preselection=False,
            keypoint_limit=alignment["keypoint_limit"],
            tiepoint_limit=alignment["tiepoint_limit"],
        )
        chunk.alignCameras()
        aligned = count_aligned_cameras(chunk)
        print("Camaras alineadas tras reintento: {}/{}".format(aligned, len(chunk.cameras)))

    if aligned == 0:
        raise RuntimeError("La alineacion termino con 0 camaras alineadas.")

    return aligned


def optimize_cameras_compatible(chunk):
    print("Optimizando camaras...")
    try:
        chunk.optimizeCameras(
            fit_f=True,
            fit_cx=True,
            fit_cy=True,
            fit_k1=True,
            fit_k2=True,
            fit_k3=True,
            fit_p1=True,
            fit_p2=True,
        )
    except TypeError:
        chunk.optimizeCameras()


def has_depth_maps(chunk):
    return bool(getattr(chunk, "depth_maps", None))


def has_sparse_product(chunk):
    tie_points = getattr(chunk, "tie_points", None)
    if tie_points:
        return True
    if hasattr(chunk, "tie_points"):
        return False
    return bool(getattr(chunk, "point_cloud", None))


def rebuild_sparse_product(chunk, alignment):
    print("Reconstruyendo matches/tie points sobre camaras importadas...")
    try:
        chunk.matchPhotos(
            downscale=ACCURACY_MAP[alignment["accuracy"]],
            generic_preselection=alignment["generic_preselection"],
            reference_preselection=False,
            keypoint_limit=alignment["keypoint_limit"],
            tiepoint_limit=alignment["tiepoint_limit"],
        )
    except TypeError:
        chunk.matchPhotos(
            accuracy=ACCURACY_MAP[alignment["accuracy"]],
            generic_preselection=alignment["generic_preselection"],
            reference_preselection=False,
            keypoint_limit=alignment["keypoint_limit"],
            tiepoint_limit=alignment["tiepoint_limit"],
        )

    if hasattr(chunk, "triangulatePoints"):
        try:
            chunk.triangulatePoints()
        except Exception as exc:
            print("triangulatePoints fallo; reintentando con alignCameras().")
            print("Detalle:", exc)
            chunk.alignCameras()
    else:
        chunk.alignCameras()


def has_dense_product(chunk):
    dense = getattr(chunk, "dense_cloud", None)
    if dense is None:
        return False

    try:
        points = getattr(dense, "points", None)
        if points is not None:
            return len(points) > 0
    except Exception:
        pass

    return True


def build_depth_maps_compatible(chunk, dense_config):
    print("Construyendo mapas de profundidad...")

    try:
        chunk.buildDepthMaps(
            downscale=QUALITY_MAP[dense_config["quality"]],
            filter_mode=FILTERING_MAP[dense_config["filtering"]],
        )
        print("Mapas de profundidad terminados sin excepcion.")
        return True
    except TypeError:
        print("buildDepthMaps no acepto parametros; reintentando sin argumentos...")
        chunk.buildDepthMaps()
        return True
    except Exception as exc:
        # En este equipo Metashape ha lanzado Assertion al final de BuildDepthMaps,
        # aun cuando el procesamiento parece haber generado archivos intermedios.
        # Solo se continua si Metashape deja depth maps detectables en el chunk.
        print("buildDepthMaps lanzo una excepcion.")
        print("Detalle:", exc)
        print("Se continuara solo si quedaron depth maps utilizables.")
        return False


def build_dense_cloud_compatible(chunk, dense_config):
    """
    Construye mapas de profundidad y luego fuerza la creacion de Dense Cloud.

    Para Metashape 1.8.x, el flujo que corresponde al boton
    Workflow > Build Dense Cloud es buildDepthMaps() + buildDenseCloud().
    No se usa buildPointCloud() porque en algunas versiones puede no crear
    el producto Dense Cloud esperado o puede corresponder a otra API.
    """
    if has_depth_maps(chunk):
        print("Depth maps ya disponibles; se continua con Dense Cloud.")
    else:
        raise RuntimeError(
            "No hay depth maps utilizables para construir Dense Cloud. "
            "Se conserva el checkpoint anterior para revision."
        )

    print("Construyendo dense cloud...")
    if hasattr(chunk, "buildDenseCloud"):
        try:
            chunk.buildDenseCloud()
        except TypeError:
            chunk.buildDenseCloud()
    else:
        raise RuntimeError(
            "Esta version de Metashape no expone buildDenseCloud(). "
            "No se puede crear Dense Cloud desde el script con esta API."
        )

    if has_dense_product(chunk):
        print("Dense cloud creada correctamente.")
    else:
        raise RuntimeError(
            "buildDenseCloud termino, pero no se detecto chunk.dense_cloud. "
            "El proyecto conserva alineacion y tie points, pero no dense cloud."
        )

    return True


def export_dense_cloud_compatible(chunk, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not has_dense_product(chunk):
        raise RuntimeError("No existe Dense Cloud para exportar.")

    print("Exportando Dense Cloud a LAS...")

    las_format = ms_attr("PointsFormatLAS", ms_attr("PointCloudFormatLAS", None))
    dense_source = ms_attr("DenseCloudData", None)

    if hasattr(chunk, "exportPoints"):
        try:
            if las_format is not None and dense_source is not None:
                chunk.exportPoints(
                    path=str(output_path),
                    source_data=dense_source,
                    format=las_format,
                )
            else:
                chunk.exportPoints(path=str(output_path))
            return True
        except TypeError:
            chunk.exportPoints(str(output_path))
            return True

    if hasattr(chunk, "exportPointCloud"):
        try:
            if las_format is not None and dense_source is not None:
                chunk.exportPointCloud(
                    path=str(output_path),
                    source_data=dense_source,
                    format=las_format,
                )
            else:
                chunk.exportPointCloud(path=str(output_path))
            return True
        except TypeError:
            chunk.exportPointCloud(str(output_path))
            return True

    raise RuntimeError("No se encontro metodo compatible para exportar la nube densa.")


def import_dense_cloud_compatible(chunk, input_path):
    if not input_path.exists():
        raise IOError("No existe el LAS de nube densa: {}".format(input_path))

    print("Importando Dense Cloud desde LAS...")

    if hasattr(chunk, "importPoints"):
        try:
            chunk.importPoints(path=str(input_path))
            return True
        except TypeError:
            chunk.importPoints(str(input_path))
            return True

    if hasattr(chunk, "importPointCloud"):
        try:
            chunk.importPointCloud(path=str(input_path))
            return True
        except TypeError:
            chunk.importPointCloud(str(input_path))
            return True

    raise RuntimeError("No se encontro metodo compatible para importar LAS.")


def has_model_product(chunk):
    return bool(getattr(chunk, "model", None))


def has_dem_product(chunk):
    return bool(getattr(chunk, "elevation", None))


def has_orthomosaic_product(chunk):
    return bool(getattr(chunk, "orthomosaic", None))


def build_model_compatible(chunk, mesh_config):
    print("Construyendo malla...")
    source_data = SOURCE_DATA_MAP.get(mesh_config["source_data"], DENSE_SOURCE_DATA)
    surface_type = SURFACE_TYPE_MAP.get(mesh_config["surface_type"], SURFACE_TYPE_MAP["arbitrary"])
    interpolation = (
        ENABLED_INTERPOLATION
        if mesh_config.get("interpolation", True)
        else DISABLED_INTERPOLATION
    )

    try:
        chunk.buildModel(
            source_data=source_data,
            surface_type=surface_type,
            interpolation=interpolation,
        )
    except TypeError:
        chunk.buildModel()

    if not has_model_product(chunk):
        raise RuntimeError("buildModel termino, pero no se detecto chunk.model.")

    return True


def export_model_compatible(chunk, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not has_model_product(chunk):
        raise RuntimeError("No existe malla para exportar.")

    model_format = ms_attr("ModelFormatOBJ", None)
    try:
        if model_format is not None:
            chunk.exportModel(path=str(output_path), format=model_format)
        else:
            chunk.exportModel(path=str(output_path))
    except TypeError:
        chunk.exportModel(str(output_path))

    return True


def build_dem_compatible(chunk, dem_config):
    print("Construyendo DEM...")
    interpolation = (
        ENABLED_INTERPOLATION
        if dem_config.get("interpolation", True)
        else DISABLED_INTERPOLATION
    )
    source_data = SOURCE_DATA_MAP.get(dem_config["source_data"], DENSE_SOURCE_DATA)

    try:
        chunk.buildDem(source_data=source_data, interpolation=interpolation)
    except Exception as exc:
        print("No se pudo construir DEM desde la fuente configurada.")
        print("Detalle:", exc)

        if has_model_product(chunk) and MODEL_DATA is not None:
            print("Reintentando DEM desde model...")
            chunk.buildDem(source_data=MODEL_DATA, interpolation=interpolation)
        else:
            raise

    if not has_dem_product(chunk):
        raise RuntimeError("buildDem termino, pero no se detecto chunk.elevation.")

    return True


def export_dem_compatible(chunk, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not has_dem_product(chunk):
        raise RuntimeError("No existe DEM para exportar.")

    try:
        if ELEVATION_DATA is not None:
            chunk.exportRaster(path=str(output_path), source_data=ELEVATION_DATA)
        else:
            chunk.exportRaster(path=str(output_path))
    except TypeError:
        chunk.exportRaster(str(output_path))

    return True


def build_orthomosaic_compatible(chunk, ortho_config):
    print("Construyendo ortomosaico...")
    surface_data = SOURCE_DATA_MAP.get(ortho_config["surface"], ELEVATION_DATA)
    blending_mode = BLENDING_MAP.get(ortho_config["blending"], BLENDING_MAP["mosaic"])

    try:
        chunk.buildOrthomosaic(
            surface_data=surface_data,
            blending_mode=blending_mode,
            fill_holes=ortho_config.get("hole_filling", True),
        )
    except TypeError:
        chunk.buildOrthomosaic()

    if not has_orthomosaic_product(chunk):
        raise RuntimeError("buildOrthomosaic termino, pero no se detecto chunk.orthomosaic.")

    return True


def export_orthomosaic_compatible(chunk, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not has_orthomosaic_product(chunk):
        raise RuntimeError("No existe ortomosaico para exportar.")

    try:
        if ORTHOMOSAIC_DATA is not None:
            chunk.exportRaster(path=str(output_path), source_data=ORTHOMOSAIC_DATA)
        else:
            chunk.exportRaster(path=str(output_path))
    except TypeError:
        chunk.exportRaster(str(output_path))

    return True


def main():
    config = load_config(CONFIG_PATH)

    input_dir = Path(config["input_images"])
    images = list_images(input_dir)

    paths = stage_paths(
        Path(config["project_path"]),
        Path(config["output_dir"]),
    )

    status_rows = []
    print("Run ID:", paths["run_id"])
    print("Imagenes encontradas:", len(images))
    print("Carpeta de salida:", paths["output_dir"])

    # -----------------------------------------------------
    # 01. Proyecto con fotos
    # -----------------------------------------------------
    doc = active_document(clear=True)
    chunk = add_photos_chunk(doc, images, "EDR_17_24_auto_photos")
    save_project(doc, paths["photos_project"])
    print("Checkpoint 01 guardado:", paths["photos_project"])
    status_rows.append(["01_photos", "ok", len(images), str(paths["photos_project"])])

    # -----------------------------------------------------
    # 02. Alineacion y exportacion de camaras
    # -----------------------------------------------------
    align_cameras_compatible(chunk, config["alignment"])
    optimize_cameras_compatible(chunk)
    aligned_after = count_aligned_cameras(chunk)

    write_alignment_check(chunk, paths["alignment_check"])
    export_aligned_cameras(chunk, paths["aligned_cameras"])
    save_project(doc, paths["aligned_project"])

    print("Checkpoint 02 guardado:", paths["aligned_project"])
    print("Camaras alineadas tras optimizacion: {}/{}".format(aligned_after, len(chunk.cameras)))
    status_rows.append([
        "02_alignment",
        "ok",
        "{}/{}".format(aligned_after, len(chunk.cameras)),
        str(paths["aligned_project"]),
    ])

    # -----------------------------------------------------
    # 03. Proyecto limpio con camaras importadas
    # -----------------------------------------------------
    doc.clear()
    imported_chunk = add_photos_chunk(doc, images, "EDR_17_24_auto_imported_alignment")
    import_aligned_cameras(imported_chunk, paths["aligned_cameras"])
    imported_aligned = count_aligned_cameras(imported_chunk)

    write_alignment_check(imported_chunk, paths["alignment_check_imported"])
    save_project(doc, paths["imported_project"])

    print("Checkpoint 03 guardado:", paths["imported_project"])
    print("Camaras alineadas importadas: {}/{}".format(imported_aligned, len(imported_chunk.cameras)))
    status_rows.append([
        "03_import_alignment",
        "ok",
        "{}/{}".format(imported_aligned, len(imported_chunk.cameras)),
        str(paths["imported_project"]),
    ])

    if imported_aligned == 0:
        write_status(paths["status"], status_rows)
        raise RuntimeError("La importacion de camaras produjo 0 camaras alineadas.")

    print("Reabriendo checkpoint 02 para procesamiento denso nativo...")
    doc, processing_chunk = open_project_chunk(paths["aligned_project"])
    native_aligned = prepare_cameras_for_processing(processing_chunk)

    if native_aligned == 0:
        print("Checkpoint 02 no conserva camaras alineadas; se usara el chunk importado por XML.")
        doc, processing_chunk = open_project_chunk(paths["imported_project"])
        native_aligned = prepare_cameras_for_processing(processing_chunk)

    if native_aligned == 0:
        write_status(paths["status"], status_rows)
        raise RuntimeError("No hay camaras alineadas disponibles para MVS.")

    # -----------------------------------------------------
    # 04. Sparse points / tie points
    # -----------------------------------------------------
    if not has_sparse_product(processing_chunk):
        rebuild_sparse_product(processing_chunk, config["alignment"])
    else:
        print("Tie points/nube dispersa ya disponibles.")

    sparse_ok = has_sparse_product(processing_chunk)
    save_project(doc, paths["sparse_project"])
    print("Checkpoint 04 guardado:", paths["sparse_project"])
    status_rows.append([
        "04_sparse_points",
        "ok" if sparse_ok else "failed",
        int(sparse_ok),
        str(paths["sparse_project"]),
    ])

    if not sparse_ok:
        write_status(paths["status"], status_rows)
        raise RuntimeError("No se pudo reconstruir tie points antes de depth maps.")

    # -----------------------------------------------------
    # 05. Depth maps
    # -----------------------------------------------------
    depth_ok = build_depth_maps_compatible(processing_chunk, config["dense_cloud"])
    save_project(doc, paths["depth_project"])
    print("Checkpoint 05 guardado:", paths["depth_project"])
    status_rows.append([
        "05_depth_maps",
        "ok" if depth_ok else "warning",
        int(bool(has_depth_maps(processing_chunk))),
        str(paths["depth_project"]),
    ])

    # -----------------------------------------------------
    # 06. Dense cloud
    # -----------------------------------------------------
    dense_ok = False
    try:
        print("Construyendo nube densa desde alineacion nativa...")
        dense_ok = build_dense_cloud_compatible(processing_chunk, config["dense_cloud"])

    except Exception as exc:
        print("Error construyendo nube densa.")
        print("Detalle:", exc)
        dense_ok = has_dense_product(processing_chunk)

    save_project(doc, paths["dense_project"])
    print("Checkpoint 06 guardado:", paths["dense_project"])
    status_rows.append([
        "06_dense_cloud",
        "ok" if dense_ok else "failed",
        int(dense_ok),
        str(paths["dense_project"]),
    ])

    if dense_ok:
        exported = export_dense_cloud_compatible(processing_chunk, paths["dense_cloud_las"])
        status_rows.append([
            "06_export_dense_cloud",
            "ok" if exported else "failed",
            int(exported),
            str(paths["dense_cloud_las"]),
        ])
    else:
        exported = False
        print("No se detecto nube densa creada; no se exporta LAS.")

    # -----------------------------------------------------
    # 07. Proyecto limpio recuperado desde XML + LAS
    # -----------------------------------------------------
    recovered_ok = False
    if exported:
        doc.clear()
        recovered_chunk = add_photos_chunk(doc, images, "EDR_17_24_auto_recovered_from_las")
        import_aligned_cameras(recovered_chunk, paths["aligned_cameras"])
        import_dense_cloud_compatible(recovered_chunk, paths["dense_cloud_las"])
        recovered_ok = True
        save_project(doc, paths["recovered_project"])
        print("Checkpoint 07 guardado:", paths["recovered_project"])
    else:
        print("No se crea checkpoint 07 porque no hay LAS exportado.")

    status_rows.append([
        "07_recover_from_las",
        "ok" if recovered_ok else "skipped",
        int(recovered_ok),
        str(paths["recovered_project"]),
    ])

    # -----------------------------------------------------
    # 08. Mesh desde el checkpoint recuperado
    # -----------------------------------------------------
    mesh_ok = False
    if recovered_ok:
        try:
            mesh_ok = build_model_compatible(recovered_chunk, config["mesh"])
        except Exception as exc:
            print("Error construyendo malla.")
            print("Detalle:", exc)
            mesh_ok = has_model_product(recovered_chunk)

        save_project(doc, paths["mesh_project"])
        print("Checkpoint 08 guardado:", paths["mesh_project"])
        status_rows.append([
            "08_mesh",
            "ok" if mesh_ok else "failed",
            int(mesh_ok),
            str(paths["mesh_project"]),
        ])

        if mesh_ok:
            try:
                exported_mesh = export_model_compatible(recovered_chunk, paths["mesh_obj"])
            except Exception as exc:
                print("No se pudo exportar la malla.")
                print("Detalle:", exc)
                exported_mesh = False

            status_rows.append([
                "08_export_mesh",
                "ok" if exported_mesh else "failed",
                int(exported_mesh),
                str(paths["mesh_obj"]),
            ])
    else:
        print("Se omite malla porque no existe checkpoint recuperado.")
        status_rows.append(["08_mesh", "skipped", 0, str(paths["mesh_project"])])

    # -----------------------------------------------------
    # 09. DEM
    # -----------------------------------------------------
    dem_ok = False
    if recovered_ok and (has_dense_product(recovered_chunk) or mesh_ok):
        try:
            reopen_path = paths["mesh_project"] if mesh_ok else paths["recovered_project"]
            print("Reabriendo checkpoint antes de DEM:", reopen_path)
            doc, recovered_chunk = open_project_chunk(reopen_path)
            dem_ok = build_dem_compatible(recovered_chunk, config["dem"])
        except Exception as exc:
            print("Error construyendo DEM.")
            print("Detalle:", exc)
            dem_ok = has_dem_product(recovered_chunk)

        save_project(doc, paths["dem_project"])
        print("Checkpoint 09 guardado:", paths["dem_project"])
        status_rows.append([
            "09_dem",
            "ok" if dem_ok else "failed",
            int(dem_ok),
            str(paths["dem_project"]),
        ])

        if dem_ok:
            try:
                exported_dem = export_dem_compatible(recovered_chunk, paths["dem_tif"])
            except Exception as exc:
                print("No se pudo exportar el DEM.")
                print("Detalle:", exc)
                exported_dem = False

            status_rows.append([
                "09_export_dem",
                "ok" if exported_dem else "failed",
                int(exported_dem),
                str(paths["dem_tif"]),
            ])
    else:
        print("Se omite DEM porque no hay nube densa/malla recuperada.")
        status_rows.append(["09_dem", "skipped", 0, str(paths["dem_project"])])

    # -----------------------------------------------------
    # 10. Orthomosaic
    # -----------------------------------------------------
    ortho_ok = False
    if recovered_ok and dem_ok:
        try:
            ortho_ok = build_orthomosaic_compatible(recovered_chunk, config["orthomosaic"])
        except Exception as exc:
            print("Error construyendo ortomosaico.")
            print("Detalle:", exc)
            ortho_ok = has_orthomosaic_product(recovered_chunk)

        save_project(doc, paths["ortho_project"])
        print("Checkpoint 10 guardado:", paths["ortho_project"])
        status_rows.append([
            "10_orthomosaic",
            "ok" if ortho_ok else "failed",
            int(ortho_ok),
            str(paths["ortho_project"]),
        ])

        if ortho_ok:
            try:
                exported_ortho = export_orthomosaic_compatible(
                    recovered_chunk,
                    paths["orthomosaic_tif"],
                )
            except Exception as exc:
                print("No se pudo exportar el ortomosaico.")
                print("Detalle:", exc)
                exported_ortho = False

            status_rows.append([
                "10_export_orthomosaic",
                "ok" if exported_ortho else "failed",
                int(exported_ortho),
                str(paths["orthomosaic_tif"]),
            ])
    else:
        print("Se omite ortomosaico porque no existe DEM.")
        status_rows.append(["10_orthomosaic", "skipped", 0, str(paths["ortho_project"])])

    write_status(paths["status"], status_rows)

    print("Flujo por etapas terminado.")
    print("Estado:", paths["status"])
    print("Proyecto 01:", paths["photos_project"])
    print("Proyecto 02:", paths["aligned_project"])
    print("Proyecto 03:", paths["imported_project"])
    print("Proyecto 04:", paths["sparse_project"])
    print("Proyecto 05:", paths["depth_project"])
    print("Proyecto 06:", paths["dense_project"])
    print("Proyecto 07:", paths["recovered_project"])
    print("Proyecto 08:", paths["mesh_project"])
    print("Proyecto 09:", paths["dem_project"])
    print("Proyecto 10:", paths["ortho_project"])
    print("LAS:", paths["dense_cloud_las"])
    print("OBJ:", paths["mesh_obj"])
    print("DEM:", paths["dem_tif"])
    print("Ortomosaico:", paths["orthomosaic_tif"])


if __name__ == "__main__":
    main()
