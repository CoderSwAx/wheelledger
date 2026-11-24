"""Create two sample releases in a temporary directory and compare them."""
import base64
import csv
import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile


def make_wheel(directory, version, files, name="pocketclock"):
    stem = f"{name}-{version}"
    root = stem + ".dist-info"
    path = directory / (stem + "-py3-none-any.whl")
    entries = {**files, root + "/METADATA": f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
               root + "/WHEEL": "Wheel-Version: 1.0\nGenerator: demo\nRoot-Is-Purelib: true\nTag: py3-none-any\n"}
    record = io.StringIO()
    rows = csv.writer(record)
    with ZipFile(path, "w") as archive:
        for key, content in entries.items():
            raw = content.encode()
            archive.writestr(key, raw)
            digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
            rows.writerow([key, "sha256=" + digest, len(raw)])
        rows.writerow([root + "/RECORD", "", ""])
        archive.writestr(root + "/RECORD", record.getvalue())
    return path


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        old = make_wheel(directory, "1.0", {"pocketclock/__init__.py": "",
                         "pocketclock/locales/sk.json": '{"today":"dnes"}'})
        new = make_wheel(directory, "1.1", {"pocketclock/__init__.py": "__version__ = '1.1'"})
        cli = Path(__file__).resolve().parents[1] / "wheelledger.py"
        sys.exit(subprocess.call([sys.executable, cli, old, new, *sys.argv[1:]]))
