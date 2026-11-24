import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from examples.demo import make_wheel
from wheelledger import main


class ReleaseComparison(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)

    def compare(self, old, new, *flags):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main([str(old), str(new), "--json", *flags])
        return status, json.loads(output.getvalue())

    def test_release_gate(self):
        old = make_wheel(self.directory, "1", {"a.py": "", "b.py": "1"})
        new = make_wheel(self.directory, "2", {"b.py": "2", "c.py": ""})
        status, report = self.compare(old, new, "--fail-on-removal")
        self.assertEqual(status, 1)
        for group, file in [("removed", "a"), ("changed", "b"), ("added", "c")]:
            self.assertEqual(report[group], [f"purelib/{file}.py"])
        self.assertEqual(self.compare(old, new)[0], 0)

    def test_relocation_to_purelib(self):
        old = make_wheel(self.directory, "1", {"a.py": "pass"})
        new = make_wheel(self.directory, "2", {"pocketclock-2.data/purelib/a.py": "pass"})
        status, report = self.compare(old, new, "--fail-on-removal")
        self.assertEqual(status, 0)
        self.assertFalse(any(report[key] for key in ("removed", "added", "changed")))

    def test_invalid_inputs(self):
        old = make_wheel(self.directory, "1", {})
        broken = self.directory / "broken.whl"
        broken.write_bytes(b"broken")
        for new in [broken, make_wheel(self.directory, "2", {}, name="other"),
                    make_wheel(self.directory, "3", {"a": "", "pocketclock-3.data/purelib/a": ""})]:
            with self.subTest(new=new), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as err:
                self.compare(old, new)
            self.assertEqual(err.exception.code, 2)
