import pandas as pd
from pathlib import Path
import zipfile
import shutil
from rich.progress import track

from morphapi.paths_manager import Paths
from morphapi.utils.data_io import connected_to_internet
from morphapi.morphology.morphology import Neuron
from bg_space import SpaceConvention
from bg_atlasapi.utils import retrieve_over_http
from bg_atlasapi import BrainGlobeAtlas


def soma_coords_from_file(file_path):
    """Compile dictionary with traced cells origins.
    """
    # Read first line after comment for soma ID:
    line_start = "#"
    with open(file_path, "r") as file:
        while line_start == "#":
            line = file.readline()
            line_start = line[0]

    return [float(p) for p in line.split(" ")[2:-2]]


def fix_mpin_swgfile(file_path, fixed_file_path=None):
    """Fix neurons downloaded from the MPIN website by correcting node
    id and changing the orientation to be standard BrainGlobe.
    """
    if fixed_file_path is None:
        fixed_file_path = file_path

    # Fixed descriptors of the dataset space:
    ORIGIN = "rai"
    SHAPE = [597, 974, 359]
    TARGET_SPACE = "asl"
    NEW_SOMA_SIZE = 7

    bgspace = SpaceConvention(origin=ORIGIN, shape=SHAPE)

    df = pd.read_csv(file_path, sep=" ", header=None, comment="#")

    # In this dataset, soma node is always the first, and
    # other nodes have unspecified identity which we'll set to axon.
    # Hopefully it will be fixed in next iterations of the database.
    df.iloc[0, 1] = 1
    df.iloc[1:, 1] = 2

    # Map points to BrainGlobe orientation:
    df.iloc[:, 2:-2] = bgspace.map_points_to(
        TARGET_SPACE, df.iloc[:, 2:-2].values
    )
    df.iloc[0, -2] = NEW_SOMA_SIZE
    df.to_csv(fixed_file_path, sep=" ", header=None, index=False)


class MpinMorphologyAPI(Paths):
    """Handles the download of neuronal morphology data from the MPIN database.
    """

    def __init__(self, *args, **kwargs):
        Paths.__init__(self, *args, **kwargs)

        self.data_path = Path(self.mpin_morphology) / "fixed"

        if not self.data_path.exists():
            self.download_dataset()

        self._neurons_df = None

    @property
    def neurons_df(self):
        """Table with all neurons positions and soma regions.
        """
        if self._neurons_df is None:
            # Generate table with soma position to query by region:
            atlas = BrainGlobeAtlas("mpin_zfish_1um", print_authors=False)

            neurons_dict = dict()
            for f in self.data_path.glob("*.swc"):
                coords = soma_coords_from_file(f)  # compute coordinates

                # Calculate anatomical structure the neuron belongs to:
                try:
                    region = atlas.structure_from_coords(coords)
                except IndexError:
                    region = 0

                neurons_dict[f.stem] = dict(
                    filename=f.name,
                    pos_ap=coords[0],
                    pos_si=coords[1],
                    pos_lr=coords[2],
                    region=region,
                )

            self._neurons_df = pd.DataFrame(neurons_dict).T

        return self._neurons_df

    def get_neurons_by_structure(self, *region):
        atlas = BrainGlobeAtlas("mpin_zfish_1um", print_authors=False)
        IDs = atlas._get_from_structure(region, "id")
        return list(
            self.neurons_df.loc[self.neurons_df.region.isin(IDs)].index
        )

    def load_neurons(self, neuron_id, **kwargs):
        """
            Load individual neurons given their IDs
        """
        if not isinstance(neuron_id, list):
            neuron_id = [neuron_id]

        to_return = []
        for nid in neuron_id:
            filepath = str(
                Path(self.mpin_morphology)
                / "fixed"
                / self.neurons_df.loc[nid].filename
            )
            to_return.append(
                Neuron(filepath, neuron_name="mpin_" + str(nid), **kwargs,)
            )

        return to_return

    def download_dataset(self):
        """Dowload dataset from Kunst et al 2019.

        """
        if not connected_to_internet():
            raise ValueError(
                "An internet connection is required to download the dataset"
            )
        SOURCE_DATA_DIR = "MPIN-Atlas__Kunst_et_al__neurons_all"

        REMOTE_URL = "https://fishatlas.neuro.mpg.de/neurons/download/download_all_neurons_aligned"

        # # Download folder with all data:
        download_zip_path = Path(self.mpin_morphology) / "data.zip"
        retrieve_over_http(REMOTE_URL, download_zip_path)

        # Uncompress and delete compressed:
        with zipfile.ZipFile(download_zip_path, "r") as zip_ref:
            zip_ref.extractall(download_zip_path.parent)
        download_zip_path.unlink()

        # Fix extracted files:
        extracted_data_path = (
            Path(self.mpin_morphology) / SOURCE_DATA_DIR / "Original"
        )
        self.data_path.mkdir(exist_ok=True)

        for f in track(
            list(extracted_data_path.glob("*.swc")),
            description="Fixing swc files",
        ):
            fix_mpin_swgfile(f, self.data_path / f.name)

        shutil.rmtree(extracted_data_path.parent)

        # # 2/1900 neurons still have a little bug, hopefully fixed in the future
        # try:
        #     return Neuron(data_file=fixed_file_path)
        # except:  # Ideally in the next iteration this except won't be necessary
        #     print(f"Unfixable problem while opening {file_path.name}")
        #     return
