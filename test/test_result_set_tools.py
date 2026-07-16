"""Tests for SPARQL XML to legacy RDF result-set normalization."""

import xml.etree.ElementTree as ET

import pytest

from sparql_conformance.rdf_tools import compare_ttl
from sparql_conformance.result_set_tools import (
    is_select_or_ask,
    sparql_xml_to_result_set_ttl,
)
from sparql_conformance.test_object import Status


RS = "http://www.w3.org/2001/sw/DataAccess/tests/result-set#"


def test_select_xml_is_converted_to_result_set_turtle():
    xml = """<?xml version="1.0"?>
    <sparql xmlns="http://www.w3.org/2005/sparql-results#">
      <head>
        <variable name="uri"/><variable name="typed"/>
        <variable name="lang"/><variable name="node"/>
        <variable name="unbound"/>
      </head>
      <results><result>
        <binding name="uri"><uri>http://example.org/value</uri></binding>
        <binding name="typed"><literal datatype="http://www.w3.org/2001/XMLSchema#integer">42</literal></binding>
        <binding name="lang"><literal xml:lang="de">hallo</literal></binding>
        <binding name="node"><bnode>b1</bnode></binding>
      </result></results>
    </sparql>"""
    expected = f"""@prefix rs: <{RS}> .
    [] a rs:ResultSet ;
       rs:resultVariable "uri", "typed", "lang", "node", "unbound" ;
       rs:solution [
         rs:binding
           [ rs:variable "uri" ; rs:value <http://example.org/value> ],
           [ rs:variable "typed" ; rs:value 42 ],
           [ rs:variable "lang" ; rs:value "hallo"@de ],
           [ rs:variable "node" ; rs:value _:expectedNode ]
       ] .
    """

    status, *_ = compare_ttl(
        expected, sparql_xml_to_result_set_ttl(xml)
    )
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

    status, *_ = compare_ttl(
        expected, sparql_xml_to_result_set_ttl(xml)
    )
    assert status == Status.PASSED


def test_empty_select_result_is_preserved():
    xml = """<sparql xmlns="http://www.w3.org/2005/sparql-results#">
      <head><variable name="x"/></head><results/>
    </sparql>"""
    expected = f"""@prefix rs: <{RS}> .
    [] a rs:ResultSet ; rs:resultVariable "x" .
    """
    status, *_ = compare_ttl(
        expected, sparql_xml_to_result_set_ttl(xml)
    )
    assert status == Status.PASSED


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
