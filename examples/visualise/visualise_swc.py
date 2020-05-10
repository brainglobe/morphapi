from vtkplotter import Plotter

from morphapi.morphology.morphology import Neuron

"""
    This example shows how to use vtkplotter to visualise a 3d reconstruction of a neuron.
    However, the reccomended way to visualise neurons is with brainrender:
    https://github.com/BrancoLab/BrainRender
"""

fp = 'examples/example_files/example1.swc'

# Create vtkplotter actors from the .swc file
neuron = Neuron(swc_file=fp)
components, neuron = neuron.create_mesh(neurite_radius=3, #
                soma_color='salmon', # Specify colors [see vtkplotter.colors for more details]
                apical_dendrites_color='darkseagreen',
                basal_dendrites_color='orangered',
                axon_color='blackboard',
                whole_neuron_color='blackboard')

# components stores an actor for each neuronal component (dendrites, soma...)
# neuron is a single actor for the entire neuron


# Show neuron as individual components or entire neuron
vp = Plotter(shape=(1, 2), axes=1)
vp.show(*list(components.values()), at=0, interactive=False)
vp.show(neuron, at=1,interactive=True)

