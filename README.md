# WheelLedger

Catch files that disappear from a Python distribution before you publish it. A checkout can still contain a translation, template or type stub that the wheel build silently omitted. WheelLedger reports the installed paths added, removed or changed between two releases of the same distribution.

## Try a release review

From this checkout, run the self-contained example with Python 3.9 or later.

```sh
python3 examples/demo.py
```

The sample release changes one module and drops the Slovak locale. The report includes `purelib/pocketclock/locales/sk.json` under **Removed**. Run the demo with `--fail-on-removal` to see the release gate exit with status 1.

## Compare your builds

```sh
python3 wheelledger.py previous.whl candidate.whl
python3 wheelledger.py previous.whl candidate.whl --json --fail-on-removal
```

Supply local wheel paths. Run the second command in CI after building the candidate and obtaining the previous release wheel. Exit 0 indicates success, 1 flags removals when the gate is enabled, and 2 indicates an input or usage error. Review intentional removals before release. To install the command in a virtual environment, run `python -m pip install .` and use `wheelledger` in place of `python3 wheelledger.py`.

## GitHub Actions

After setting up Python 3.9+ and placing both wheels in the runner workspace, add this step. Supply exact paths and use the optional gate once intentional removals have been reviewed.

```yaml
- uses: CoderSwAx/wheelledger@main
  with:
    before: artifacts/previous.whl
    after: artifacts/candidate.whl
    fail-on-removal: 'false'
```

The job summary shows up to 50 paths per category. The job log contains the full report. Pin the action to a commit SHA for reproducible release workflows.

## Reproduce a public release comparison

```sh
python -m pip download --no-deps --only-binary=:all: click==8.2.1
python -m pip download --no-deps --only-binary=:all: click==8.3.0
python wheelledger.py click-8.2.1-py3-none-any.whl click-8.3.0-py3-none-any.whl
```

These PyPI wheels contain one added file (`purelib/click/_utils.py`), nine changed files and zero removals. This example uses published artifacts and makes no claim of adoption by Click.

## What the comparison covers

The tool reads archive members without installing or importing either package. It compares SHA-256 digests of uncompressed file contents and groups paths by installation scheme. Moving a module between the wheel root and its corresponding `.data/purelib/` directory preserves its identity. ZIP order, timestamps and compression do not affect the result.

Both wheels must declare `Root-Is-Purelib: true`. Compare builds intended for the same target. Distribution metadata, entry points, generated console scripts, permissions, dependency changes and API compatibility are outside the scope of this file comparison. A clean report covers payload files only.

## Contributing

For a missed change or false positive, open an issue with the Python version, a minimal pair of wheel layouts, the command, and expected and actual output. Run `python3 -m unittest discover -s tests -v` before opening a pull request. The example creates disposable wheel fixtures and can be adapted for a regression test.

MIT licensed.
