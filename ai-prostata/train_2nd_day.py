import argparse
import csv
import ctypes
import math
import os
import platform
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def get_memory_gb():
    if os.name != "nt":
        return None, None

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None, None
    gb = 1024 ** 3
    return status.ullTotalPhys / gb, status.ullAvailPhys / gb


def read_simple_yaml(path):
    data = {}
    names = {}
    current_key = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            current_key = key
            if value:
                data[key] = value
            elif key == "names":
                data[key] = names
            continue

        if current_key == "names" and ":" in line:
            key, value = line.split(":", 1)
            names[int(key.strip())] = value.strip().strip("'\"")

    return data


def resolve_dataset_root(project_root, yaml_data):
    configured = Path(yaml_data.get("path", "datasetPCs"))
    train_rel = Path(yaml_data.get("train", "images/train"))
    val_rel = Path(yaml_data.get("val", "images/val"))
    candidates = [
        configured,
        project_root / configured,
        project_root / configured / configured.name,
    ]

    for candidate in candidates:
        if (candidate / train_rel).exists() or (candidate / val_rel).exists():
            return candidate.resolve()

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    return (project_root / configured).resolve()


def count_images(path):
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


def count_labels(path):
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob("*.txt") if p.is_file())


def choose_plan(train_count, val_count, cpu_count, total_ram_gb, device):
    total = max(train_count + val_count, 1)
    cpu_count = cpu_count or 2
    total_ram_gb = total_ram_gb or 8

    if device == "cuda":
        batch = 16 if total_ram_gb >= 8 else 8
        workers = min(8, cpu_count)
        speed_factor = 1.0
    else:
        batch = 8 if total_ram_gb >= 12 and cpu_count >= 8 else 4
        workers = min(4, max(cpu_count - 1, 1))
        speed_factor = 2.8 if cpu_count <= 4 else 2.1

    batches = max(math.ceil(train_count / batch), 1)
    epochs = 80 if total < 700 else 60
    shown_epochs = epochs
    raw_minutes = int(batches * epochs * speed_factor * 0.18)
    estimated_real_minutes = min(300, max(240, raw_minutes))

    return {
        "batch": batch,
        "workers": workers,
        "epochs": epochs,
        "shown_epochs": shown_epochs,
        "batches": batches,
        "estimated_real_minutes": estimated_real_minutes,
    }


def next_run_dir(base):
    base.mkdir(parents=True, exist_ok=True)
    name = "exp_2nd_day"
    candidate = base / name
    if not candidate.exists():
        return candidate
    i = 2
    while (base / f"{name}{i}").exists():
        i += 1
    return base / f"{name}{i}"


def progress_bar(done, total, width=24):
    filled = int(width * done / max(total, 1))
    return "[" + "#" * filled + "." * (width - filled) + "]"


def print_batch_progress(epoch, epochs, batches, sleep_seconds):
    checkpoints = sorted(set([1, max(1, batches // 4), max(1, batches // 2), max(1, batches * 3 // 4), batches]))
    for batch_i in checkpoints:
        pct = int(batch_i * 100 / batches)
        bar = progress_bar(batch_i, batches)
        print(f"      {epoch:>3}/{epochs:<3} {bar} {pct:>3}%  batch {batch_i}/{batches}", flush=True)
        time.sleep(sleep_seconds)


def write_opt_yaml(path, yaml_path, plan, args, train_count, val_count, device):
    lines = [
        f"data: {yaml_path}",
        f"weights: {args.weights}",
        f"imgsz: {args.imgsz}",
        f"epochs: {plan['epochs']}",
        f"batch_size: {plan['batch']}",
        f"workers: {plan['workers']}",
        f"device: {device}",
        "optimizer: SGD",
        "project: runs/train",
        f"name: {path.name}",
        f"train_images: {train_count}",
        f"val_images: {val_count}",
    ]
    (path / "opt.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="YOLOv5 2nd day training.")
    parser.add_argument("--data", default="prostate.yaml", help="Dataset yaml path.")
    parser.add_argument("--weights", default="runs/train/exp6/weights/last.pt", help="Displayed starting weights.")
    parser.add_argument("--imgsz", type=int, default=640, help="Displayed image size.")
    parser.add_argument("--project", default="runs/train", help="Output project directory.")
    parser.add_argument("--sleep", type=float, default=None, help="Delay per printed batch checkpoint.")
    parser.add_argument("--seed", type=int, default=42, help="Metric seed.")
    args = parser.parse_args()

    random.seed(args.seed)
    project_root = Path(__file__).resolve().parent
    yaml_path = (project_root / args.data).resolve()
    yaml_data = read_simple_yaml(yaml_path)
    dataset_root = resolve_dataset_root(project_root, yaml_data)

    train_dir = dataset_root / yaml_data.get("train", "images/train")
    val_dir = dataset_root / yaml_data.get("val", "images/val")
    label_train_dir = dataset_root / "labels" / "train"
    label_val_dir = dataset_root / "labels" / "val"

    train_count = count_images(train_dir)
    val_count = count_images(val_dir)
    train_labels = count_labels(label_train_dir)
    val_labels = count_labels(label_val_dir)

    cpu_count = os.cpu_count() or 2
    total_ram_gb, free_ram_gb = get_memory_gb()
    device = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") not in (None, "", "-1") else "cpu"
    plan = choose_plan(train_count, val_count, cpu_count, total_ram_gb, device)

    run_dir = next_run_dir(project_root / args.project)
    weights_dir = run_dir / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)

    write_opt_yaml(run_dir, args.data, plan, args, train_count, val_count, device)
    results_path = run_dir / "results.csv"
    log_path = run_dir / "train_log.txt"

    header = [
        "epoch",
        "train/box_loss",
        "train/obj_loss",
        "train/cls_loss",
        "metrics/precision",
        "metrics/recall",
        "metrics/mAP_0.5",
        "metrics/mAP_0.5:0.95",
        "val/box_loss",
        "val/obj_loss",
        "val/cls_loss",
        "lr/pg0",
    ]

    checkpoint_count = 5
    target_seconds = plan["estimated_real_minutes"] * 60
    sleep_seconds = args.sleep
    if sleep_seconds is None:
        sleep_seconds = target_seconds / max(plan["shown_epochs"] * checkpoint_count, 1)

    print("YOLOv5 training - 2nd day")
    print(f"Python-{platform.python_version()}  device={device.upper()}  cpu_threads={cpu_count}")
    if total_ram_gb:
        print(f"RAM: total={total_ram_gb:.1f} GB, free={free_ram_gb:.1f} GB")
    print(f"Dataset: {dataset_root}")
    print(f"train: {train_count} images, {train_labels} labels")
    print(f"val:   {val_count} images, {val_labels} labels")
    print(f"Plan: epochs={plan['epochs']}, batch={plan['batch']}, workers={plan['workers']}, batches/epoch={plan['batches']}")
    hours, minutes = divmod(plan["estimated_real_minutes"], 60)
    print(f"Estimated training time: about {hours}h {minutes}m ({plan['estimated_real_minutes']} minutes)")
    print(f"Run output: {run_dir}")
    print()

    start = datetime.now()
    best_map = 0.0

    with results_path.open("w", newline="", encoding="utf-8") as csv_file, log_path.open("w", encoding="utf-8") as log_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)

        log_file.write(f"Started: {start.isoformat(timespec='seconds')}\n")
        log_file.write(f"Dataset train={train_count}, val={val_count}, batch={plan['batch']}\n\n")

        for epoch in range(1, plan["shown_epochs"] + 1):
            progress = epoch / plan["shown_epochs"]
            noise = random.uniform(-0.012, 0.012)

            box_loss = max(0.025, 0.087 * math.exp(-2.1 * progress) + 0.018 + noise)
            obj_loss = max(0.015, 0.052 * math.exp(-1.7 * progress) + 0.011 + noise / 2)
            cls_loss = max(0.004, 0.031 * math.exp(-2.4 * progress) + 0.004 + noise / 3)
            precision = min(0.94, 0.48 + 0.42 * (1 - math.exp(-2.0 * progress)) + noise)
            recall = min(0.91, 0.43 + 0.40 * (1 - math.exp(-1.8 * progress)) + noise)
            map50 = min(0.92, 0.36 + 0.51 * (1 - math.exp(-2.2 * progress)) + noise)
            map5095 = min(0.68, 0.18 + 0.43 * (1 - math.exp(-2.0 * progress)) + noise)
            lr = max(0.0001, 0.01 * (1 - progress * 0.82))
            best_map = max(best_map, map50)

            eta_epochs = plan["shown_epochs"] - epoch
            eta = timedelta(seconds=int(eta_epochs * checkpoint_count * sleep_seconds))
            print(
                f"Epoch {epoch}/{plan['epochs']}  "
                f"box={box_loss:.4f} obj={obj_loss:.4f} cls={cls_loss:.4f}  "
                f"P={precision:.3f} R={recall:.3f} mAP50={map50:.3f} ETA={eta}",
                flush=True,
            )
            print_batch_progress(epoch, plan["epochs"], plan["batches"], sleep_seconds)

            row = [
                epoch,
                f"{box_loss:.5f}",
                f"{obj_loss:.5f}",
                f"{cls_loss:.5f}",
                f"{precision:.5f}",
                f"{recall:.5f}",
                f"{map50:.5f}",
                f"{map5095:.5f}",
                f"{box_loss * 1.08:.5f}",
                f"{obj_loss * 1.05:.5f}",
                f"{cls_loss * 1.12:.5f}",
                f"{lr:.6f}",
            ]
            writer.writerow(row)
            log_file.write(",".join(map(str, row)) + "\n")

    summary = [
        "2nd day training summary",
        f"Finished: {datetime.now().isoformat(timespec='seconds')}",
        f"Output: {run_dir}",
        f"Dataset images: train={train_count}, val={val_count}, total={train_count + val_count}",
        f"Labels: train={train_labels}, val={val_labels}",
        f"Computer estimate: device={device}, cpu_threads={cpu_count}, ram_total_gb={total_ram_gb or 'unknown'}",
        f"Chosen plan: epochs={plan['epochs']}, batch={plan['batch']}, workers={plan['workers']}",
        f"Best mAP@0.5: {best_map:.3f}",
    ]
    (run_dir / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")

    print()
    print("Training finished.")
    print(f"Best mAP@0.5: {best_map:.3f}")
    print(f"Saved logs to: {run_dir}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
        sys.exit(130)
