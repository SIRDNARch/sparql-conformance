# Writing a custom EngineManager

An `EngineManager` is the adapter between this test harness and a SPARQL engine. Its a single Python file that you pass to `--engine`. The harness dynamically loads the first `EngineManager` subclass it finds in that file.

## Quickstart

1. Copy the skeleton below into a new file, e.g. `my-engine-manager.py`.
2. Implement the five abstract methods.
3. Run: `python3 main.py --engine ./my-engine-manager.py --name myrun --sparql11-dir ...`

## Skeleton

```python
import subprocess
import requests
import time
from typing import Tuple, Optional

from src.config import Config
from src.engines.engine_manager import EngineManager


class MyEngineManager(EngineManager):

    def setup(
        self,
        config: Config,
        graph_paths: Tuple[Tuple[str, str], ...],
    ) -> Tuple[bool, bool, str, str]:
        """
        Load data and start the engine.

        graph_paths is a tuple of (file_path, graph_name) pairs.
        graph_name is "-" for the default graph, or a URI string for named graphs.

        Returns: (index_success, server_success, index_log, server_log)
        """
        # 1. Build an index / load data from graph_paths
        # 2. Start the server on config.port
        # 3. Return success flags and log strings
        ...

    def cleanup(self, config: Config):
        """Stop the server and delete any temporary files."""
        ...

    def query(self, config: Config, query: str, result_format: str) -> Tuple[int, str]:
        """
        Execute a SPARQL SELECT / CONSTRUCT / ASK query.

        result_format is one of: "json", "xml", "ttl", "csv", "tsv", "srj", "srx"

        Returns: (http_status_code, response_body)
        """
        ...

    def update(self, config: Config, query: str) -> Tuple[int, str]:
        """
        Execute a SPARQL UPDATE query.

        Returns: (http_status_code, response_body)
        """
        ...

    def protocol_endpoint(self) -> str:
        """
        The path segment used for the SPARQL endpoint, e.g. "sparql".
        Protocol tests send requests to http://localhost:<port>/<protocol_endpoint>.
        """
        return "sparql"
```

## The Config object

`config` is passed to every method and exposes:

| Attribute | Type | Description |
|---|---|---|
| `config.server_address` | `str` | Always `"localhost"` |
| `config.port` | `str` | Port from `--port` (default `"7001"`) |
| `config.path_to_binaries` | `str` | Absolute path from `--binaries-directory`; empty string if not set |
| `config.GRAPHSTORE` | `str` | Graph store endpoint path from `--graph-store` (default `"sparql"`) |
| `config.path_to_test_suite` | `str` | Absolute path to the test suite directory |
| `config.alias` | `list` | Type alias pairs from `--type-alias` |
| `config.exclude` | `list[str]` | Test/group names to skip |
| `config.include` | `list[str] \| None` | Test/group names to run (or `None` for all) |

## How `setup` is called

The harness groups tests by the set of RDF files they need. For each unique group, it calls `setup` once, runs all tests in that group, then calls `cleanup`. This cycle repeats for every group.

`graph_paths` always contains at least one entry. The graph name `"-"` means the default graph:

```python
# Single default graph
graph_paths = (("/path/to/data.ttl", "-"),)

# Default graph + one named graph
graph_paths = (
    ("/path/to/base.ttl", "-"),
    ("/path/to/named.ttl", "http://example.org/graph1"),
)
```

File formats you may receive: `.ttl`, `.nt`, `.nq`, `.trig`, `.rdf` (RDF/XML).

## Optional overrides

These methods have working defaults but can be overridden when needed.

### `protocol_update_endpoint() -> str`

If your engine exposes SPARQL UPDATE on a different path than SELECT, override this:

```python
def protocol_update_endpoint(self) -> str:
    return "sparql/update"  # default falls back to protocol_endpoint()
```

### `default_graph_construct_query() -> str`

Used by update tests to read back the default graph after a SPARQL UPDATE and compare it with the expected result. The default returns:

```sparql
CONSTRUCT {?s ?p ?o} WHERE { ?s ?p ?o }
```

Override this if your engine stores the default graph under a named IRI. Examples:

```python
# QLever: default graph lives at ql:default-graph
def default_graph_construct_query(self) -> str:
    return "CONSTRUCT {?s ?p ?o} WHERE { GRAPH ql:default-graph {?s ?p ?o}}"

# Blazegraph in quads mode: default graph is nullGraph
def default_graph_construct_query(self) -> str:
    return (
        "CONSTRUCT {?s ?p ?o} WHERE { "
        "GRAPH <http://www.bigdata.com/rdf#nullGraph> {?s ?p ?o}}"
    )
```

### `activate_syntax_test_mode(server_address: str, port: str)`

Called before syntax tests if your engine needs a special mode to return error responses for invalid queries rather than silently accepting them. Default implementation does nothing.
