import pandas as pd
from pathlib import Path
import zipfile


from morphapi.paths_manager import Paths
from morphapi.utils.data_io import connected_to_internet
from morphapi.morphology.morphology import Neuron
from bg_space import SpaceConvention
from bg_atlasapi.utils import retrieve_over_http


def soma_pos_dict_from_folder(folder_path):
    """Compile dictionary with traced cells origins.
    """
    soma_location_dict = dict()
    for f in folder_path.glob("*.swc"):

        # Read first line after comment for soma ID:
        line_start = "#"
        with open(f, "r") as file:
            while line_start == "#":
                line = file.readline()
                line_start = line[0]

        soma_location_dict[f.name] = [float(p) for p in line.split(" ")[2:-2]]

    return soma_location_dict


def load_mpin_fixed_neuron(file_path, force_refix=True):
    """Fix neurons downloaded from the MPIN website by correcting node
    id and changing the orientation to be standard BrainGlobe.
    """

    # Fixed descriptors of the dataset space:
    ORIGIN = "rai"
    SHAPE = [597, 974, 359]
    bgspace = SpaceConvention(origin=ORIGIN, shape=SHAPE)

    SUFFIX = "soma_fixed"  # filename for cached fixed neurons
    fixed_file_path = file_path.parent / f"{file_path.stem}_{SUFFIX}.swc"

    if not fixed_file_path.exists() or force_refix:
        df = pd.read_csv(file_path,
                         sep=" ", header=None, comment='#')

        # In this dataset, soma node is always the first, and
        # other nodes have unspecified identity which we'll set to axon.
        # Hopefully it will be fixed in next iterations of the database.
        df.iloc[0, 1] = 1
        df.iloc[1:, 1] = 2

        # Map points to BrainGlobe orientation:
        df.iloc[:, 2:-2] = bgspace.map_points_to("asl", df.iloc[:, 2:-2])

        df.to_csv(fixed_file_path, sep=" ", header=None, index=False)

    # 2/1900 neurons still have a little bug, hopefully fixed in the future
    try:
        return Neuron(data_file=fixed_file_path)
    except:  # Ideally in the next iteration this except won't be necessary
        print(f"Unfixable problem while opening {file_path.name}")
        return


class MpinMorphology(Paths):
    """Handles the download of neuronal morphology data from the MPIN database.
    """
    SOURCE_DATA_DIR = "MPIN-Atlas__Kunst_et_al__neurons_all"
    REMOTE_URL = "https://fishatlas.neuro.mpg.de/neurons/download/download_all_neurons_aligned"

    def __init__(self, *args, **kwargs):
        Paths.__init__(self, *args, **kwargs)

        self.data_path = Path(self.mpin_morphology) / self.SOURCE_DATA_DIR

        if not self.data_path.exists():
            # Download folder with all data:
            download_zip_path = Path(self.mpin_morphology) / "data.zip"
            retrieve_over_http(self.REMOTE_URL, download_zip_path)
            # Uncompress and delete compressed;
            with zipfile.ZipFile(download_zip_path, "r") as zip_ref:
                zip_ref.extractall(download_zip_path.parent)
            download_zip_path.unlink()

        # Generate table with soma position to query by region:
        self.pos_dict = soma_pos_dict_from_folder(self.data_path / "Original")



    def get_downloaded_neurons(self):
        """
            Get's the path to files of downloaded neurons
        """
        pass

    def download_neurons(self, ids, **kwargs):
        """
            Download neurons and return neuron reconstructions (instances
            of Neuron class)

        :param ids: list of integers with neurons IDs

        """
        pass