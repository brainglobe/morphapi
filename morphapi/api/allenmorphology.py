import sys

sys.path.append("./")

import os
import pandas as pd
import numpy as np
from tqdm import tqdm

from allensdk.core.cell_types_cache import CellTypesCache
from allensdk.api.queries.cell_types_api import CellTypesApi

from morphapi.paths_manager import Paths
from morphapi.utils.data_io import connected_to_internet
from morphapi.morphology.morphology import Neuron


class AllenMorphology(Paths):
    """ Handles the download of neuronal morphology data from the Allen database. """

    def __init__(self, *args, **kwargs):
        """
            Initialise API interaction and fetch metadata of neurons in the Allen Database. 
        """
        if not connected_to_internet():
            raise ConnectionError(
                "You will need to be connected to the internet to use the AllenMorphology class to download neurons"
            )

        Paths.__init__(self, *args, **kwargs)

        # Create a Cache for the Cell Types Cache API
        self.ctc = CellTypesCache(
            manifest_file=os.path.join(
                self.allen_morphology_cache, "manifest.json"
            )
        )

        # Get a list of cell metadata for neurons with reconstructions, download if necessary
        self.neurons = pd.DataFrame(
            self.ctc.get_cells(
                species=[CellTypesApi.MOUSE], require_reconstruction=True
            )
        )
        self.n_neurons = len(self.neurons)

        if not self.n_neurons:
            raise ValueError(
                "Something went wrong and couldn't get neurons metadata from Allen"
            )

        self.downloaded_neurons = self.get_downloaded_neurons()

    def get_downloaded_neurons(self):
        """ 
            Get's the path to files of downloaded neurons
        """
        return [
            os.path.join(self.allen_morphology_cache, f)
            for f in os.listdir(self.allen_morphology_cache)
            if ".swc" in f
        ]

    def download_neurons(self, ids, **kwargs):
        """
            Download neurons and return neuron reconstructions (instances
            of Neuron class)

        :param ids: list of integers with neurons IDs

        """
        if isinstance(ids, np.ndarray):
            ids = list(ids)
        if not isinstance(ids, (list)):
            ids = [ids]

        neurons = []
        print("Downloading neurons")
        for neuron_id in tqdm(ids):
            neuron_file = os.path.join(
                self.allen_morphology_cache, "{}.swc".format(neuron_id)
            )

            # Download file
            self.ctc.get_reconstruction(neuron_id, file_name=neuron_file)

            # Reconstruct neuron
            neurons.append(
                Neuron(neuron_file, neuron_name=str(neuron_id), **kwargs)
            )

        return neurons
