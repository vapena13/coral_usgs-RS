from pathlib import Path
import shutil
import pandas as pd

# =========================
# CONFIGURACIÓN
# =========================
EXCEL_FILE = r"D:\coral_proyecto\images_cut\select_images.xls"
SOURCE_ROOT = r"D:\coral_proyecto\images"
DEST_ROOT = r"D:\coral_proyecto\SQUID5_EDR_2021_dataset"
FILENAME_COLUMN = "ImageFile"

# True = solo prueba, no copia nada
# False = copia de verdad
DRY_RUN = False
# =========================

excel_file = Path(EXCEL_FILE)
source_root = Path(SOURCE_ROOT)
dest_root = Path(DEST_ROOT)

dest_root.mkdir(parents=True, exist_ok=True)

# Leer Excel
try:
    df = pd.read_excel(excel_file)
except Exception as e:
    raise RuntimeError(
        f"No se pudo leer el Excel.\n"
        f"Si es .xls antiguo, instala xlrd con:\n"
        f"pip install xlrd\n\n"
        f"Error original: {e}"
    )

if FILENAME_COLUMN not in df.columns:
    raise ValueError(
        f"La columna '{FILENAME_COLUMN}' no existe.\n"
        f"Columnas disponibles: {list(df.columns)}"
    )

selected_names = (
    df[FILENAME_COLUMN]
    .dropna()
    .astype(str)
    .str.strip()
    .tolist()
)

selected_names_set = set(selected_names)

print(f"Archivos listados en Excel: {len(selected_names_set)}")

# Buscar todos los archivos dentro de la carpeta fuente
all_files = [p for p in source_root.rglob("*") if p.is_file()]

# Indexar por nombre
name_to_paths = {}
for p in all_files:
    name_to_paths.setdefault(p.name, []).append(p)

copied = []
missing = []
duplicates = []

for name in sorted(selected_names_set):
    matches = name_to_paths.get(name, [])

    if len(matches) == 0:
        missing.append({"ImageFile": name})
        continue

    if len(matches) > 1:
        duplicates.append({
            "ImageFile": name,
            "matches": " | ".join(str(m) for m in matches)
        })
        src = matches[0]
    else:
        src = matches[0]

    # Mantener estructura relativa respecto a SOURCE_ROOT
    rel_path = src.relative_to(source_root)
    dst = dest_root / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)

    if DRY_RUN:
        print(f"[DRY RUN] {src} -> {dst}")
    else:
        shutil.copy2(str(src), str(dst))
        print(f"Copiado: {src.name}")

    copied.append({
        "ImageFile": name,
        "source": str(src),
        "dest": str(dst)
    })

# Guardar reportes
pd.DataFrame(copied).to_csv(dest_root / "imagenes_copiadas.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(missing).to_csv(dest_root / "imagenes_no_encontradas.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(duplicates).to_csv(dest_root / "imagenes_duplicadas.csv", index=False, encoding="utf-8-sig")

print("\nResumen")
print(f"Copiadas: {len(copied)}")
print(f"No encontradas: {len(missing)}")
print(f"Duplicadas: {len(duplicates)}")
print(f"Reportes guardados en: {dest_root}")