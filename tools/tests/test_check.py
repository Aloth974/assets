from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check import Checker  # noqa: E402


def write_brief(root: Path, family: str, stem: str, status: str, owner: str = "") -> None:
    path: Path = root / "briefs" / family / f"{stem}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nstatus: {status}\nowner: {owner}\n---\n\n# {stem}\n", encoding="utf-8")


def write_image(path: Path, size: int, mode: str = "RGB", alpha: int = 255) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    colour: tuple[int, ...] = (120, 90, 60, alpha) if mode == "RGBA" else (120, 90, 60)
    Image.new(mode, (size, size), colour).save(path, "PNG")


def write_record(image: Path, stem: str, **overrides: object) -> None:
    record: dict[str, object] = {
        "brief": stem,
        "author": "friend",
        "tool": "ChatGPT",
        "model": "gpt-image-1",
        "date": "2026-10-05",
        "prompt": "A painted sword.",
        "references": [],
        "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
    }
    record.update(overrides)
    image.with_suffix(".json").write_text(json.dumps(record), encoding="utf-8")


class CheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
        self.root: Path = Path(self.tmp.name)
        write_brief(self.root, "icons", "sword", "taken", "friend")
        self.image: Path = self.root / "submissions" / "sword" / "friend-1.png"
        write_image(self.image, 512)
        write_record(self.image, "sword")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def errors(self, fix_hashes: bool = False) -> list[str]:
        return Checker(self.root, fix_hashes).run()

    def assert_one_error(self, fragment: str) -> None:
        errors: list[str] = self.errors()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn(fragment, errors[0])

    def test_valid_submission_passes(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_empty_repository_passes(self) -> None:
        empty: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        self.assertEqual(Checker(Path(empty.name), False).run(), [])

    def test_bad_brief_stem(self) -> None:
        write_brief(self.root, "icons", "Bad-Name", "open")
        self.assert_one_error("stem must match")

    def test_taken_brief_needs_owner(self) -> None:
        write_brief(self.root, "icons", "shield", "taken")
        self.assert_one_error("needs an owner")

    def test_submission_without_brief(self) -> None:
        orphan: Path = self.root / "submissions" / "axe" / "friend-1.png"
        write_image(orphan, 512)
        write_record(orphan, "axe")
        self.assert_one_error("no brief with this stem")

    def test_open_brief_rejects_submission(self) -> None:
        write_brief(self.root, "icons", "sword", "open")
        self.assert_one_error("still open")

    def test_bad_candidate_name(self) -> None:
        self.image.rename(self.image.with_name("Friend_one.png"))
        self.image.with_suffix(".json").unlink()
        self.assert_one_error("<handle>-<n>.png")

    def test_transparent_pixels(self) -> None:
        write_image(self.image, 512, "RGBA", 200)
        write_record(self.image, "sword")
        self.assert_one_error("transparent")

    def test_opaque_rgba_passes(self) -> None:
        write_image(self.image, 512, "RGBA", 255)
        write_record(self.image, "sword")
        self.assertEqual(self.errors(), [])

    def test_icon_size_out_of_range(self) -> None:
        write_image(self.image, 1024)
        write_record(self.image, "sword")
        self.assert_one_error("outside 256-512")

    def test_texture_size(self) -> None:
        write_brief(self.root, "textures", "brick", "taken", "friend")
        texture: Path = self.root / "submissions" / "brick" / "friend-1.png"
        write_image(texture, 512)
        write_record(texture, "brick")
        self.assert_one_error("outside 1024-1024")

    def test_missing_record(self) -> None:
        self.image.with_suffix(".json").unlink()
        self.assert_one_error("missing record")

    def test_record_keys(self) -> None:
        write_record(self.image, "sword", extra="x")
        self.assert_one_error("unexpected ['extra']")

    def test_record_bad_date(self) -> None:
        write_record(self.image, "sword", date="05/10/2026")
        self.assert_one_error("YYYY-MM-DD")

    def test_record_missing_reference(self) -> None:
        write_record(self.image, "sword", references=["archive/icons/nope.png"])
        self.assert_one_error("references")

    def test_hash_mismatch_and_fix(self) -> None:
        write_record(self.image, "sword", sha256="0" * 64)
        self.assert_one_error("sha256")
        self.assertEqual(self.errors(fix_hashes=True), [])
        self.assertEqual(self.errors(), [])

    def test_local_path_in_record(self) -> None:
        write_record(self.image, "sword", prompt="see /home/alice/ref.png")
        self.assert_one_error("local path")

    def test_archive_needs_done_brief(self) -> None:
        archived: Path = self.root / "archive" / "icons" / "sword.png"
        write_image(archived, 512)
        write_record(archived, "sword")
        self.assert_one_error("needs a done brief")
        write_brief(self.root, "icons", "sword", "done")
        self.image.unlink()
        self.image.with_suffix(".json").unlink()
        self.assertEqual(self.errors(), [])


if __name__ == "__main__":
    unittest.main()
