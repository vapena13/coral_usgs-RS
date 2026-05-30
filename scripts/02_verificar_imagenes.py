"""
Verifica las imágenes corregidas y elimina las que estén dañadas o no se puedan abrir.
Uso: python verificar_imagenes.py
"""

from pathlib import Path
import numpy as np
import rasterio

# =========================
# CONFIGURACIÓN
# =========================
INPUT_DIR = Path(r"D:\coral_proyecto\SQUID5_EDR_2021_dataset_corregido")
EXTENSIONS = {".tif", ".tiff", ".TIF", ".TIFF"}
# =========================

def verificar(path: Path) -> tuple[bool, str]:
    try:
        with rasterio.open(path) as src:
            if src.count < 3:
                return False, f"menos de 3 bandas ({src.count})"
            data = src.read()
            if data is None or data.size == 0:
                return False, "lectura vacía"
            if np.all(data == 0):
                return False, "imagen completamente negra"
        return True, "OK"
    except Exception as e:
        return False, str(e)

def main():
    imagenes = sorted([p for p in INPUT_DIR.rglob("*") if p.suffix in EXTENSIONS])

    if not imagenes:
        print(f"No se encontraron imágenes en: {INPUT_DIR}")
        return

    print(f"Verificando {len(imagenes)} imágenes en: {INPUT_DIR}\n")

    ok = 0
    eliminadas = 0

    for i, img in enumerate(imagenes, 1):
        valida, msg = verificar(img)
        if valida:
            print(f"[{i}/{len(imagenes)}] {img.name} — OK")
            ok += 1
        else:
            print(f"[{i}/{len(imagenes)}] {img.name} — DAÑADA ({msg}) → eliminando...")
            img.unlink()
            eliminadas += 1

    print(f"\nResultado: {ok} válidas, {eliminadas} eliminadas.")

if __name__ == "__main__":
    main()