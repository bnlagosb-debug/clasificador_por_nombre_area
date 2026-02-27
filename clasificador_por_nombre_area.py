# clasificador_por_nombre_area.py
# -*- coding: utf-8 -*-

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class Config:
    base_dir: Path
    action: str
    dry_run: bool
    recursive: bool
    allowed_extensions: List[str]
    area_regex: str
    no_match_dest: str


def normalize_ext(ext: str) -> str:
    ext = ext.strip().lower()
    if ext in ("*", ".*"):
        return "*"
    if not ext.startswith("."):
        ext = "." + ext
    return ext


def load_config(path: Path) -> Config:
    with path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    return Config(
        base_dir=Path(cfg["base_dir"]).expanduser().resolve(),
        action=cfg.get("action", "move").strip().lower(),
        dry_run=bool(cfg.get("dry_run", False)),
        recursive=bool(cfg.get("recursive", False)),
        allowed_extensions=[normalize_ext(e) for e in cfg.get("allowed_extensions", [".pdf"])],
        area_regex=cfg.get("area_regex", r"\s-\s(\d{3})(?=-)"),
        no_match_dest=cfg.get("no_match_dest", "_NO_CLASIFICADO"),
    )


def iter_files(base_dir: Path, recursive: bool):
    if recursive:
        return [p for p in base_dir.rglob("*") if p.is_file()]
    return [p for p in base_dir.iterdir() if p.is_file()]


def ext_allowed(file_path: Path, allowed_extensions: List[str]) -> bool:
    if "*" in allowed_extensions:
        return True
    return file_path.suffix.lower() in allowed_extensions


def unique_destination_path(dest_dir: Path, original_name: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    candidate = dest_dir / original_name
    if not candidate.exists():
        return candidate

    stem = Path(original_name).stem
    suf = Path(original_name).suffix
    i = 1
    while True:
        candidate = dest_dir / f"{stem} ({i}){suf}"
        if not candidate.exists():
            return candidate
        i += 1


def extract_area_from_filename(filename: str, area_regex: str) -> Optional[str]:
    m = re.search(area_regex, filename)
    return m.group(1) if m else None


def main():
    parser = argparse.ArgumentParser(description="Clasifica PDFs por área leyendo el nombre del archivo.")
    parser.add_argument("--config", required=True, help="Ruta al config.json")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    cfg = load_config(config_path)

    files = iter_files(cfg.base_dir, cfg.recursive)

    processed = moved = no_match = 0

    for fpath in files:
        if not ext_allowed(fpath, cfg.allowed_extensions):
            continue

        area = extract_area_from_filename(fpath.stem, cfg.area_regex)

        if area is None:
            dest_dir = cfg.base_dir / cfg.no_match_dest
            no_match += 1
        else:
            dest_dir = cfg.base_dir / area

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / fpath.name

        if not cfg.dry_run:
            if cfg.action == "move":
                shutil.move(str(fpath), str(dest_path))
            else:
                shutil.copy2(str(fpath), str(dest_path))
            moved += 1

        processed += 1

    print(f"Procesados: {processed} | Movidos/Copiados: {moved} | No match: {no_match}")


if __name__ == "__main__":
    main()
