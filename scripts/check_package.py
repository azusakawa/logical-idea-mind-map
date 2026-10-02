#!/usr/bin/env python3
"""Run lightweight, local checks on the public plugin package."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
REQUIRED_INTERFACE = {
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
    "capabilities",
    "defaultPrompt",
    "websiteURL",
    "supportURL",
    "privacyPolicyURL",
    "termsOfServiceURL",
    "logo",
    "composerIcon",
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def contained_path(root: Path, value: str) -> Path:
    if not value.startswith("./"):
        fail(f"asset path must start with './': {value}")
    path = (root / value[2:]).resolve()
    if root.resolve() not in path.parents:
        fail(f"asset path escapes plugin root: {value}")
    if not path.is_file():
        fail(f"referenced asset is missing: {value}")
    return path


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    manifest_path = root / "plugin.json"
    if not manifest_path.is_file():
        fail("plugin.json is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    name = manifest.get("name", "")
    version = manifest.get("version", "")
    if not NAME_RE.fullmatch(name) or len(name) > 64:
        fail("plugin name must be lowercase kebab-case and at most 64 characters")
    if not SEMVER_RE.fullmatch(version):
        fail("version must use strict semantic versioning")
    if (root / ".app.json").exists() or manifest.get("apps") is not None:
        fail("public upload must not contain a root app binding")

    openai = manifest.get("extensions", {}).get("com.openai", {})
    if openai.get("apps") is not None:
        fail("public upload must not declare extensions.com.openai.apps")
    interface = openai.get("interface", {})
    missing = sorted(REQUIRED_INTERFACE - interface.keys())
    if missing:
        fail(f"missing listing fields: {', '.join(missing)}")
    if len(interface["displayName"]) > 30:
        fail("displayName exceeds 30 characters")
    if len(interface["shortDescription"]) > 30:
        fail("shortDescription exceeds 30 characters")
    if len(interface["longDescription"]) > 4000:
        fail("longDescription exceeds 4000 characters")
    if len(interface["developerName"]) > 80:
        fail("developerName exceeds 80 characters")

    prompts = interface["defaultPrompt"]
    if isinstance(prompts, str):
        prompts = [prompts]
    if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
        fail("defaultPrompt must contain one to three prompts")
    normalized = []
    for prompt in prompts:
        if not isinstance(prompt, str) or not prompt.strip() or "\n" in prompt:
            fail("default prompts must be nonblank single-line strings")
        if len(prompt) > 128:
            fail("a default prompt exceeds 128 characters")
        normalized.append(" ".join(prompt.split()))
    if len(normalized) != len(set(normalized)):
        fail("default prompts must be unique")

    for key in ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL"):
        parsed = urlparse(interface[key])
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            fail(f"{key} must be an absolute credential-free HTTPS URL")

    for key, minimum in (("logo", 256), ("composerIcon", 48)):
        path = contained_path(root, interface[key])
        with Image.open(path) as image:
            if image.format != "PNG":
                fail(f"{key} must reference a PNG")
            width, height = image.size
            if width != height or width < minimum or width > 4096:
                fail(f"{key} must be square and between {minimum} and 4096 pixels")
            if path.stat().st_size > 5 * 1024 * 1024:
                fail(f"{key} exceeds 5 MiB")

    skill_file = root / "skills" / name / "SKILL.md"
    if not skill_file.is_file():
        fail(f"expected skill file is missing: skills/{name}/SKILL.md")
    frontmatter = skill_file.read_text(encoding="utf-8").split("---", 2)
    if len(frontmatter) < 3 or f"name: {name}" not in frontmatter[1]:
        fail("SKILL.md frontmatter name does not match plugin name")

    print(f"PASS: {name} {version} package checks completed")


if __name__ == "__main__":
    main()

