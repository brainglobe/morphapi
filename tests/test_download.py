from morphapi.api.mouselight import MouseLightAPI
from morphapi.api.neuromorphorg import NeuroMorpOrgAPI


def test_neuromorpho_download():
    api = NeuroMorpOrgAPI()
    metadata, _ = api.get_neurons_metadata(
        size=2,  # Can get the metadata for up to 500 neurons at the time
        species="mouse",
        cell_type="pyramidal",
        brain_region="neocortex",
    )

    if len(metadata) != 2:
        raise ValueError("Incorrect metadata length")

    neurons = api.download_neurons(metadata)

    if len(neurons) != len(metadata):
        raise ValueError

    neurons = [neuron.create_mesh()[1] for neuron in neurons]


def test_mouselight_download():
    mlapi = MouseLightAPI()

    neurons_metadata = mlapi.fetch_neurons_metadata(
        filterby="soma", filter_regions=["MOs"]
    )

    neurons = mlapi.download_neurons(neurons_metadata[0])

    neurons = [neuron.create_mesh()[1] for neuron in neurons]


def test_allen_morphology_download():
    # TODO
    pass
