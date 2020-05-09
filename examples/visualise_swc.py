from vtkplotter import Plotter

from morphapi.morphology.morphology import Neuron

fp = 'test.swc'


neuro = Neuron(swc_file=fp)

components, neuron = neuro.create_mesh(fixed_neurite_radius=.3,
                soma_color='salmon',
                apical_dendrites_color='darkseagreen',
                basal_dendrites_color='orangered',
                axon_color='blackboard',
                whole_neuron_color='ivory')


# Show neuron as individual components or entire neuron
vp = Plotter(shape=(1, 2), axes=1)
vp.show(*list(components.values()), at=0, interactive=False)
vp.show(neuron, at=1,interactive=True)

