import logging
import sys

sys.path.append("./")

import os
import pandas as pd
import numpy as np

try:
    from allensdk.core.cell_types_cache import CellTypesCache
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        'You need to install the allen sdk package to use AllenMorphology:  "pip install allensdk"'
    )

from morphapi.paths_manager import Paths
from morphapi.utils.data_io import connected_to_internet
from morphapi.morphology.morphology import Neuron

logger = logging.getLogger(__name__)


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
            self.ctc.get_cells(require_reconstruction=True)
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
                self.ctc.get_reconstruction(neuron_id, file_name=neuron_file)
            except Exception as exc:
                logger.error(
                    "Could not fetch the neuron %s for the following reason: %s",
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
