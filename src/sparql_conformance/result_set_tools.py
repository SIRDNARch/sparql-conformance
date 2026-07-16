"""Helpers for normalizing SPARQL result sets used by legacy test suites."""

import re
import xml.etree.ElementTree as ET

import rdflib


SPARQL_RESULTS_NS = "http://www.w3.org/2005/sparql-results#"
RESULT_SET = rdflib.Namespace(
    "http://www.w3.org/2001/sw/DataAccess/tests/result-set#"
)


def is_select_or_ask(query: str) -> bool:
    """Return whether the first query form in ``query`` is SELECT or ASK."""
    without_comments = re.sub(r"#[^\n]*", "", query)
    match = re.search(
        r"\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b",
        without_comments,
        re.IGNORECASE,
    )
    return match is not None and match.group(1).upper() in ("SELECT", "ASK")


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
        for result in results.findall(f"{{{ns}}}result"):
            solution = rdflib.BNode()
            graph.add((result_set, RESULT_SET.solution, solution))
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
