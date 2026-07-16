"""Tests for semantic comparison of RDF-encoded SPARQL result sets."""

import xml.etree.ElementTree as ET

import pytest
import rdflib

from sparql_conformance.result_set_tools import (
    RESULT_SET,
    RESULT_SET_INDEX,
    compare_rdf_result_set,
    expected_is_result_set,
    is_select_or_ask,
    sparql_xml_to_result_set_ttl,
)
from sparql_conformance.test_object import Status


RS = "http://www.w3.org/2001/sw/DataAccess/tests/result-set#"


def select_xml(rows, variables=("value",)):
    head = "".join(f'<variable name="{name}"/>' for name in variables)
    body = "".join(f"<result>{row}</result>" for row in rows)
    return f"""<?xml version="1.0"?>
    <sparql xmlns="http://www.w3.org/2005/sparql-results#">
      <head>{head}</head><results>{body}</results>
    </sparql>"""


def literal_binding(value, name="value", attributes=""):
    return (
        f'<binding name="{name}"><literal {attributes}>'
        f"{value}</literal></binding>"
    )


def ordered_result(values):
    solutions = "\n".join(
        f"""rs:solution [
          rs:index {index} ;
          rs:binding [
            rs:variable "value" ;
            rs:value {value}
          ]
        ] ;"""
        for index, value in enumerate(values, start=1)
    )
    return f"""@prefix rs: <{RS}> .
    [] a rs:ResultSet ;
       rs:resultVariable "value" ;
       {solutions}
       .
    """


def test_select_xml_is_converted_with_one_based_indices():
    xml = select_xml([
        literal_binding("first"),
        literal_binding("second"),
    ])
    graph = rdflib.Graph()
    graph.parse(data=sparql_xml_to_result_set_ttl(xml), format="turtle")

    indices = sorted(
        int(value)
        for value in graph.objects(None, RESULT_SET_INDEX)
    )
    assert indices == [1, 2]


def test_unordered_result_preserves_terms_unbound_variables_and_shared_bnodes():
    xml = select_xml(
        [
            (
                '<binding name="uri"><uri>http://example.org/value</uri></binding>'
                '<binding name="typed"><literal datatype="http://www.w3.org/2001/XMLSchema#integer">42</literal></binding>'
                '<binding name="lang"><literal xml:lang="de">hallo</literal></binding>'
                '<binding name="node"><bnode>shared</bnode></binding>'
            ),
            '<binding name="node"><bnode>shared</bnode></binding>',
        ],
        variables=("uri", "typed", "lang", "node", "unbound"),
    )
    expected = f"""@prefix rs: <{RS}> .
    [] a rs:ResultSet ;
       rs:resultVariable "uri", "typed", "lang", "node", "unbound" ;
       rs:solution [
         rs:binding
           [ rs:variable "uri" ; rs:value <http://example.org/value> ],
               [ rs:variable "typed" ; rs:value 42 ],
               [ rs:variable "lang" ; rs:value "hallo"@de ],
               [ rs:variable "node" ; rs:value _:shared ]
       ] ;
       rs:solution [
         rs:binding [
           rs:variable "node" ; rs:value _:shared
         ]
       ] .
    """

    status, *_ = compare_rdf_result_set(expected, xml, "ttl")
    assert status == Status.PASSED


@pytest.mark.parametrize("value", ["true", "false"])
def test_ask_xml_is_converted_to_typed_boolean(value):
    xml = f"""<sparql xmlns="http://www.w3.org/2005/sparql-results#">
      <head/><boolean>{value}</boolean>
    </sparql>"""
    expected = f"""@prefix rs: <{RS}> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    [] a rs:ResultSet ; rs:boolean "{value}"^^xsd:boolean .
    """

    status, *_ = compare_rdf_result_set(expected, xml, "ttl")
    assert status == Status.PASSED


def test_empty_select_result_is_preserved():
    xml = """<sparql xmlns="http://www.w3.org/2005/sparql-results#">
      <head><variable name="x"/></head><results/>
    </sparql>"""
    expected = f"""@prefix rs: <{RS}> .
    [] a rs:ResultSet ; rs:resultVariable "x" .
    """
    status, *_ = compare_rdf_result_set(expected, xml, "ttl")
    assert status == Status.PASSED


def test_rdf_xml_result_set_is_detected_semantically():
    expected = f"""<?xml version="1.0"?>
    <rdf:RDF xmlns:rdf="{rdflib.RDF}" xmlns:rs="{RS}">
      <rs:ResultSet>
        <rs:boolean rdf:datatype="{rdflib.XSD.boolean}">true</rs:boolean>
      </rs:ResultSet>
    </rdf:RDF>"""
    assert expected_is_result_set(expected, "rdf")


def test_rdf_xml_ordered_result_set_is_compared_semantically():
    expected = f"""<?xml version="1.0"?>
    <rdf:RDF xmlns:rdf="{rdflib.RDF}" xmlns:rs="{RS}"
             xmlns:xsd="{rdflib.XSD}">
      <rs:ResultSet>
        <rs:resultVariable>value</rs:resultVariable>
        <rs:solution rdf:parseType="Resource">
          <rs:index rdf:datatype="{rdflib.XSD.integer}">1</rs:index>
          <rs:binding rdf:parseType="Resource">
            <rs:variable>value</rs:variable><rs:value>Alice</rs:value>
          </rs:binding>
        </rs:solution>
        <rs:solution rdf:parseType="Resource">
          <rs:index rdf:datatype="{rdflib.XSD.integer}">2</rs:index>
          <rs:binding rdf:parseType="Resource">
            <rs:variable>value</rs:variable><rs:value>Bob</rs:value>
          </rs:binding>
        </rs:solution>
      </rs:ResultSet>
    </rdf:RDF>"""
    correct = select_xml([
        literal_binding("Alice"),
        literal_binding("Bob"),
    ])
    reversed_rows = select_xml([
        literal_binding("Bob"),
        literal_binding("Alice"),
    ])

    assert compare_rdf_result_set(expected, correct, "rdf")[0] == Status.PASSED
    assert (
        compare_rdf_result_set(expected, reversed_rows, "rdf")[0]
        == Status.FAILED
    )


def test_turtle_result_set_is_detected_semantically():
    assert expected_is_result_set(
        f"@prefix rs: <{RS}> . [] a rs:ResultSet .",
        "ttl",
    )
    assert not expected_is_result_set(
        "@prefix ex: <http://example.org/> . ex:s ex:p ex:o .",
        "ttl",
    )


def test_ordered_results_require_the_actual_xml_order():
    expected = ordered_result(['"Alice"', '"Bob"'])
    correct = select_xml([
        literal_binding("Alice"),
        literal_binding("Bob"),
    ])
    reversed_rows = select_xml([
        literal_binding("Bob"),
        literal_binding("Alice"),
    ])

    assert compare_rdf_result_set(expected, correct, "ttl")[0] == Status.PASSED
    assert (
        compare_rdf_result_set(expected, reversed_rows, "ttl")[0]
        == Status.FAILED
    )


def test_unordered_results_ignore_actual_xml_order():
    expected = ordered_result(['"Alice"', '"Bob"']).replace(
        "rs:index 1 ;", ""
    ).replace("rs:index 2 ;", "")
    reversed_rows = select_xml([
        literal_binding("Bob"),
        literal_binding("Alice"),
    ])
    assert (
        compare_rdf_result_set(expected, reversed_rows, "ttl")[0]
        == Status.PASSED
    )


def test_ordered_duplicate_solutions_are_preserved():
    expected = ordered_result(['"same"', '"same"'])
    duplicate_rows = select_xml([
        literal_binding("same"),
        literal_binding("same"),
    ])
    one_row = select_xml([literal_binding("same")])
    assert (
        compare_rdf_result_set(expected, duplicate_rows, "ttl")[0]
        == Status.PASSED
    )
    assert (
        compare_rdf_result_set(expected, one_row, "ttl")[0]
        == Status.FAILED
    )


@pytest.mark.parametrize(
    "indices",
    [
        ("rs:index 1 ;", ""),
        ('rs:index "first" ;', 'rs:index "second" ;'),
        ("rs:index 1, 2 ;", "rs:index 2 ;"),
    ],
)
def test_malformed_or_partial_order_indices_are_rejected(indices):
    expected = ordered_result(['"Alice"', '"Bob"'])
    expected = expected.replace("rs:index 1 ;", indices[0])
    expected = expected.replace("rs:index 2 ;", indices[1])
    actual = select_xml([
        literal_binding("Alice"),
        literal_binding("Bob"),
    ])
    with pytest.raises(ValueError, match="rs:index|integer"):
        compare_rdf_result_set(expected, actual, "ttl")


def test_malformed_xml_is_rejected():
    with pytest.raises(ET.ParseError):
        sparql_xml_to_result_set_ttl("<sparql>")


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("SELECT * WHERE { ?s ?p ?o }", True),
        ("PREFIX ex: <http://example.org/> ASK { ?s ?p ?o }", True),
        ("# SELECT is only a comment\nCONSTRUCT { ?s ?p ?o } WHERE {}", False),
        ("DESCRIBE <http://example.org/>", False),
    ],
)
def test_query_form_detection(query, expected):
    assert is_select_or_ask(query) is expected
