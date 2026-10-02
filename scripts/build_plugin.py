#!/usr/bin/env python3
"""Build a deterministic public-submission ZIP from the repository source."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "plugin.json"


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    name = manifest["name"]
    version = manifest["version"]
    output_dir = REPO_ROOT / "dist"
    output_dir.mkdir(exist_ok=True)
    output = output_dir / f"{name}-{version}.zip"

    with tempfile.TemporaryDirectory(prefix=f"{name}-") as temp_dir:
        package_root = Path(temp_dir) / name
        package_root.mkdir()
        shutil.copy2(MANIFEST, package_root / "plugin.json")
        copy_tree(REPO_ROOT / "assets", package_root / "assets")
        copy_tree(REPO_ROOT / "skills", package_root / "skills")
        shutil.copy2(REPO_ROOT / "LICENSE", package_root / "LICENSE")
        shutil.copy2(
            REPO_ROOT / "THIRD_PARTY_NOTICES.md",
            package_root / "THIRD_PARTY_NOTICES.md",
        )
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "check_package.py"), str(package_root)],
            check=True,
        )
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(package_root.rglob("*")):
                if not path.is_file():
                    continue
                relative = path.relative_to(Path(temp_dir))
                info = zipfile.ZipInfo(relative.as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())

    print(output)


if __name__ == "__main__":
    main()
