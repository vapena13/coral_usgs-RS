"""
Genera histogramas RGB comparativos para imagenes originales y corregidas.

No usa matplotlib para evitar dependencias externas: dibuja las figuras con
Pillow y calcula histogramas con numpy.
"""

import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ORIGINAL_DIR = Path(r"D:\coral_proyecto\SQUID5_EDR_2021_dataset")
CORRECTED_DIR = Path(r"D:\coral_proyecto\SQUID5_EDR_2021_dataset_corregido")
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs" / "figures" / "histogramas_rgb"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def get_font(size=18, bold=False):
    font_name = "arialbd.ttf" if bold else "arial.ttf"
    font_path = Path(r"C:\Windows\Fonts") / font_name
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size)
    return ImageFont.load_default()


FONT_SMALL = get_font(18)
FONT = get_font(22)
FONT_BOLD = get_font(24, bold=True)


def list_images(folder):
    return sorted(
        path for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def sample_images(folder, max_images=30):
    return list_images(folder)[:max_images]


def compute_average_histogram(folder, max_images=30):
    files = sample_images(folder, max_images)

    hist_r = np.zeros(256, dtype=np.float64)
    hist_g = np.zeros(256, dtype=np.float64)
    hist_b = np.zeros(256, dtype=np.float64)
    count = 0

    for path in files:
        with Image.open(path) as img:
            arr = np.asarray(img.convert("RGB"))

        hist_r += np.histogram(arr[:, :, 0], bins=256, range=(0, 255))[0]
        hist_g += np.histogram(arr[:, :, 1], bins=256, range=(0, 255))[0]
        hist_b += np.histogram(arr[:, :, 2], bins=256, range=(0, 255))[0]
        count += 1

    if count:
        hist_r /= count
        hist_g /= count
        hist_b /= count

    return hist_r, hist_g, hist_b, files


def draw_dashed_line(draw, points, fill, width=3, dash=10, gap=7):
    for start, end in zip(points[:-1], points[1:]):
        x1, y1 = start
        x2, y2 = end
        dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if dist == 0:
            continue
        vx = (x2 - x1) / dist
        vy = (y2 - y1) / dist
        pos = 0
        while pos < dist:
            seg_end = min(pos + dash, dist)
            draw.line(
                [
                    (x1 + vx * pos, y1 + vy * pos),
                    (x1 + vx * seg_end, y1 + vy * seg_end),
                ],
                fill=fill,
                width=width,
            )
            pos += dash + gap


def plot_histograms(series, title, output_path, width=1800, height=1080, show_legend=True):
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    left = 140
    right = 80
    top = 120
    bottom = 130
    plot_w = width - left - right
    plot_h = height - top - bottom

    draw.text((left, 35), title, fill="black", font=FONT_BOLD)

    axis_color = (30, 30, 30)
    draw.line([(left, top), (left, top + plot_h)], fill=axis_color, width=2)
    draw.line([(left, top + plot_h), (left + plot_w, top + plot_h)], fill=axis_color, width=2)

    for tick in [0, 64, 128, 192, 255]:
        x = left + int(plot_w * tick / 255)
        draw.line([(x, top + plot_h), (x, top + plot_h + 8)], fill=axis_color, width=2)
        draw.text((x - 18, top + plot_h + 14), str(tick), fill="black", font=FONT_SMALL)

    max_y = max(float(np.max(values)) for _, values, _, _ in series)
    max_y = max(max_y, 1.0)

    for frac in [0.25, 0.5, 0.75, 1.0]:
        y = top + plot_h - int(plot_h * frac)
        draw.line([(left, y), (left + plot_w, y)], fill=(225, 225, 225), width=1)
        label = "{:.0f}".format(max_y * frac)
        draw.text((25, y - 12), label, fill="black", font=FONT_SMALL)

    for label, values, color, style in series:
        points = []
        for idx, value in enumerate(values):
            x = left + int(plot_w * idx / 255)
            y = top + plot_h - int(plot_h * float(value) / max_y)
            points.append((x, y))

        if style == "dashed":
            draw_dashed_line(draw, points, fill=color, width=4)
        else:
            draw.line(points, fill=color, width=4)

    draw.text((left + plot_w // 2 - 70, height - 55), "Nivel digital", fill="black", font=FONT)
    draw.text((20, top - 45), "Frecuencia promedio", fill="black", font=FONT_SMALL)

    if show_legend:
        legend_x = left + plot_w - 480
        legend_y = 40
        for idx, (label, _, color, style) in enumerate(series):
            y = legend_y + idx * 32
            if style == "dashed":
                draw_dashed_line(draw, [(legend_x, y + 12), (legend_x + 55, y + 12)], fill=color, width=4)
            else:
                draw.line([(legend_x, y + 12), (legend_x + 55, y + 12)], fill=color, width=4)
            draw.text((legend_x + 70, y), label, fill="black", font=FONT_SMALL)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def find_representative_pair(original_files, corrected_files):
    corrected_by_name = {}
    for path in corrected_files:
        corrected_by_name.setdefault(path.name, path)

    for original in original_files:
        corrected = corrected_by_name.get(original.name)
        if corrected:
            return original, corrected

    if original_files and corrected_files:
        return original_files[0], corrected_files[0]

    raise RuntimeError("No hay imagenes suficientes para generar figura representativa.")


def resize_to_box(img, box):
    img = img.copy()
    img.thumbnail(box, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", box, "white")
    x = (box[0] - img.width) // 2
    y = (box[1] - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def make_representative_figure(original_path, corrected_path, output_path):
    with Image.open(original_path) as img:
        original = img.convert("RGB")
    with Image.open(corrected_path) as img:
        corrected = img.convert("RGB")

    width, height = 1800, 1250
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    draw.text((60, 35), "Comparacion visual e histogramas RGB", fill="black", font=FONT_BOLD)
    draw.text((80, 95), "Original: {}".format(original_path.name), fill="black", font=FONT_SMALL)
    draw.text((980, 95), "Corregida: {}".format(corrected_path.name), fill="black", font=FONT_SMALL)

    canvas.paste(resize_to_box(original, (760, 470)), (80, 140))
    canvas.paste(resize_to_box(corrected, (760, 470)), (980, 140))

    hist_o = [np.histogram(np.asarray(original)[:, :, i], bins=256, range=(0, 255))[0] for i in range(3)]
    hist_c = [np.histogram(np.asarray(corrected)[:, :, i], bins=256, range=(0, 255))[0] for i in range(3)]

    temp_o = OUTPUT_DIR / "_tmp_hist_o.png"
    temp_c = OUTPUT_DIR / "_tmp_hist_c.png"
    plot_histograms(
        [
            ("Rojo", hist_o[0], (210, 40, 40), "solid"),
            ("Verde", hist_o[1], (40, 150, 70), "solid"),
            ("Azul", hist_o[2], (45, 85, 210), "solid"),
        ],
        "Histograma RGB original",
        temp_o,
        width=820,
        height=520,
        show_legend=False,
    )
    plot_histograms(
        [
            ("Rojo", hist_c[0], (210, 40, 40), "solid"),
            ("Verde", hist_c[1], (40, 150, 70), "solid"),
            ("Azul", hist_c[2], (45, 85, 210), "solid"),
        ],
        "Histograma RGB corregido",
        temp_c,
        width=820,
        height=520,
        show_legend=False,
    )

    with Image.open(temp_o) as hist_img:
        canvas.paste(hist_img.convert("RGB"), (60, 670))
    with Image.open(temp_c) as hist_img:
        canvas.paste(hist_img.convert("RGB"), (930, 670))

    temp_o.unlink(missing_ok=True)
    temp_c.unlink(missing_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)


def write_summary(output_path, rows):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item", "value"])
        writer.writerows(rows)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    hist_r_o, hist_g_o, hist_b_o, original_sample = compute_average_histogram(ORIGINAL_DIR, max_images=30)
    hist_r_c, hist_g_c, hist_b_c, corrected_sample = compute_average_histogram(CORRECTED_DIR, max_images=30)

    original_files = list_images(ORIGINAL_DIR)
    corrected_files = list_images(CORRECTED_DIR)

    plot_histograms(
        [
            ("Rojo original", hist_r_o, (210, 40, 40), "solid"),
            ("Verde original", hist_g_o, (40, 150, 70), "solid"),
            ("Azul original", hist_b_o, (45, 85, 210), "solid"),
        ],
        "Histogramas promedio - imagenes originales",
        OUTPUT_DIR / "histograma_originales.png",
    )

    plot_histograms(
        [
            ("Rojo corregido", hist_r_c, (210, 40, 40), "solid"),
            ("Verde corregido", hist_g_c, (40, 150, 70), "solid"),
            ("Azul corregido", hist_b_c, (45, 85, 210), "solid"),
        ],
        "Histogramas promedio - imagenes corregidas",
        OUTPUT_DIR / "histograma_corregidas.png",
    )

    plot_histograms(
        [
            ("Rojo original", hist_r_o, (210, 40, 40), "solid"),
            ("Verde original", hist_g_o, (40, 150, 70), "solid"),
            ("Azul original", hist_b_o, (45, 85, 210), "solid"),
            ("Rojo corregido", hist_r_c, (210, 40, 40), "dashed"),
            ("Verde corregido", hist_g_c, (40, 150, 70), "dashed"),
            ("Azul corregido", hist_b_c, (45, 85, 210), "dashed"),
        ],
        "Comparacion de histogramas RGB antes y despues de la correccion",
        OUTPUT_DIR / "comparacion_histogramas_rgb.png",
        width=2000,
        height=1200,
    )

    original_rep, corrected_rep = find_representative_pair(original_files, corrected_files)
    make_representative_figure(
        original_rep,
        corrected_rep,
        OUTPUT_DIR / "comparacion_imagen_histograma.png",
    )

    write_summary(
        OUTPUT_DIR / "histogramas_resumen.csv",
        [
            ("original_dir", ORIGINAL_DIR),
            ("corrected_dir", CORRECTED_DIR),
            ("original_images_total", len(original_files)),
            ("corrected_images_total", len(corrected_files)),
            ("average_histogram_sample_size", 30),
            ("original_sample_first", original_sample[0] if original_sample else ""),
            ("corrected_sample_first", corrected_sample[0] if corrected_sample else ""),
            ("representative_original", original_rep),
            ("representative_corrected", corrected_rep),
        ],
    )

    print("Figuras generadas en:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
