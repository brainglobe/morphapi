import sys
from pathlib import Path

"""
    Class to create and store paths to a number of folders uesed to save/load data
"""


# Default paths for Data Folders (store stuff like object meshes, neurons morphology data etc)
default_paths = dict(
    # APIs caches
    allen_morphology_cache="Data/allen_morphology_cache",
    mouselight_cache="Data/mouselight_cache",
    neuromorphorg_cache="Data/neuromorphorg_cache",
    meshes_cache="Data/meshes_cache",
    # Other
    mouse_connectivity_cache="Data/mouse_connectivity_cache",
    mpin_morphology="Data/mpin_morphology"
)


class Paths:

    def __init__(self, base_dir=None, **kwargs):
        """
        Parses a YAML file to get data folders paths. Stores paths to a number of folders used throughtout morphapi. 
        
        :param base_dir: str with path to directory to use to save data. If none the user's base directiry is used. 
        :param kwargs: use the name of a folder as key and a path as argument to specify the path of individual subfolders
        """
        # Get and make base directory

        if base_dir is None:
            self.base_dir = Path.home() / ".morphapi"
        else:
            self.base_dir = base_dir

        self.base_dir.mkdir(exist_ok=True)

        for fld_name, folder in default_paths.items():
            # Check if user provided a path for this folder, otherwise use default

            path = self.base_dir / kwargs.pop(fld_name,
                                              folder)

            # Create folder if it doesn't exist:
            path.mkdir(parents=True, exist_ok=True)
            self.__setattr__(fld_name, str(path))
