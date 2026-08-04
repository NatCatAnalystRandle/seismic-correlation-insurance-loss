#!/usr/bin/env python3
"""Replace machine-specific repository paths in notebook source cells.

The script changes source code only. It does not alter saved notebook outputs or
tracked validation/provenance metadata. Run without --apply for a preview.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_NOTEBOOKS = [
    "01_download_and_inspect_usgs_nshm2018.ipynb",
    "02_extract_usgs_rupture_rates.ipynb",
    "03_generate_annual_event_catalog.ipynb",
    "04_generate_ground_motion_fields.ipynb",
    "05_calculate_ground_up_losses.ipynb",
    "06_apply_insurance_terms.ipynb",
    "07_baseline_results_and_validation.ipynb",
]

WINDOWS_PROJECT_RE = re.compile(
    r"(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\r\n\"']+"
    r"[\\/]+Documents[\\/]+GitHub[\\/]+seismic-correlation-insurance-loss"
)
POSIX_PROJECT_RE = re.compile(
    r"(?i)/(?:home|Users)/[^/\r\n\"']+"
    r"/(?:Documents/GitHub/)?seismic-correlation-insurance-loss"
)
WINDOWS_HOME_RE = re.compile(r"(?i)\b[A-Z]:[\\/]+Users[\\/]+[^\\/\s\"']+")
POSIX_HOME_RE = re.compile(r"(?<![A-Za-z0-9_])/(?:home|Users)/[^/\s\"']+")


def find_root(start: Path) -> Path:
    for candidate in [start.resolve(), *start.resolve().parents]:
        if all((candidate / name).is_file() for name in EXPECTED_NOTEBOOKS):
            return candidate
    raise FileNotFoundError(
        "Could not find the repository root containing notebooks 01 through 07."
    )


def source_to_text(source: object) -> str:
    if isinstance(source, list):
        return "".join(str(item) for item in source)
    return str(source)


def text_to_source(text: str, original: object) -> object:
    if isinstance(original, list):
        return text.splitlines(keepends=True)
    return text


def replace_project_paths(text: str) -> tuple[str, int]:
    updated, windows_count = WINDOWS_PROJECT_RE.subn(".", text)
    updated, posix_count = POSIX_PROJECT_RE.subn(".", updated)
    return updated, windows_count + posix_count


def contains_home_path(text: str) -> bool:
    return bool(WINDOWS_HOME_RE.search(text) or POSIX_HOME_RE.search(text))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Repository root")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the changes. Without this flag, the script only previews them.",
    )
    args = parser.parse_args()

    root = args.root.resolve() if args.root else find_root(Path.cwd())
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = Path(tempfile.gettempdir()) / f"seismic_notebook_backup_{timestamp}"

    planned: list[tuple[str, int, int]] = []
    remaining: list[str] = []
    rewritten: dict[Path, dict] = {}

    for notebook_name in EXPECTED_NOTEBOOKS:
        path = root / notebook_name
        payload = json.loads(path.read_text(encoding="utf-8"))
        notebook_replacements = 0
        modified_cells = 0

        for cell_number, cell in enumerate(payload.get("cells", []), start=1):
            if cell.get("cell_type") != "code":
                continue

            original_source = cell.get("source", [])
            source_text = source_to_text(original_source)
            updated_source, count = replace_project_paths(source_text)

            if count:
                cell["source"] = text_to_source(updated_source, original_source)
                notebook_replacements += count
                modified_cells += 1

            if contains_home_path(updated_source):
                remaining.append(f"{notebook_name}: code cell {cell_number}")

        if notebook_replacements:
            planned.append((notebook_name, modified_cells, notebook_replacements))
            rewritten[path] = payload

    print("PORTABLE NOTEBOOK PATH NORMALIZATION")
    print("=" * 78)
    print(f"Repository: {root}")
    print(f"Mode:       {'APPLY' if args.apply else 'PREVIEW'}")
    print()

    if not planned:
        print("No machine-specific repository-root paths were found in code cells.")
    else:
        print("Planned notebook changes:")
        for notebook_name, modified_cells, replacements in planned:
            print(
                f"  {notebook_name}: "
                f"{modified_cells} code cell(s), {replacements} replacement(s)"
            )

    if remaining:
        print()
        print("Home-directory paths that remain in code cells and require review:")
        for item in remaining:
            print(f"  {item}")

    if not args.apply:
        print()
        print("No files were changed. Rerun with --apply after reviewing this preview.")
        return 1 if remaining else 0

    if planned:
        backup_root.mkdir(parents=True, exist_ok=False)
        for path in rewritten:
            shutil.copy2(path, backup_root / path.name)

        for path, payload in rewritten.items():
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8",
            )
            json.loads(temporary.read_text(encoding="utf-8"))
            temporary.replace(path)

        print()
        print(f"Backup copies: {backup_root}")
        print(f"Notebooks modified: {len(rewritten)}")
    else:
        print()
        print("Nothing needed to be written.")

    if remaining:
        print("Some source-cell paths still require manual review.")
        return 1

    print("All detected project-root paths in notebook code cells are now portable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
