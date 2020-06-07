from vtkplotter import Plotter

from morphapi.api.mouselight import MouseLightAPI


# ---------------------------- Downloading neurons --------------------------- #
mlapi = MouseLightAPI()

# Fetch metadata for neurons with some in the secondary motor cortex
neurons_metadata = mlapi.fetch_neurons_metadata(
    filterby="soma", filter_regions=["MOs"]
)

neurons = mlapi.download_neurons(
    neurons_metadata[0]
)  # downloading only one neuron to speed things up

# ------------------------------- Visualisation ------------------------------ #
print("creating meshes")
neurons = [neuron.create_mesh()[1] for neuron in neurons]

print("visualizing")
vp = Plotter(shape=(1, len(neurons)), axes=1)

vp.show(neurons)
