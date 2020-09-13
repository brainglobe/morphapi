from vedo import Plotter

from morphapi.api.mouselight import MouseLightAPI


# ---------------------------- Downloading neurons --------------------------- #
mlapi = MouseLightAPI()

# Fetch metadata for neurons with soma in the secondary motor cortex
neurons_metadata = mlapi.fetch_neurons_metadata(
    filterby="soma", filter_regions=["MOs"]
)

# Then we can download the files and save them as a .json file
neurons = mlapi.download_neurons(neurons_metadata[0])


"""
    mlapi.download_neurons returns a list of instances of the class Neuron
    from morphapi.morphology.morphology.
"""


# ------------------------------- Visualisation ------------------------------ #
print("creating meshes")
neurons = [neuron.create_mesh()[1] for neuron in neurons]

print("visualizing")
vp = Plotter(shape=(1, len(neurons)), axes=1)

vp.show(neurons)
