"""Helpers for RDF-encoded SPARQL result sets used by legacy test suites."""

import xml.etree.ElementTree as ET

import rdflib
from rdflib.plugins.sparql.parser import parseQuery


SPARQL_RESULTS_NS = "http://www.w3.org/2005/sparql-results#"
RESULT_SET = rdflib.Namespace(
    "http://www.w3.org/2001/sw/DataAccess/tests/result-set#"
)
RESULT_SET_INDEX = RESULT_SET["index"]


def is_select_or_ask(query: str) -> bool:
    """Return whether RDFLib parses ``query`` as SELECT or ASK."""
    try:
        query_form = parseQuery(query)[1].name
    except Exception:
        return False
    return query_form in ("SelectQuery", "AskQuery")


def _new_result_set_graph():
    graph = rdflib.Graph()
    graph.bind("rs", RESULT_SET)
    result_set = rdflib.BNode()
    graph.add((result_set, rdflib.RDF.type, RESULT_SET.ResultSet))
    return graph, result_set


def _add_boolean(graph, result_set, value) -> str:
    graph.add(
        (
            result_set,
            RESULT_SET.boolean,
            rdflib.Literal(value, datatype=rdflib.XSD.boolean),
        )
    )
    return graph.serialize(format="turtle")


def _add_binding(graph, solution, name, value) -> None:
    binding = rdflib.BNode()
    graph.add((solution, RESULT_SET.binding, binding))
    graph.add((binding, RESULT_SET.variable, rdflib.Literal(name)))
    graph.add((binding, RESULT_SET.value, value))


def sparql_xml_to_result_set_ttl(xml_string: str) -> str:
    """Convert SPARQL Results XML to the SPARQL 1.0 result-set vocabulary."""
    root = ET.fromstring(xml_string)
    graph, result_set = _new_result_set_graph()
    ns = SPARQL_RESULTS_NS

    boolean = root.find(f"{{{ns}}}boolean")
    if boolean is not None:
        value = (boolean.text or "").strip().lower() == "true"
        return _add_boolean(graph, result_set, value)

    head = root.find(f"{{{ns}}}head")
    if head is not None:
        for variable in head.findall(f"{{{ns}}}variable"):
            graph.add(
                (
                    result_set,
                    RESULT_SET.resultVariable,
                    rdflib.Literal(variable.get("name")),
                )
            )

    results = root.find(f"{{{ns}}}results")
    if results is not None:
        for index, result in enumerate(
            results.findall(f"{{{ns}}}result"), start=1
        ):
            solution = rdflib.BNode()
            graph.add((result_set, RESULT_SET.solution, solution))
            graph.add(
                (
                    solution,
                    RESULT_SET_INDEX,
                    rdflib.Literal(index, datatype=rdflib.XSD.integer),
                )
            )
            for binding in result.findall(f"{{{ns}}}binding"):
                name = binding.get("name")
                uri = binding.find(f"{{{ns}}}uri")
                literal = binding.find(f"{{{ns}}}literal")
                bnode = binding.find(f"{{{ns}}}bnode")

                if uri is not None:
                    value = rdflib.URIRef((uri.text or "").strip())
                elif literal is not None:
                    text = literal.text or ""
                    datatype = literal.get("datatype")
                    language = literal.get(
                        "{http://www.w3.org/XML/1998/namespace}lang"
                    )
                    if datatype:
                        value = rdflib.Literal(
                            text, datatype=rdflib.URIRef(datatype)
                        )
                    elif language:
                        value = rdflib.Literal(text, lang=language)
                    else:
                        value = rdflib.Literal(text)
                elif bnode is not None:
                    value = rdflib.BNode((bnode.text or "").strip())
                else:
                    continue
                _add_binding(graph, solution, name, value)

    return graph.serialize(format="turtle")


def parse_expected_rdf(
    rdf_string: str,
    rdf_format: str,
    public_id: str | None = None,
) -> rdflib.Graph:
    """Parse an RDF expectation using the format implied by its extension."""
    formats = {"rdf": "xml", "ttl": "turtle"}
    if rdf_format not in formats:
        raise ValueError(f"Unsupported RDF expectation format: {rdf_format}")
    graph = rdflib.Graph()
    graph.parse(
        data=rdf_string,
        format=formats[rdf_format],
        publicID=public_id,
    )
    return graph


def is_result_set_graph(graph: rdflib.Graph) -> bool:
    """Return whether an RDF graph semantically contains an rs:ResultSet."""
    return any(graph.subjects(rdflib.RDF.type, RESULT_SET.ResultSet))


def expected_is_result_set(
    rdf_string: str,
    rdf_format: str,
    public_id: str | None = None,
) -> bool:
    """Return whether a Turtle or RDF/XML expectation is an RDF result set."""
    if rdf_format not in ("rdf", "ttl"):
        return False
    return is_result_set_graph(
        parse_expected_rdf(rdf_string, rdf_format, public_id)
    )


def _validate_expected_indices(graph: rdflib.Graph) -> bool:
    """Validate ordered result-set metadata and return whether it is present."""
    solutions = [
        solution
        for result_set in graph.subjects(
            rdflib.RDF.type, RESULT_SET.ResultSet
        )
        for solution in graph.objects(result_set, RESULT_SET.solution)
    ]
    index_values = [
        list(graph.objects(solution, RESULT_SET_INDEX))
        for solution in solutions
    ]
    has_indices = any(index_values)
    if not has_indices:
        return False
    for values in index_values:
        if len(values) != 1:
            raise ValueError(
                "Ordered RDF result sets require exactly one rs:index per "
                "solution."
            )
        value = values[0]
        python_value = value.toPython() if isinstance(
            value, rdflib.Literal
        ) else None
        if (
            not isinstance(value, rdflib.Literal)
            or isinstance(python_value, bool)
            or not isinstance(python_value, int)
        ):
            raise ValueError(
                "Every rs:index in an ordered RDF result set must be an "
                "integer literal."
            )
    return True


def compare_rdf_result_set(
    expected_rdf: str,
    actual_xml: str,
    expected_format: str,
    public_id: str | None = None,
) -> tuple:
    """Compare an RDF result-set expectation with SPARQL Results XML."""
    from sparql_conformance.rdf_tools import compare_ttl

    expected_graph = parse_expected_rdf(
        expected_rdf,
        expected_format,
        public_id,
    )
    if not is_result_set_graph(expected_graph):
        raise ValueError("Expected RDF graph is not an rs:ResultSet.")

    ordered = _validate_expected_indices(expected_graph)
    actual_graph = rdflib.Graph()
    actual_graph.parse(
        data=sparql_xml_to_result_set_ttl(actual_xml),
        format="turtle",
    )
    if not ordered:
        actual_graph.remove((None, RESULT_SET_INDEX, None))

    return compare_ttl(
        expected_graph.serialize(format="turtle"),
        actual_graph.serialize(format="turtle"),
    )
