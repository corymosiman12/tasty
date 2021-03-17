import os

import pytest
from rdflib import Namespace, SH
from pyshacl import validate

import tasty.graphs
from tasty import constants as tc
from tasty import graphs as tg
from tests.conftest import get_single_node_validation_query, assert_remove_markers, write_csv, \
    get_parent_node_validation_query, get_severity_query, run_another, get_validate_dir

SAMPLE = Namespace('urn:sample/')


class TestNRELVavCoolingOnly:
    @pytest.mark.parametrize('shape_name, target_node', [
        [tc.PH_SHAPES_NREL['NREL-VAV-SD-Cooling-Only-Shape'], SAMPLE['NREL-VAV-01']]
    ])
    def test_is_valid(self, get_haystack_nrel_data, get_haystack_nrel_generated_shapes, shape_name, target_node):
        # -- Setup
        data_graph = get_haystack_nrel_data
        shapes_graph = get_haystack_nrel_generated_shapes
        ont_graph = tg.load_ontology(tc.HAYSTACK, tc.V3_9_9)
        validate_dir = os.path.join(os.path.dirname(__file__), 'output/validate')
        if not os.path.isdir(validate_dir):
            os.mkdir(validate_dir)

        # -- Setup
        shapes_graph.add((shape_name, SH.targetNode, target_node))

        result = validate(data_graph, shacl_graph=shapes_graph, ont_graph=ont_graph)
        conforms, results_graph, results = result

        # -- Serialize results
        f = 'TestNRELVavCoolingOnly' + '_valid.ttl'
        output_file = os.path.join(validate_dir, f)
        results_graph.serialize(output_file, format='turtle')

        # -- Assert conforms
        assert conforms

    @pytest.mark.parametrize('shape_name, target_node, remove_from_node, remove_markers, num_runs', [
        [
            tc.PH_SHAPES_NREL['NREL-VAV-SD-Cooling-Only-Shape'], SAMPLE['NREL-VAV-01'],
            SAMPLE['NREL-VAV-01-ZoneRelativeHumiditySensor'], ['zone'], 2
        ],
    ])
    def test_is_invalid(self, get_haystack_nrel_data, get_haystack_nrel_generated_shapes, shape_name, target_node,
                        remove_from_node,
                        remove_markers, num_runs):
        # Set version for constants
        tc.set_default_versions(haystack_version=tc.V3_9_10)

        # -- Setup
        data_graph = get_haystack_nrel_data
        shapes_graph = get_haystack_nrel_generated_shapes
        ont_graph = tg.load_ontology(tc.HAYSTACK, tc.V3_9_10)
        validate_dir = get_validate_dir()

        # -- Setup
        shapes_graph.add((shape_name, SH.targetNode, target_node))
        for marker in remove_markers:
            ns = tg.get_namespaces_given_term(ont_graph, marker)
            if tasty.graphs.has_one_namespace(ns, marker):
                ns = ns[0]
                data_graph.remove((remove_from_node, tc.PH_DEFAULT.hasTag, ns[marker]))

        result = validate(data_graph, shacl_graph=shapes_graph, ont_graph=ont_graph)
        conforms, results_graph, results = result

        # -- Serialize results
        f = 'TestNREL_' + '_'.join(remove_markers) + '_remove.ttl'
        output_file = os.path.join(validate_dir, f)
        results_graph.serialize(output_file, format='turtle')

        # -- Assert does not conform
        assert not conforms

        # Grab easy to read info
        str_name = str(shape_name)
        str_name = str_name.split('#')[1]
        target_name = str(target_node)
        target_name = target_name.split(str(SAMPLE))[1]

        # Here we iterate through to add target nodes
        # based on
        for run in range(num_runs - 1):
            print(f"Iteration {run} on {str_name}")
            conforms, results_graph, results = run_another(results_graph, shapes_graph, data_graph, ont_graph)

        # -- Serialize results
        f = f"NREL_{str_name}_{target_name}" + '_'.join(remove_markers) + '_remove.ttl'
        output_file = os.path.join(validate_dir, f)
        results_graph.serialize(output_file, format='turtle')

        # -- Assert does not conform
        assert not conforms