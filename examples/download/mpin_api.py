from vedo import Plotter

from morphapi.api.mpin_celldb import MpinMorphologyAPI


api = MpinMorphologyAPI()

# ----------------------------- Download dataset ----------------------------- #
"""
    If it's the first time using this API, you'll have to download the dataset
    with all of the neurons' data.
"""
api.download_dataset()


# You can then inspect metadata about all neurons:
print(api.neurons_df.head())

# and load a few neurons
neurons = api.load_neurons(list(api.neurons_df.index[:10]))

# ------------------------------- Visualisation ------------------------------ #
print("creating meshes")
neurons = [neuron.create_mesh()[1] for neuron in neurons]

print("visualizing")
vp = Plotter(shape=(1, len(neurons)), axes=1)

vp.show(neurons)
