from vtkplotter import Plotter

from morphapi.morphology.morphology import Neuron
from morphapi.api.allenmorphology import AllenMorphology

amapi = AllenMorphology()

# ---------------------------- Downloading neurons --------------------------- #
print('Neurons metadata:')
print(amapi.neurons.head())
# you can use the metadata to select which neurons to download

# e.g. select only neurons with full reconstructions
neurons_metadata = amapi.neurons.loc[amapi.neurons['reconstruction_type'] == 'full']

print('\n\ndownloading neurons')
neurons = amapi.download_neurons(neurons_metadata.id.values[0])
# Download neurons by passing IDs values

"""
    amapi.download_neurons returns a list of instances of the class Neuron
    from morphapi.morphology.morphology.
"""


# ------------------------------- Visualisation ------------------------------ #
print('creating meshes')
neurons = [neuron.create_mesh()[1] for neuron in neurons]

print('visualizing')
vp = Plotter(shape=(1, len(neurons)), axes=1)

vp.show(neurons)