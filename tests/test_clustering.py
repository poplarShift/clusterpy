"""
Testing clustering algorithms in Clusterpy -Arisel-
** All the following tests take considerable time to complete **
"""

from unittest import TestCase
from nose.plugins.attrib import attr
import clusterpy
from numpy.random import seed as make_static_random
from clusterpy.core.toolboxes.cluster.componentsAlg import AreaManager

map_type = 'n100'
into_regions = 10

sample_input_path = "clusterpy/data_examples/" + map_type
sample_output_path = "tests/sample_output/" + map_type

class TestArisel(TestCase):
    def setUp(self):
        self.map_instance = clusterpy.importArcData(sample_input_path)

    def tearDown(self):
        # Remove generated output/Arc data
        pass

    @attr('slow')
    def test_arisel_never_breaks_contiguity(self):
        """
        Tests that the output regions never break the contiguity constraint.
        """
        instance = self.map_instance

        make_static_random(10)
        instance.cluster('arisel', ['SAR1'],
                                  into_regions, dissolve = 1,
                                  inits = 20)

        exp_name = instance.fieldNames[-1]
        clustering_results = instance.outputCluster[exp_name]
        final_region_assignment = clustering_results['r2a']

        am = AreaManager(instance.Wrook, instance.Y)
        feasible = am.checkFeasibility(final_region_assignment)
        self.assertTrue(feasible)

    @attr('slow')
    def test_arisel_gives_at_least_same_obj_func(self):
        """
        Tests that the objective function is at least the same, but not worse.
        """
        instance = self.map_instance

        make_static_random(10)
        initial_obj_func = float(90.1868744781) # Using a seed of 10

        instance.cluster('arisel', ['SAR1'],
                                  into_regions, dissolve = 1,
                                  inits = 20)

        exp_name = instance.fieldNames[-1]
        clustering_results = instance.outputCluster[exp_name]
        final_obj_func = clustering_results['objectiveFunction']

        assert initial_obj_func >= final_obj_func
