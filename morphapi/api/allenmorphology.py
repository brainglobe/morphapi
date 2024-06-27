import json
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from morphapi.morphology.morphology import Neuron
from morphapi.paths_manager import Paths
from morphapi.utils.data_io import connected_to_internet

logger = logging.getLogger(__name__)

columns_of_interest = {
    "cell_reporter_status": "reporter_status",
    "cell_soma_location": "cell_soma_location",
    "donor__species": "species",
    "specimen__id": "id",
    "specimen__name": "name",
    "structure__layer": "structure_layer_name",
    "structure__id": "structure_area_id",
    "structure_parent__acronym": "structure_area_abbrev",
    "line_name": "transgenic_line",
    "tag__dendrite_type": "dendrite_type",
    "tag__apical": "apical",
    "nr__reconstruction_type": "reconstruction_type",
    "donor__disease_state": "disease_state",
    "donor__id": "donor_id",
    "specimen__hemisphere": "structure_hemisphere",
    "csl__normalized_depth": "normalized_depth",
}


class AllenMorphology(Paths):
    """Handles the download of neuronal morphology data from the
    Allen database."""

    def __init__(self, *args, **kwargs):
        """
        Initialise API interaction and fetch metadata of neurons in the
        Allen Database.
        """
        if not connected_to_internet():
            raise ConnectionError(
                "You will need to be connected to the internet to use the "
                "AllenMorphology class to download neurons"
            )

        Paths.__init__(self, *args, **kwargs)

        # Get a list of cell metadata for neurons with reconstructions,
        # download if necessary
        self.neurons = self.get_cells(require_reconstruction=True)
        self.n_neurons = len(self.neurons)

        if not self.n_neurons:
            raise ValueError(
                "Something went wrong and couldn't get neurons metadata "
                "from Allen"
            )

        self.downloaded_neurons = self.get_downloaded_neurons()

    def get_cells(self, require_reconstruction: bool = True) -> pd.DataFrame:
        """
        Download the metadata for all neurons in the Allen database and save
        it to a cells_api.json file.
        """
        cells_path = Path(
            os.path.join(self.allen_morphology_cache, "cells.json")
        )

        if not cells_path.exists():
            cells = self.fetch_all_cell_metadata(cells_path)
        else:
            cells = self.check_cell_metadata(cells_path)

        cells["cell_soma_location"] = cells[
            ["csl__x", "csl__y", "csl__z"]
        ].apply(list, axis=1)
        cells = cells[columns_of_interest.keys()].rename(
            columns=columns_of_interest
        )

        if require_reconstruction:
            cells.dropna(subset=["reconstruction_type"], inplace=True)
            cells.reset_index(inplace=True, drop=True)

        return cells

    def fetch_all_cell_metadata(self, cells_path) -> pd.DataFrame:
        """
        Fetches the metadata for all neurons in the Allen database and saves
        it to a json file.

        :param cells_path: Path to save the metadata to
        """
        query = "http://api.brain-map.org/api/v2/data/query.json?criteria=model::ApiCellTypesSpecimenDetail,rma::options[num_rows$eqall]"

        try:
            r = requests.get(query)
            with open(cells_path, "w") as f:
                json.dump(r.json()["msg"], f, indent=4)
        except requests.exceptions.RequestException as e:
            logger.error(
                "Could not fetch the neuron metadata for the following "
                "reason: %s",
                str(e),
            )
            raise e

        return pd.read_json(cells_path)

    def check_cell_metadata(self, cells_path) -> pd.DataFrame:
        """
        Check if the metadata file is up-to-date and return the metadata
        as a pandas DataFrame.

        :param cells_path: Path to the metadata file
        """
        # Query for all cell types but return no rows (check for total number)
        query = "http://api.brain-map.org/api/v2/data/query.json?criteria=model::ApiCellTypesSpecimenDetail,rma::options[num_rows$eq0]"

        cells = pd.read_json(cells_path)
        try:
            r = requests.get(query)
        except requests.exceptions.RequestException as e:
            logger.error(
                "Could not check for metadata validity for the following "
                "reason: %s",
                str(e),
            )
            return cells

        n_cells = r.json()["total_rows"]

        if n_cells != len(cells):
            logger.info("Updating neuron metadata")
            cells = self.fetch_all_cell_metadata(cells_path)

        return cells

    def get_downloaded_neurons(self):
        """
        Gets the path to files of downloaded neurons
        """
        return [
            os.path.join(self.allen_morphology_cache, f)
            for f in os.listdir(self.allen_morphology_cache)
            if ".swc" in f
        ]

    def build_filepath(self, neuron_id):
        """
        Build a filepath from neuron's metadata.
        """
        return os.path.join(
            self.allen_morphology_cache, "{}.swc".format(neuron_id)
        )

    def download_neurons(self, ids, load_neurons=True, **kwargs):
        """
            Download neurons and return neuron reconstructions (instances
            of Neuron class)

        :param ids: list of integers with neurons IDs

        """
        if isinstance(ids, np.ndarray):
            ids = ids.tolist()
        if not isinstance(ids, (list)):
            ids = [ids]

        neurons = []
        for neuron_id in ids:
            neuron_file = self.build_filepath(neuron_id)
            load_current_neuron = load_neurons
            logger.debug(
                "Downloading neuron '%s' to %s", neuron_id, neuron_file
            )

            # Download file
            try:
                self.get_reconstruction(neuron_id, file_name=neuron_file)
            except Exception as exc:
                logger.error(
                    "Could not fetch the neuron %s "
                    "for the following reason: %s",
                    neuron_id,
                    str(exc),
                )
                load_current_neuron = False

            # Reconstruct neuron
            neurons.append(
                Neuron(
                    neuron_file,
                    neuron_name=str(neuron_id),
                    load_file=load_current_neuron,
                    **kwargs,
                )
            )

        return neurons

    def get_reconstruction(self, neuron_id: int, file_name: str):
        """
        Download a neuron's reconstruction from the Allen database.

        :param neuron_id: int, neuron ID
        :param file_name: str, path to save the neuron's reconstruction to
        """
        query_for_file_path = f"http://api.brain-map.org/api/v2/data/query.json?criteria=model::NeuronReconstruction,rma::criteria,[specimen_id$eq{neuron_id}],rma::include,well_known_files"

        r = requests.get(query_for_file_path)
        file_paths = r.json()["msg"][0]["well_known_files"]
        file_path = None
        for file in file_paths:
            if ".png" not in file["path"] and "marker" not in file["path"]:
                file_path = file["download_link"]
                break

        if not file_path:
            raise ValueError(
                f"Could not find a reconstruction file for neuron {neuron_id}"
            )

        query_file = f"http://api.brain-map.org{file_path}"
        r = requests.get(query_file)
        with open(file_name, "wb") as f:
            f.write(r.content)
