from pathlib import Path

from qlever.command import QleverCommand
from qlever.log import log
from sparql_conformance.config import Config
from sparql_conformance.engines import ENGINE_TYPES, get_engine_manager
from sparql_conformance.extract_tests import extract_tests
from sparql_conformance.runner import assemble_suites
from sparql_conformance.testsuite import TestSuite
from sparql_conformance.util import warn_if_missing_image


class AnalyzeCommand(QleverCommand):
    """
    Class for executing the `analyze` command.
    """

    def __init__(self):
        self.options = ENGINE_TYPES

    def description(self) -> str:
        return "Run SPARQL conformance tests against different engines"

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str, list[str]]:
        return {
            "conformance": ["name", "port", "engine", "graph_store",
                            "sparql11_dir", "sparql10_dir", "custom",
                            "type_alias", "exclude", "binaries_directory"],
            "runtime": ["system"],
            "qlever": ["qlever_image"],
            "oxigraph": ["oxigraph_image"],
            "blazegraph": ["blazegraph_image"],
            "virtuoso": ["virtuoso_image"],
            "graphdb": ["graphdb_image"],
            "jena": ["jena_image"],
            "mdb": ["mdb_image"],
        }

    def additional_arguments(self, subparser):
        subparser.add_argument(
            "include",
            type=str,
            nargs="+",
            help="Name(s) of the test(s) to start the server for.",
        )

    def execute(self, args) -> bool:
        if args.engine not in self.options:
            log.error(f"Invalid engine type: {args.engine}")
            return False
        image = getattr(args, f"{args.engine}_image", None)
        if (args.system == "native" and args.binaries_directory == "" or
                args.system != "native" and image is None and args.engine != "blazegraph"):
            log.error(
                f"Selected system {args.system} not compatible with image: {image}"
                f" and binaries_directory: {args.binaries_directory}"
            )
            return False

        warn_if_missing_image(args.system, image, args.engine)

        active_suites = assemble_suites(
            args.sparql11_dir, args.sparql10_dir, args.custom
        )

        if not active_suites:
            log.error("Provide at least one of --sparql11-dir, --sparql10-dir, --custom.")
            return False

        for _, d in active_suites:
            if not Path(d).is_dir():
                log.error(f"Test suite directory not found: {d}. Use `sparql_conformance setup` to download it.")
                return False

        if args.engine == "blazegraph" and args.graph_store == "sparql":
            args.graph_store = "blazegraph/namespace/kb/sparql"
        if args.engine == "jena" and args.graph_store == "sparql":
            args.graph_store = "qlever-sparql-conformance/data"

        alias = [tuple(x) for x in args.type_alias] if args.type_alias else []

        for suite_key, suite_dir in active_suites:
            config = Config(image, args.system, args.port, args.graph_store, suite_dir, alias,
                            args.binaries_directory, args.exclude, args.include)
            tests, test_count = extract_tests(config)
            if test_count == 0:
                continue
            test_suite = TestSuite(name=args.name, tests=tests, test_count=test_count,
                                   config=config, engine_manager=get_engine_manager(args.engine))
            test_suite.analyze()
        return True
