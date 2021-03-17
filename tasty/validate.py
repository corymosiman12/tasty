import os

import rdflib
from rdflib import Graph, SH
from rdflib.util import guess_format
from pyshacl import validate
import pandas as pd

import tasty.constants as tc
import tasty.graphs as tg
from tasty.generated_shapes import load_all_shapes_and_merge

tasty_dir = os.path.dirname(__file__)


def pretty_print_errors(results_graph: Graph) -> None:
    """
    Print out errors (sh:Violation) vs. warnings (sh:Warning) given a results graph.
    Grabs the focus node (i.e. what the error fired on) and the shape
    that was fired.

    :param results_graph: graph used to generate the output
    :return:
    """
    q_warn = '''SELECT ?fn ?bad_shape WHERE {
        ?n a sh:ValidationReport .
        ?n sh:result ?vr .
        ?vr sh:focusNode ?fn .
        ?vr sh:resultSeverity sh:Warning .
        ?vr sh:sourceShape ?shape .
        ?shape sh:qualifiedValueShape ?bad_shape .
    }'''
    q_error = '''SELECT ?fn ?bad_shape WHERE {
        ?n a sh:ValidationReport .
        ?n sh:result ?vr .
        ?vr sh:focusNode ?fn .
        ?vr sh:resultSeverity sh:Violation .
        ?vr sh:sourceShape ?shape .
        ?shape sh:qualifiedValueShape ?bad_shape .
    }'''
    warnings = results_graph.query(q_warn)
    errors = results_graph.query(q_error)
    print("-" * 100)
    print(f"Warnings: {len(warnings)}")
    for warning in warnings:
        print(f"Warning on entity: {warning[0]}, triggered by shape: {warning[1]}")
    print("-" * 100)
    print(f"Errors: {len(errors)}")
    for error in errors:
        print(f"Error on entity: {error[0]}, triggered by shape: {error[1]}")
    print("-" * 100)


def validate_from_csv(data_graph: str, input_file: str) -> None:
    """
    Given a csv as generated by generate_input_file, add the marked entities as target nodes
    for the specific shapes and run through a SHACL validator. Merges all ttl files from
    tasty/generated_shapes into a single graph for simplicity.

    :param data_graph: path to a data graph to load
    :param input_file: path to the input csv file
    :return:
    """
    shapes_graph = load_all_shapes_and_merge()
    data_graph = Graph().parse(data_graph, format=guess_format(data_graph))
    data = pd.read_csv(input_file, index_col='entity-id', true_values='X').fillna(value=False)
    for entity_id, vals in data.iterrows():
        for shape_name, val in vals.iteritems():
            if val is True:
                if rdflib.term.URIRef(entity_id) not in data_graph.subjects():
                    print(f"Entity does not exist: {entity_id}")
                else:
                    str_ns, shape_name = shape_name.split(':')
                    ns = tc.namespace_map[str_ns]
                    print(f"Targeting entity {entity_id} with shape {shape_name}")
                    shapes_graph.add((ns[shape_name], SH.targetNode, rdflib.term.URIRef(entity_id)))

    shapes_graph_output_file = 'shapes.ttl'
    shapes_graph.serialize(shapes_graph_output_file, format='turtle')
    ont_graph = tg.load_ontology(tc.HAYSTACK, tc.V3_9_10)

    conforms, results_graph, results = validate(data_graph, shacl_graph=shapes_graph, ont_graph=ont_graph)
    output_file_name = f"results-{os.path.splitext(os.path.basename(data_graph))[0]}.ttl"

    results_graph.serialize(output_file_name, format='turtle')
    if not conforms:
        pretty_print_errors(results_graph)

    print(f"Validation report saved at: {output_file_name}")
    print(f"Copy of shapes graph saved at: {shapes_graph_output_file}")
    print("-" * 100)
