from vedo import Plotter

from morphapi.api.neuromorphorg import NeuroMorpOrgAPI


api = NeuroMorpOrgAPI()

# ---------------------------- Downloading metadata --------------------------- #
# Get metadata for pyramidal neurons from the mouse cortex.
metadata, _ = api.get_neurons_metadata(
    size=10,  # Can get the metadata for up to 500 neurons at the time
    species="mouse",
    cell_type="pyramidal",
    brain_region="neocortex",
)

# To get a list of available query fields: print(api.fields)
# To get a list of valid values for a field: print(api.get_fields_values(field))

print("Neurons metadata:")
print(metadata[0])

# ---------------------------- Download morphology --------------------------- #
neurons = api.download_neurons(metadata[5])


# ------------------------------- Visualisation ------------------------------ #
print("creating meshes")
neurons = [neuron.create_mesh()[1] for neuron in neurons]

print("visualizing")
vp = Plotter(shape=(1, len(neurons)), axes=1)

vp.show(neurons)
