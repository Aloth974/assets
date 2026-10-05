"""Validate briefs, submissions and archive against docs/specs.md.

Usage: python tools/check.py [--root PATH] [--fix-hashes]
Exits 1 and lists every problem when the repository breaks a rule.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image

STEM: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9_]*$")
CANDIDATE: re.Pattern[str] = re.compile(r"^([a-z0-9_]+)-(\d+)$")
LOCAL_PATH: re.Pattern[str] = re.compile(r"(/home/|/Users/|/root/|[A-Za-z]:\\\\?Users)")
STATUSES: frozenset[str] = frozenset({"open", "taken", "done"})
RECORD_KEYS: frozenset[str] = frozenset(
    {"brief", "author", "tool", "model", "date", "prompt", "references", "sha256"}
)
TEXT_SUFFIXES: frozenset[str] = frozenset({".md", ".json", ".txt", ".yml", ".yaml", ".py"})
MAX_BYTES: int = 5 * 1024 * 1024


@dataclass(frozen=True)
class Spec:
    min_side: int
    max_side: int


SPECS: dict[str, Spec] = {
    "icons": Spec(256, 512),
    "textures": Spec(1024, 1024),
}


class Checker:
    def __init__(self, root: Path, fix_hashes: bool) -> None:
        self.root: Path = root
        self.fix_hashes: bool = fix_hashes
        self.errors: list[str] = []
        self.briefs: dict[str, tuple[str, str]] = {}

    def error(self, path: Path, message: str) -> None:
        self.errors.append(f"{path.relative_to(self.root).as_posix()}: {message}")

    def run(self) -> list[str]:
        self.check_briefs()
        self.check_submissions()
        self.check_archive()
        self.check_local_paths()
        return self.errors

    def check_briefs(self) -> None:
        briefs: Path = self.root / "briefs"
        for path in sorted(briefs.rglob("*.md")):
            if path.parent == briefs:
                continue
            family: str = path.parent.name
            if path.parent.parent != briefs or family not in SPECS:
                self.error(path, f"briefs live in briefs/<{'|'.join(SPECS)}>/")
                continue
            if not STEM.match(path.stem):
                self.error(path, "stem must match [a-z][a-z0-9_]*")
                continue
            if path.stem in self.briefs:
                self.error(path, "stem already used by another brief")
                continue
            meta: dict[str, str] = read_frontmatter(path)
            status: str = meta.get("status", "")
            if status not in STATUSES:
                self.error(path, f"status must be one of {sorted(STATUSES)}")
            elif status == "taken" and not meta.get("owner"):
                self.error(path, "a taken brief needs an owner")
            self.briefs[path.stem] = (family, status)

    def check_submissions(self) -> None:
        submissions: Path = self.root / "submissions"
        for entry in sorted(submissions.iterdir()) if submissions.is_dir() else []:
            if entry.name == ".gitkeep":
                continue
            if not entry.is_dir():
                self.error(entry, "submissions must sit in submissions/<stem>/")
                continue
            brief: tuple[str, str] | None = self.briefs.get(entry.name)
            if brief is None:
                self.error(entry, "no brief with this stem")
                continue
            family, status = brief
            if status == "open":
                self.error(entry, "brief is still open; set it to taken")
            for path in sorted(entry.iterdir()):
                if path.suffix == ".png":
                    if not CANDIDATE.match(path.stem):
                        self.error(path, "candidate must be named <handle>-<n>.png")
                        continue
                    self.check_image(path, family)
                    self.check_record(path, path.with_suffix(".json"), entry.name)
                elif path.suffix == ".json":
                    if not path.with_suffix(".png").exists():
                        self.error(path, "record without its image")
                else:
                    self.error(path, "only <handle>-<n>.png and .json files belong here")

    def check_archive(self) -> None:
        archive: Path = self.root / "archive"
        for path in sorted(archive.rglob("*")) if archive.is_dir() else []:
            if path.is_dir() or path.name == ".gitkeep":
                continue
            family: str = path.parent.name
            if path.parent.parent != archive or family not in SPECS:
                self.error(path, f"archive files live in archive/<{'|'.join(SPECS)}>/")
                continue
            if path.suffix == ".json":
                if not path.with_suffix(".png").exists():
                    self.error(path, "record without its image")
                continue
            if path.suffix != ".png":
                self.error(path, "only .png and .json files belong here")
                continue
            brief: tuple[str, str] | None = self.briefs.get(path.stem)
            if brief is None or brief != (family, "done"):
                self.error(path, f"needs a done brief at briefs/{family}/{path.stem}.md")
            self.check_image(path, family)
            self.check_record(path, path.with_suffix(".json"), path.stem)

    def check_image(self, path: Path, family: str) -> None:
        spec: Spec = SPECS[family]
        if path.stat().st_size > MAX_BYTES:
            self.error(path, "larger than 5 MB")
        try:
            with Image.open(path) as image:
                if image.format != "PNG":
                    self.error(path, f"is {image.format}, not PNG")
                width, height = image.size
                if width != height:
                    self.error(path, f"{width}x{height} is not square")
                elif not spec.min_side <= width <= spec.max_side:
                    self.error(path, f"{width} px outside {spec.min_side}-{spec.max_side} px")
                if not is_opaque(image):
                    self.error(path, "has transparent pixels")
        except OSError as exc:
            self.error(path, f"unreadable image ({exc})")

    def check_record(self, image: Path, path: Path, stem: str) -> None:
        if not path.exists():
            self.error(image, f"missing record {path.name}")
            return
        try:
            record: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            self.error(path, f"invalid JSON ({exc})")
            return
        if not isinstance(record, dict):
            self.error(path, "record must be a JSON object")
            return
        keys: set[str] = set(record)
        if keys != RECORD_KEYS:
            missing: list[str] = sorted(RECORD_KEYS - keys)
            extra: list[str] = sorted(keys - RECORD_KEYS)
            self.error(path, f"keys missing {missing}, unexpected {extra}")
            return
        if record["brief"] != stem:
            self.error(path, f"brief must be {stem!r}")
        for key in ("author", "tool", "model", "prompt"):
            if not isinstance(record[key], str) or not record[key].strip():
                self.error(path, f"{key} must be a non-empty string")
        try:
            date.fromisoformat(str(record["date"]))
        except ValueError:
            self.error(path, "date must be YYYY-MM-DD")
        references: object = record["references"]
        if not isinstance(references, list) or not all(
            isinstance(ref, str) and (self.root / ref).is_file() for ref in references
        ):
            self.error(path, "references must list existing repo-relative files")
        digest: str = hashlib.sha256(image.read_bytes()).hexdigest()
        if record["sha256"] != digest:
            if self.fix_hashes:
                record["sha256"] = digest
                path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            else:
                self.error(path, "sha256 does not match the image (try --fix-hashes)")

    def check_local_paths(self) -> None:
        for path in sorted(self.root.rglob("*")):
            parts: tuple[str, ...] = path.relative_to(self.root).parts
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            if parts[0] in {".git", "tools"} or "__pycache__" in parts:
                continue
            match: re.Match[str] | None = LOCAL_PATH.search(path.read_text(encoding="utf-8"))
            if match:
                self.error(path, f"contains a local path ({match.group(0)})")


def read_frontmatter(path: Path) -> dict[str, str]:
    lines: list[str] = path.read_text(encoding="utf-8").splitlines()
    meta: dict[str, str] = {}
    if not lines or lines[0].strip() != "---":
        return meta
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta


def is_opaque(image: Image.Image) -> bool:
    if image.mode in ("RGB", "L"):
        return True
    if "A" in image.getbands():
        low, _ = image.getchannel("A").getextrema()
        return low == 255
    if image.mode == "P" and "transparency" not in image.info:
        return True
    return False


def main() -> int:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--fix-hashes", action="store_true")
    args: argparse.Namespace = parser.parse_args()
    errors: list[str] = Checker(args.root.resolve(), args.fix_hashes).run()
    for message in errors:
        print(message)
    print(f"{len(errors)} problem(s)" if errors else "ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
