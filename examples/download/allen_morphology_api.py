from morphapi.api.allenmorphology import AllenMorphology
from vedo import Plotter

am = AllenMorphology()

print(am.neurons.head())

# Select some mouse neurons in the primary visual cortex
neurons = am.neurons.loc[
    (am.neurons.species == "Mus musculus")
    & (am.neurons.structure_area_abbrev == "VISp")
]

# Download some neurons
neurons = am.download_neurons(neurons[:5].id.values)

# ------------------------------- Visualisation ------------------------------ #
print("creating meshes")
neurons = [neuron.create_mesh()[1] for neuron in neurons]

print("visualizing")
vp = Plotter(axes=1)

vp.show(neurons)
