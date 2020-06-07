from morphapi.morphology.morphology import Neuron
from vtkplotter import Mesh


def test_create_mesh():
    fp = "tests/data/example1.swc"

    # Create vtkplotter actors from the .swc file
    neuron = Neuron(swc_file=fp)
    components, neuron = neuron.create_mesh(
        neurite_radius=3,  #
        soma_color="salmon",  # Specify colors [see vtkplotter.colors for more details]
        apical_dendrites_color="darkseagreen",
        basal_dendrites_color="orangered",
        axon_color="blackboard",
        whole_neuron_color="blackboard",
    )

    if not isinstance(neuron, Mesh):
        raise ValueError

    if not isinstance(components, dict):
        raise ValueError

    for ntp in Neuron._neurite_types:
        if ntp not in components.keys():
            raise ValueError
        if components[ntp] is not None:
            if not isinstance(components[ntp], Mesh):
                raise ValueError
