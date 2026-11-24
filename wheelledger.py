"""Compare the installed payload of two pure-Python wheels."""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path


def read_metadata(archive, path):
    return BytesParser(policy=policy.default).parsebytes(archive.read(path))


def inventory(path):
    with zipfile.ZipFile(path) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        names = {item.filename for item in files}
        roots = {name.split("/")[0] for name in names
                 if name.split("/")[0].endswith(".dist-info")}
        if len(names) != len(files) or len(roots) != 1:
            raise ValueError("expected unique file names and one .dist-info directory")
        root = roots.pop()
        if not {root + "/METADATA", root + "/WHEEL"} <= names:
            raise ValueError("missing wheel metadata")
        meta = read_metadata(archive, root + "/METADATA")
        wheel = read_metadata(archive, root + "/WHEEL")
        if wheel.get("Root-Is-Purelib", "").lower() != "true":
            raise ValueError("only purelib wheels are supported")
        name, version = meta.get("Name"), meta.get("Version")
        if not name or not version:
            raise ValueError("missing distribution name or version")
        data = root.removesuffix(".dist-info") + ".data/"
        payload = {}
        for item in files:
            key = item.filename
            if any(part in {"", ".", ".."} for part in key.split("/")) or "\\" in key:
                raise ValueError(f"invalid wheel path {key!r}")
            if key.startswith(root + "/"):
                continue
            if key.startswith(data):
                scheme, sep, relative = key[len(data):].partition("/")
                if not sep or scheme not in {"purelib", "platlib", "headers", "scripts", "data"}:
                    raise ValueError(f"invalid wheel data path {key!r}")
                key = scheme + "/" + relative
            else:
                key = "purelib/" + key
            if key in payload:
                raise ValueError(f"overlapping install paths {key!r}")
            digest = hashlib.sha256()
            with archive.open(item) as stream:
                for block in iter(lambda: stream.read(65536), b""):
                    digest.update(block)
            payload[key] = digest.digest()
        return name, version, payload


def compare(before, after):
    name, old_version, old = inventory(before)
    other_name, new_version, new = inventory(after)
    if re.sub(r"[-_.]+", "-", name.lower()) != re.sub(r"[-_.]+", "-", other_name.lower()):
        raise ValueError("the wheels belong to different distributions")
    return dict(distribution=name, before=old_version, after=new_version,
                removed=sorted(old.keys() - new.keys()), added=sorted(new.keys() - old.keys()),
                changed=sorted(key for key in old.keys() & new.keys() if old[key] != new[key]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--json", action="store_true", help="emit a machine-readable report")
    parser.add_argument("--fail-on-removal", action="store_true", help="exit 1 for removed files")
    parser.add_argument("--summary", type=Path, help="append a GitHub job summary")
    args = parser.parse_args(argv)
    try:
        report = compare(args.before, args.after)
        if args.summary:
            with args.summary.open("a", encoding="utf-8") as summary:
                print("## WheelLedger release review\n", file=summary)
                for group in ("removed", "added", "changed"):
                    paths = report[group]
                    print(f"### {group.capitalize()} ({len(paths)})\n", file=summary)
                    for path in paths[:50]:
                        print("    " + ascii(path), file=summary)
                    if len(paths) > 50:
                        print("\nSee the job log for the full list.", file=summary)
                    print(file=summary)
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        parser.exit(2, f"wheelledger: {exc}\n")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['distribution']}  {report['before']} → {report['after']}")
        for group in ("removed", "added", "changed"):
            print(f"{group.capitalize()} ({len(report[group])})")
            for path in report[group]:
                print("  " + ascii(path))
    return int(args.fail_on_removal and bool(report["removed"]))


if __name__ == "__main__":
    sys.exit(main())
