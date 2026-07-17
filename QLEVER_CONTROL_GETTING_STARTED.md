# Getting started with sparql-conformance and qlever-control

This guide explains how to install `sparql-conformance` together with
`qlever-control` and run the W3C SPARQL conformance test suites against
QLever.

> [!NOTE]
> The integration is currently under review in upstream pull requests. Until
> those pull requests are merged, clone both projects from the `SIRDNARch`
> forks as shown below.

## Prerequisites

Install the following before you begin:

- Git
- Python 3.10 or newer
- Docker or Podman

Make sure that your container runtime is running before starting the tests.
The generated QLever configuration uses containers by default.

## 1. Create a working directory and virtual environment

```bash
mkdir sparql-conformance-qlever
cd sparql-conformance-qlever

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## 2. Clone sparql-conformance from the development fork

The pending integration changes are on the `main` branch of the `SIRDNARch`
fork. No additional branch switch is required after cloning, but the explicit
`git switch main` below makes the expected branch clear.

```bash
git clone https://github.com/SIRDNARch/sparql-conformance.git
cd sparql-conformance
git switch main
cd ..
```

The older `unify-package` development branch is no longer needed because its
changes have been merged into `main`.

## 3. Clone qlever-control from the development fork

The corresponding pending changes live on the
`sparql-conformance-command-all-engines` branch of the `SIRDNARch` fork.

```bash
git clone https://github.com/SIRDNARch/qlever-control.git
cd qlever-control
git switch sparql-conformance-command-all-engines
cd ..
```

You can alternatively clone that branch directly:

```bash
git clone \
  --branch sparql-conformance-command-all-engines \
  https://github.com/SIRDNARch/qlever-control.git
```

## 4. Install both projects

Install both projects into the same virtual environment. Install
`sparql-conformance` first so that the qlever-control dependency is already
available locally.

```bash
python -m pip install -e ./sparql-conformance
python -m pip install -e ./qlever-control
```

Verify that the integrated commands are available:

```bash
sparql_conformance --help
qlever --help
```

The integrated qlever-control command is named `sparql_conformance`, with an
underscore. The standalone command installed by `sparql-conformance` is named
`sparql-conformance`, with a hyphen.

## 5. Create a directory for the QLever test run

Use a separate working directory for every engine. The setup command creates
an engine-specific `Qleverfile` in the current directory.

```bash
mkdir qlever-conformance
cd qlever-conformance
```

## 6. Set up the test suite

```bash
sparql_conformance setup qlever
```

This command:

- creates `./Qleverfile`;
- downloads the W3C SPARQL 1.0 and 1.1 test suites into
  `./testsuite-files`.

You do not need to clone `w3c/rdf-tests` separately.

## 7. Run the tests

Run the complete test suite and print a summary:

```bash
sparql_conformance test --report summary
```

To print one live result line per test, use:

```bash
sparql_conformance test --report line
```

The result is written to:

```text
./results/qlever.json.bz2
```

## Complete command sequence

```bash
mkdir sparql-conformance-qlever
cd sparql-conformance-qlever

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

git clone https://github.com/SIRDNARch/sparql-conformance.git
cd sparql-conformance
git switch main
cd ..

git clone https://github.com/SIRDNARch/qlever-control.git
cd qlever-control
git switch sparql-conformance-command-all-engines
cd ..

python -m pip install -e ./sparql-conformance
python -m pip install -e ./qlever-control

mkdir qlever-conformance
cd qlever-conformance

sparql_conformance setup qlever
sparql_conformance test --report summary
```

When opening a new terminal later, return to the top-level working directory
and reactivate the virtual environment before using the commands:

```bash
source .venv/bin/activate
```
