from pathlib import Path

from morphapi.api.allenmorphology import AllenMorphology
from morphapi.api.mouselight import MouseLightAPI
from morphapi.api.neuromorphorg import NeuroMorpOrgAPI


def test_neuromorpho_download(tmpdir):
    api = NeuroMorpOrgAPI(base_dir=tmpdir)
    cache_path = Path(api.neuromorphorg_cache)

    metadata, _ = api.get_neurons_metadata(
        size=2,  # Can get the metadata for up to 500 neurons at the time
        species="mouse",
        cell_type="pyramidal",
        brain_region="neocortex",
    )

    if len(metadata) != 2:
        raise ValueError("Incorrect metadata length")

    assert len(list(cache_path.iterdir())) == 0
    neurons = api.download_neurons(metadata)

    assert len(neurons) == len(metadata)
    assert len(list(cache_path.iterdir())) == 2

    neurons = [neuron.create_mesh()[1] for neuron in neurons]

    # Test no load
    assert api.download_neurons(metadata, load_neurons=False)[0].points is None
    assert len(list(cache_path.iterdir())) == 2

    # Test using neuron names
    assert (
        api.download_neurons(
            metadata, load_neurons=False, use_neuron_names=True
        )[0].points
        is None
    )
    assert len(list(cache_path.iterdir())) == 4

    cache_files = list(cache_path.iterdir())
    assert sorted([i.name for i in cache_files]) == [
        "10075.swc",
        "10076.swc",
        "C1q-Cell7-40x.swc",
        "Ctrl-Cell3-40x.swc",
    ]

    # Test failure
    metadata[0]["neuron_id"] = "BAD ID"
    metadata[0]["neuron_name"] = "BAD NAME"
    neurons = api.download_neurons([metadata[0]])

    assert neurons[0].data_file.name == "BAD ID.swc"
    assert neurons[0].points is None

    # Test get_fields_values
    assert len(api.get_fields_values("strain")) > 1000


def test_mouselight_download(tmpdir):
    mlapi = MouseLightAPI(base_dir=tmpdir)

    neurons_metadata = mlapi.fetch_neurons_metadata(
        filterby="soma", filter_regions=["MOs"]
    )
    neurons_metadata = sorted(neurons_metadata, key=lambda x: x["idString"])

    neurons = mlapi.download_neurons(neurons_metadata[0])

    neurons = [neuron.create_mesh()[1] for neuron in neurons]

    # Test no load
    assert (
        mlapi.download_neurons(neurons_metadata[0], load_neurons=False)[
            0
        ].points
        is None
    )

    # Test failure
    neurons_metadata[0]["idString"] = "BAD ID"
    neurons = mlapi.download_neurons(neurons_metadata[0])

    assert neurons[0].data_file.name == "BAD ID.swc"
    assert neurons[0].points is None

    # Test filter without atlas
    filtered_neurons_metadata = mlapi.filter_neurons_metadata(
        neurons_metadata, filterby="soma", filter_regions=["MOs6b"]
    )
    assert all(
        [i["brainArea_acronym"] == "MOs6b" for i in filtered_neurons_metadata]
    )

    # Test filter with atlas
    atlas = mlapi.fetch_default_atlas()

    filtered_neurons_metadata_atlas = mlapi.filter_neurons_metadata(
        neurons_metadata,
        filterby="soma",
        filter_regions=["MOs6b"],
        atlas=atlas,
    )
    assert all(
        [
            i["brainArea_acronym"] == "MOs6b"
            for i in filtered_neurons_metadata_atlas
        ]
    )
    assert filtered_neurons_metadata == filtered_neurons_metadata_atlas


def test_allen_morphology_download(tmpdir):
    am = AllenMorphology(base_dir=tmpdir)

    # Select some mouse neurons in the primary visual cortex
    neurons_df = am.neurons.loc[
        (am.neurons.species == "Mus musculus")
        & (am.neurons.structure_area_abbrev == "VISp")
    ].loc[[2, 120, 505]]

    # Download some neurons
    neurons = am.download_neurons(neurons_df["id"].values)

    neurons = [neuron.create_mesh()[1] for neuron in neurons]

    # Test no load
    assert all(
        i.points is None
        for i in am.download_neurons(
            neurons_df["id"].values, load_neurons=False
        )
    )

    # Test failure
    neurons_df.loc[2, "id"] = "BAD ID"
    neurons = am.download_neurons(neurons_df["id"].values)

    assert neurons[0].data_file.name == "BAD ID.swc"
    assert neurons[0].points is None
