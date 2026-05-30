"""
Corrección colorimétrica relativa de imágenes subacuáticas RGB
con preservación de metadata raster y copia de metadata EXIF.

Requisitos:
    pip install rasterio numpy
    exiftool instalado y disponible en PATH

Uso:
    python correccion_imagenes_exif.py
"""

from pathlib import Path
import subprocess
import sys

import numpy as np
import rasterio


# =========================
# CONFIGURACIÓN
# =========================

INPUT_DIR = Path(r"D:/coral_proyecto/SQUID5_EDR_2021_dataset")
OUTPUT_DIR = Path(r"D:/coral_proyecto/SQUID5_EDR_2021_dataset_corregido")
percRemove = 0.0005
alpha_red = 1.0
alpha_blue = 0.0

EXTENSIONS = {".tif", ".tiff", ".TIF", ".TIFF"}

# Si tus imágenes están en subcarpetas por línea/cámara, deja True.
BUSCAR_SUBCARPETAS = True

# Copia metadata fotográfica con ExifTool.
EXIFTOOL_EXE = r"C:\Users\TUF Dash\AppData\Local\Programs\ExifTool\ExifTool.exe"
COPIAR_EXIF = True


# =========================
# FUNCIONES
# =========================

def verificar_exiftool() -> bool:
    try:
        result = subprocess.run(
            [EXIFTOOL_EXE, "-ver"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"ExifTool detectado. Versión: {result.stdout.strip()}")
        return True
    except Exception:
        print("Advertencia: ExifTool no está disponible en PATH.")
        print("Las imágenes se corregirán, pero no se copiará EXIF fotográfico.")
        return False


def copiar_metadata_exif(origen: Path, destino: Path) -> None:
    """
    Copia metadata fotográfica útil desde la imagen original hacia la corregida.

    Se evita copiar etiquetas estructurales del TIFF que pueden entrar en conflicto
    con la imagen corregida, especialmente porque la salida se guarda como uint8.
    """

    cmd = [
        EXIFTOOL_EXE,
        "-overwrite_original",
        "-TagsFromFile", str(origen),

        # Grupos principales útiles para fotogrametría y trazabilidad.
        "-EXIF:All",
        "-XMP:All",
        "-IPTC:All",
        "-ICC_Profile",

        # Evitar copiar tags estructurales que pueden quedar inconsistentes.
        "--IFD0:ImageWidth",
        "--IFD0:ImageHeight",
        "--IFD0:BitsPerSample",
        "--IFD0:Compression",
        "--IFD0:PhotometricInterpretation",
        "--IFD0:StripOffsets",
        "--IFD0:StripByteCounts",
        "--IFD0:RowsPerStrip",
        "--IFD0:SamplesPerPixel",
        "--IFD0:PlanarConfiguration",

        str(destino)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"ExifTool falló para {destino.name}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


def calcular_max_val(dtype_name: str, arr: np.ndarray) -> float:
    """
    Determina el rango dinámico para normalizar a [0, 1].
    """
    dtype = np.dtype(dtype_name)

    if np.issubdtype(dtype, np.integer):
        return float(np.iinfo(dtype).max)

    # Para float, se usa el valor máximo real si viene fuera de [0,1].
    max_real = float(np.nanmax(arr))
    return max_real if max_real > 1.0 else 1.0


def corregir_imagen(input_path: Path, output_path: Path, usar_exiftool: bool) -> str:
    with rasterio.open(input_path) as src:
        profile = src.profile.copy()
        img = src.read()

        # Tags raster del dataset y de cada banda.
        dataset_tags = src.tags()
        band_tags = {b: src.tags(b) for b in range(1, src.count + 1)}

    if img.shape[0] < 3:
        return f"SALTADA — menos de 3 bandas ({img.shape[0]})"

    rgb_raw = img[:3].astype(np.float32)

    max_val = calcular_max_val(profile.get("dtype", str(img.dtype)), rgb_raw)
    rgb = np.clip(rgb_raw / max_val, 0, 1)

    Ir, Ig, Ib = rgb[0], rgb[1], rgb[2]

    # Máscara para evitar que bordes negros o NoData contaminen las medias.
    valid = np.isfinite(Ir) & np.isfinite(Ig) & np.isfinite(Ib)
    valid &= (Ir > 0.01) | (Ig > 0.01) | (Ib > 0.01)

    if valid.sum() < 100:
        return "SALTADA — pocos píxeles válidos"

    Ir_mean = Ir[valid].mean()
    Ig_mean = Ig[valid].mean()
    Ib_mean = Ib[valid].mean()

    # (a) Compensación de color.
    Irc = Ir + alpha_red * (Ig_mean - Ir_mean) * (1 - Ir) * Ig
    Ibc = Ib + alpha_blue * (Ig_mean - Ib_mean)

    I = np.stack([Irc, Ig, Ibc], axis=0)
    I = np.clip(I, 0, 1)

    # (b) Balance de blancos Gray World usando solo píxeles válidos.
    R_avg = I[0][valid].mean()
    G_avg = I[1][valid].mean()
    B_avg = I[2][valid].mean()

    RGB_avg = np.array([R_avg, G_avg, B_avg], dtype=np.float32)
    gray_value = RGB_avg.mean()

    # Evita división por cero.
    RGB_avg = np.where(RGB_avg == 0, 1e-6, RGB_avg)
    scale = gray_value / RGB_avg

    Iwb = np.empty_like(I)
    for k in range(3):
        Iwb[k] = np.clip(I[k] * scale[k], 0, 1)

    # (c) Estiramiento de histograma con percentiles, usando píxeles válidos.
    gray_img = Iwb.mean(axis=0)
    gray_valid = gray_img[valid]
    gray_sorted = np.sort(gray_valid.ravel())

    ttl = gray_sorted.size
    cell_low = max(0, int(np.floor(percRemove * ttl)))
    cell_high = min(ttl - 1, ttl - cell_low - 1)

    gL = gray_sorted[cell_low]
    gH = gray_sorted[cell_high]

    if gH <= gL:
        return f"SALTADA — histograma plano (gL={gL:.4f}, gH={gH:.4f})"

    slope = 1.0 / (gH - gL)
    offset = -slope * gL

    Ifinal = np.clip(Iwb * slope + offset, 0, 1)

    # Mantener NoData visualmente negro si existían bordes vacíos.
    for k in range(3):
        Ifinal[k][~valid] = 0

    out = np.round(Ifinal * 255).astype(np.uint8)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Perfil GeoTIFF de salida.
    profile.update(
        driver="GTiff",
        dtype=rasterio.uint8,
        count=3,
        compress="LZW"
    )

    # El nodata original puede ser incompatible con uint8 si era >255.
    nodata = profile.get("nodata", None)
    if nodata is not None:
        try:
            nodata_float = float(nodata)
            if nodata_float < 0 or nodata_float > 255:
                profile.pop("nodata", None)
        except Exception:
            profile.pop("nodata", None)

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(out)

        # Conserva tags raster generales.
        if dataset_tags:
            dst.update_tags(**dataset_tags)

        # Conserva tags por banda para las primeras tres bandas.
        for b in range(1, min(3, len(band_tags)) + 1):
            if band_tags.get(b):
                dst.update_tags(b, **band_tags[b])

        # Marca trazabilidad del procesamiento.
        dst.update_tags(
            PROCESSING="Correccion colorimetrica relativa subacuatica",
            COLOR_CORRECTION="red_compensation_gray_world_histogram_stretch",
            ALPHA_RED=str(alpha_red),
            ALPHA_BLUE=str(alpha_blue),
            PERC_REMOVE=str(percRemove),
            SOURCE_FILE=input_path.name
        )

    # Copia EXIF/XMP/IPTC/ICC desde el original.
    if usar_exiftool:
        copiar_metadata_exif(input_path, output_path)

    return "OK"


def listar_imagenes(input_dir: Path):
    if BUSCAR_SUBCARPETAS:
        return sorted([
            p for p in input_dir.rglob("*")
            if p.is_file() and p.suffix in EXTENSIONS
        ])

    return sorted([
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix in EXTENSIONS
    ])


def construir_salida(input_path: Path) -> Path:
    relative = input_path.relative_to(INPUT_DIR)
    return OUTPUT_DIR / relative

def main():
    if not INPUT_DIR.exists():
        print(f"No existe la carpeta de entrada:\n{INPUT_DIR}")
        sys.exit(1)

    usar_exiftool = COPIAR_EXIF and verificar_exiftool()

    imagenes = listar_imagenes(INPUT_DIR)

    if not imagenes:
        print(f"No se encontraron imágenes TIFF en:\n{INPUT_DIR}")
        sys.exit(1)

    print(f"\nImágenes encontradas: {len(imagenes)}")
    print(f"Carpeta de salida: {OUTPUT_DIR}\n")

    ok = 0
    skipped = 0
    errores = 0

    for i, img_path in enumerate(imagenes, 1):
        out_path = construir_salida(img_path)

        print(f"[{i}/{len(imagenes)}] {img_path.name}", end="  ", flush=True)

        if out_path.exists():
            print("YA EXISTE — saltada")
            skipped += 1
            continue

        try:
            estado = corregir_imagen(img_path, out_path, usar_exiftool)
            print(estado)

            if estado == "OK":
                ok += 1
            else:
                skipped += 1

        except Exception as e:
            print(f"ERROR — {e}")
            errores += 1

    print("\nFinalizado.")
    print(f"Corregidas: {ok}")
    print(f"Saltadas: {skipped}")
    print(f"Errores: {errores}")
    print(f"Salida:\n{OUTPUT_DIR}")


if __name__ == "__main__":
    main()