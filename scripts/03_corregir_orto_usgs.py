from pathlib import Path
import numpy as np
import rasterio

# =========================
# CONFIGURACIÓN
# =========================
input_tif = Path(r"C:\Users\TUF Dash\Documents\Maestria\PercepcionRemota\informe1_RS\coral-usgs-RS\outputs\products\orthomosaic\ortho_subbloque_rgb.tif")
output_tif = input_tif.with_name("ortho_subbloque_rgb_corregida.tif")

# igual que el script USGS / Ancuti parcial
percRemove = 0.0005
alpha_red = 1.0
alpha_blue = 0.0
# =========================

with rasterio.open(input_tif) as src:
    profile = src.profile.copy()
    img = src.read()

# Espera 3 bandas RGB
if img.shape[0] < 3:
    raise ValueError(f"Se esperaban al menos 3 bandas RGB, pero llegaron {img.shape[0]}")

# Usar solo RGB
rgb = img[:3].astype(np.float32)

# Normalización aproximada a 0-1 para 8 bits
# Si tu raster no está en 8 bits, esto igual suele funcionar para visualización
rgb = np.clip(rgb / 255.0, 0, 1)

Ir, Ig, Ib = rgb[0], rgb[1], rgb[2]

Ir_mean = Ir.mean()
Ig_mean = Ig.mean()
Ib_mean = Ib.mean()

# (a) Color compensation
Irc = Ir + alpha_red * (Ig_mean - Ir_mean) * (1 - Ir) * Ig
Ibc = Ib + alpha_blue * (Ig_mean - Ib_mean)

I = np.stack([Irc, Ig, Ibc], axis=0)
I = np.clip(I, 0, 1)

# (b) White balance (Gray World)
R_avg = I[0].mean()
G_avg = I[1].mean()
B_avg = I[2].mean()

RGB_avg = np.array([R_avg, G_avg, B_avg], dtype=np.float32)
gray_value = RGB_avg.mean()
scaleValue = gray_value / RGB_avg

Iwb = np.empty_like(I)
Iwb[0] = I[0] * scaleValue[0]
Iwb[1] = I[1] * scaleValue[1]
Iwb[2] = I[2] * scaleValue[2]
Iwb = np.clip(Iwb, 0, 1)

# (c) Histogram stretch
grayImageNEW = Iwb.mean(axis=0)
gray_sorted = np.sort(grayImageNEW.ravel())

ttl = gray_sorted.size
cellLow = max(0, int(np.floor(percRemove * ttl)))
cellHigh = min(ttl - 1, ttl - cellLow - 1)

grayLow = gray_sorted[cellLow]
grayHigh = gray_sorted[cellHigh]

if grayHigh <= grayLow:
    raise ValueError("grayHigh <= grayLow; no se puede hacer histogram stretch útil.")

slope = 1.0 / (grayHigh - grayLow)
offset = -slope * grayLow

Ifinal = Iwb * slope + offset
Ifinal = np.clip(Ifinal, 0, 1)

Ifinal8 = np.round(Ifinal * 255).astype(np.uint8)

# Actualizar perfil para salida RGB uint8
profile.update(
    dtype=rasterio.uint8,
    count=3,
    compress="LZW"
)

with rasterio.open(output_tif, "w", **profile) as dst:
    dst.write(Ifinal8)

print(f"Imagen corregida guardada en:\n{output_tif}")
