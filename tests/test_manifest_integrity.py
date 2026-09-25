"""Check tracked QA metadata against local Git-ignored control artifacts."""
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CurrentControlManifestTests(unittest.TestCase):
    def test_local_control_checksums_and_documentation(self):
        documentation = (ROOT / "docs/historical_controls.md").read_text(encoding="utf-8")
        for manifest in sorted((ROOT / "data/manifests").glob("*_current_controls_manifest.json")):
            with self.subTest(manifest=manifest.name):
                record = json.loads(manifest.read_text(encoding="utf-8"))
                path = ROOT / record["output"]
                if not path.is_file():
                    # Generated controls are intentionally absent in a fresh clone.
                    continue
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                self.assertEqual(digest.hexdigest(), record["sha256"])
                self.assertIn(record["sha256"], documentation)


if __name__ == "__main__":
    unittest.main()
