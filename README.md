# sparql-conformance

A test harness that runs the [W3C SPARQL conformance test suite](https://github.com/w3c/rdf-tests/tree/main/sparql/) against any SPARQL engine and reports which tests pass, fail, or fail in an "intended" (accepted) way. It checks query evaluation, updates, syntax validation, the SPARQL protocol, and the graph store protocol, and writes a machine-readable result file plus optional console output.

The engine under test is plugged in as a small adapter class (an `EngineManager`) — no framework dependency required, so it works with any engine you can start and query over HTTP. Originally developed for [QLever](https://github.com/ad-freiburg/qlever); now engine-agnostic.

There are two ways to use it:

- **Standalone** (this document): bring your own engine adapter, or use the bundled in-process rdflib reference engine.
- **[qlever-control integration](src/sparql_conformance/README.md)**: run `sparql_conformance test` with built-in support for QLever, Blazegraph, GraphDB, Jena, MillenniumDB, Oxigraph, and Virtuoso — no adapter needed.

## Get started

```bash
git clone https://github.com/ad-freiburg/sparql-conformance.git
cd sparql-conformance
pip install -e .

git clone https://github.com/w3c/rdf-tests.git ../rdf-tests
```

Try it against the bundled in-process rdflib engine — no server or engine installation needed:

```bash
sparql-conformance \
  --engine src/sparql_conformance/engines/rdflib_manager.py \
  --name rdflib-demo \
  --test-suites '{"sparql11":"../rdf-tests/sparql/sparql11"}' \
  --report summary
```

This writes `results/rdflib-demo.json.bz2` and prints a pass/fail summary. To test your own engine instead, write an `EngineManager` for it — see [Adding support for a new engine](#adding-support-for-a-new-engine) — and pass its file to `--engine`.

## Installation

```bash
pip install -e .
```

This installs the `sparql_conformance` package and both console scripts. The
standalone `sparql-conformance --engine <file>` workflow does not require
qlever-control. The named built-in engines and the
`sparql_conformance setup|test|analyze|visualize` workflow require
qlever-control and print the required installation command when it is absent.
See the [integration documentation](src/sparql_conformance/README.md).

**Prerequisites:** Python 3.9+, and the W3C test suite files (`git clone https://github.com/w3c/rdf-tests.git`).

## Usage

```bash
sparql-conformance \
  --engine <engine-file-or-type> \
  --name <run-name> \
  --test-suites '{"sparql11":"<path/to/sparql11>"}'
```

`--test-suites` is a required JSON object mapping result-suite names to directories. Add any number of standard or custom suites; they run in the order in which they appear in the object.

### Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `--engine` | yes | — | Path to a Python file containing an `EngineManager` subclass, or a named engine type if [qlever-control](https://github.com/ad-freiburg/qlever-control) is installed. See [Adding support for a new engine](#adding-support-for-a-new-engine). |
| `--name` | yes | — | Label for this run; output is written to `<results-dir>/<name>.json.bz2` |
| `--test-suites` | yes | — | JSON object mapping suite names to directories. Example: `--test-suites '{"sparql11":"/path/to/sparql11","my-suite":"/path/to/custom"}'` |
| `--results-dir` | no | `./results` | Directory for the output JSON file |
| `--port` | no | `7001` | Port the engine server listens on |
| `--graph-store` | no | engine-specific | Override the graph store endpoint supplied by the engine manager |
| `--binaries-directory` | no | `""` | Directory containing engine binaries (forwarded to the engine manager via `config.path_to_binaries`) |
| `--server-binary` | no | `qlever-server` | Server binary name (used by the bundled QLever-binaries engine manager) |
| `--index-binary` | no | `qlever-index` | Index-builder binary name (used by the bundled QLever-binaries engine manager) |
| `--exclude` | no | — | Comma-separated list of test names or group names to skip |
| `--include` | no | — | Comma-separated list of test names or group names to run (all others skipped) |
| `--type-alias` | no | — | JSON list of XSD type pairs treated as equivalent. See [Type aliases](#type-aliases). |
| `--report` | no | `none` | Console output verbosity: `none`, `summary`, or `line`. See [Console output](#console-output). |
| `--compare-to` | no | — | Path to a previous `<name>.json.bz2` run to compare against; prints regressions and fixes. See [Comparing against a previous run](#comparing-against-a-previous-run). |

### Example: QLever

```bash
sparql-conformance \
  --engine src/sparql_conformance/engines/qlever-binaries-manager.py \
  --name qlever-2024 \
  --test-suites '{"sparql11":"../rdf-tests/sparql/sparql11","sparql10":"../rdf-tests/sparql/sparql10"}' \
  --binaries-directory ../qlever/build
```

### Migrating suite arguments

`--test-suites` replaces `--sparql11-dir`, `--sparql10-dir`, and `--custom`; the old arguments are no longer accepted. The JSON keys become the suite keys in the result file. Keep the whole JSON value in single quotes in shells so its double quotes reach the application unchanged.

### Type aliases

Some engines return a numerically equivalent but differently typed literal (e.g. `xsd:int` instead of `xsd:integer`). Use `--type-alias` to mark these as intended deviations rather than failures:

```bash
sparql-conformance --engine ... --name my-run \
  --test-suites '{"sparql11":"../rdf-tests/sparql/sparql11"}' \
  --type-alias '[["http://www.w3.org/2001/XMLSchema#integer","http://www.w3.org/2001/XMLSchema#int"]]'
```

### Filtering tests

Run or skip a single test or group by name:

```bash
# Run only the property path group
sparql-conformance --engine ... --name my-run \
  --test-suites '{"sparql11":"../rdf-tests/sparql/sparql11"}' \
  --include pp01,pp02,pp06

# Skip the aggregates group
sparql-conformance --engine ... --name my-run \
  --test-suites '{"sparql11":"../rdf-tests/sparql/sparql11"}' \
  --exclude aggregates
```

## Output

Results are written to `<results-dir>/<name>.json.bz2` — a bzip2-compressed JSON file with one entry per test suite and a summary:

```json
{
  "version": 2,
  "suites": {
    "sparql11": { "tests": { "...": { "name": "...", "status": "Passed", "...": "..." } }, "info": { "passed": 512, "failed": 34, "...": "..." } },
    "sparql10": { "tests": { "...": "..." }, "info": { "...": "..." } }
  },
  "info": { "passed": 560, "tests": 620, "failed": 38, "passedFailed": 20, "notTested": 2 }
}
```

Each test entry also carries HTML-formatted diffs (`expectedHtml`, `gotHtml`) meant for a viewer such as [sparql-conformance-ui](https://github.com/SIRDNARch/sparql-conformance-ui).

## Console output

By default a run only prints progress and writes the JSON file. For readable feedback in the terminal, use `--report`:

| `--report` | What it prints |
|---|---|
| `none` (default) | Nothing extra — unchanged behavior. |
| `summary` | An end-of-run totals block (passed / failed / intended / not tested, per suite and overall) plus a list of the failed tests. |
| `line` | A live colored `PASS` / `FAIL` / `INTD` line per test as it runs, plus the summary. |

```bash
sparql-conformance --engine <engine-file> --name my-run \
  --test-suites '{"sparql11":"../rdf-tests/sparql/sparql11"}' --report line
```

Colors are only used when writing to a terminal; piping to a file (or setting `NO_COLOR`) produces plain text.

### Comparing against a previous run

Pass a previous result file to `--compare-to` to see what changed. It prints the **regressions** (tests that passed before and now fail) and **fixes** (tests that failed before and now pass):

```bash
sparql-conformance --engine <engine-file> --name new-run \
  --test-suites '{"sparql11":"../rdf-tests/sparql/sparql11"}' \
  --compare-to results/old-run.json.bz2
```

`--report` and `--compare-to` can be combined and work independently.

## Adding support for a new engine

See [`src/sparql_conformance/engines/README.md`](src/sparql_conformance/engines/README.md) for a step-by-step guide to writing an `EngineManager` for any SPARQL engine, including a minimal working example ([`rdflib_manager.py`](src/sparql_conformance/engines/rdflib_manager.py)).

## Running the framework's own tests

```bash
pip install -e .[dev]
pytest
```

## qlever-control integration

For built-in support of seven engines with no adapter to write, plus
`setup`/`analyze`/`visualize` commands, install both local checkouts in
editable mode. Install qlever-control first so sparql-conformance remains the
owner of the `sparql_conformance` executable:

```bash
python -m pip install -e ../qlever-control
python -m pip install -e .
```

The order matters when upgrading from an older qlever-control revision that
also installed the `sparql_conformance` executable: pip removes that old
executable while upgrading qlever-control. Reinstalling this package restores
the executable with sparql-conformance as its sole owner. If needed, the
equivalent module invocation is `python -m sparql_conformance visualize`.

Use the Git URL only when you intentionally want to test the pushed
qlever-control branch instead of your local working tree.

Then see
[`src/sparql_conformance/README.md`](src/sparql_conformance/README.md).
