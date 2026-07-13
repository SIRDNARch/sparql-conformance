# sparql-conformance

A standalone tool for running the [W3C SPARQL conformance test suite](https://github.com/w3c/rdf-tests/tree/main/sparql/) against any SPARQL engine. The engine under test is provided as a small Python file — no framework dependency required.

Originally developed for [QLever](https://github.com/ad-freiburg/qlever); now engine-agnostic.

## Installation

```bash
pip install -e .
```

This installs the `sparql_conformance` package and the `sparql-conformance`
console script. The built-in engine managers (`qlever`, `blazegraph`,
`graphdb`, `jena`, `mdb`, `oxigraph`, `virtuoso`) and the
`sparql_conformance` CLI integration additionally require
[qlever-control](https://github.com/ad-freiburg/qlever-control); without it,
provide your own engine via `--engine <file>`.

## Prerequisites

- Python 3.9+
- The W3C test suite files — clone or download:
  ```
  git clone https://github.com/w3c/rdf-tests.git
  ```
- A compiled SPARQL engine to test

## Running the test suite

```
sparql-conformance \
  --engine <engine-file-or-type> \
  --name <run-name> \
  --sparql11-dir <path/to/sparql11>
```

(`python3 main.py ...` still works without installation.)

### Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `--engine` | yes | — | Path to a Python file containing an `EngineManager` subclass (see [src/sparql_conformance/engines/README.md](src/sparql_conformance/engines/README.md)) |
| `--name` | yes | — | Label for this run; output is written to `results/<name>.json.bz2` |
| `--sparql11-dir` | one of the three | — | Path to the SPARQL 1.1 test suite directory |
| `--sparql10-dir` | one of the three | — | Path to the SPARQL 1.0 test suite directory |
| `--custom-dir` | one of the three | — | Path to a custom test suite directory |
| `--port` | no | `7001` | Port the engine server listens on |
| `--graph-store` | no | `sparql` | Graph store endpoint path for graph store protocol tests |
| `--binaries-directory` | no | `` | Directory containing engine binaries (forwarded to the engine manager via `config.path_to_binaries`) |
| `--exclude` | no | — | Comma-separated list of test names or group names to skip |
| `--include` | no | — | Comma-separated list of test names or group names to run (all others skipped) |
| `--type-alias` | no | — | JSON list of XSD type pairs treated as equivalent. See below. |
| `--report` | no | `none` | Console output verbosity: `none`, `summary`, or `line`. See [Console output](#console-output). |
| `--compare-to` | no | — | Path to a previous `<name>.json.bz2` run to compare against; prints regressions and fixes. See [Console output](#console-output). |

### Example: QLever

```bash
sparql-conformance \
  --engine src/sparql_conformance/engines/qlever-binaries-manager.py \
  --name qlever-2024 \
  --sparql11-dir ../rdf-tests/sparql/sparql11 \
  --sparql10-dir ../rdf-tests/sparql/sparql10 \
  --binaries-directory ../qlever/build
```

### Type aliases

Some engines return a numerically equivalent but differently typed literal (e.g. `xsd:int` instead of `xsd:integer`). Use `--type-alias` to mark these as intended deviations rather than failures:

```bash
--type-alias "[['xsd:integer','xsd:int'],['xsd:double','xsd:float']]"
```

### Filtering tests

Run a single group or test by name:

```bash
# Run only the property path group
--include pp01,pp02,pp06

# Skip aggregates
--exclude aggregates
```

## Output

Results are written to `results/<name>.json.bz2`. The file contains a JSON object with one entry per test suite and a summary:

```json
{
  "version": 2,
  "suites": {
    "sparql11": { "tests": [...], "info": { "passed": 512, "failed": 34, ... } },
    "sparql10": { "tests": [...], "info": { ... } }
  },
  "info": { "passed": 560, "tests": 620, "failed": 38, ... }
}
```

## Console output

By default the run only prints progress and writes the JSON file. For readable
feedback in the terminal, use `--report`:

| `--report` | What it prints |
|---|---|
| `none` (default) | Nothing extra — unchanged behavior. |
| `summary` | An end-of-run totals block (passed / failed / intended / not tested, per suite and overall) plus a list of the failed tests. |
| `line` | A live colored `PASS` / `FAIL` / `INTD` line per test as it runs, plus the summary. |

```bash
python3 main.py --engine <engine-file> --name my-run \
  --sparql11-dir ../rdf-tests/sparql/sparql11 --report line
```

Colors are only used when writing to a terminal; piping to a file (or setting
`NO_COLOR`) produces plain text.

### Comparing against a previous run

Pass a previous result file to `--compare-to` to see what changed. It prints the
**regressions** (tests that passed before and now fail) and **fixes** (tests that
failed before and now pass):

```bash
python3 main.py --engine <engine-file> --name new-run \
  --sparql11-dir ../rdf-tests/sparql/sparql11 \
  --compare-to results/old-run.json.bz2
```

`--report` and `--compare-to` can be combined and work independently.

## Adding support for a new engine

See [src/sparql_conformance/engines/README.md](src/sparql_conformance/engines/README.md) for a step-by-step guide to writing an `EngineManager` for any SPARQL engine.
