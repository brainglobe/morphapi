import os

from vedo import write, load, Mesh, merge

from morphapi.paths_manager import Paths
from morphapi.utils.data_io import save_yaml, load_yaml


class NeuronCache(Paths):
    cache_filenames_parts = [
        "_soma",
        "_axon",
        "_apical_dendrites",
        "_basal_dendrites",
        "whole_neuron",
    ]

    def __init__(self, **kwargs):
        """
            Initialise API interaction and fetch metadata of neurons in the Allen Database. 
        """
        super().__init__(**kwargs)  # path to data caches

    def get_cache_filenames(self, neuron_name):
        fld = os.path.join(self.meshes_cache, str(neuron_name))
        if not os.path.isdir(fld):
            os.mkdir(fld)
        return [
            os.path.join(fld, str(neuron_name) + part + ".obj")
            for part in self.cache_filenames_parts
        ]

    def get_cache_params_filename(self, neuron_name):
        fld = os.path.join(self.meshes_cache, str(neuron_name))
        if not os.path.isdir(fld):
            os.mkdir(fld)

        return os.path.join(fld, str(neuron_name) + "_params.yml")

    def _check_neuron_mesh_cached(self, neuron_name):
        # If any of the files doesn't exist, the neuron wasn't cached
        for fn in self.get_cache_filenames(neuron_name):
            if not os.path.isfile(fn):
                return False
        return True

    def load_cached_neuron(self, neuron_name, _params):
        if not self._check_neuron_mesh_cached(neuron_name):
            return None

        # Check if params are the same as when cached
        cached_params = load_yaml(self.get_cache_params_filename(neuron_name))
        if len(cached_params) != len(_params):
            changed = cached_params.values()
        else:
            changed = {v for k, v in _params.items() if v != cached_params[k]}
        if changed:
            return None

        # Load neurites
        neurites = [
            "soma",
            "axon",
            "apical_dendrites",
            "basal_dendrites",
            "whole_neuron",
        ]
        loaded = {
            nn: load(fp)
            for nn, fp in zip(neurites, self.get_cache_filenames(neuron_name))
        }

        for nn, act in loaded.items():
            if len(act.points()) == 0:
                loaded[nn] = None

        return loaded

    def write_neuron_to_cache(self, neuron_name, neuron, _params):
        # Write params to file
        save_yaml(self.get_cache_params_filename(neuron_name), _params)

        # Write neurons to file
        file_names = self.get_cache_filenames(neuron_name)

        if isinstance(neuron, Mesh):
            write(neuron, [f for f in file_names if f.endswith("soma.obj")][0])
        else:
            if not isinstance(neuron, dict):
                raise ValueError(
                    f"Invalid neuron argument passed while caching: {neuron}"
                )
            for key, actor in neuron.items():
                if key == "whole_neuron":
                    fname = [f for f in file_names if f.endswith(f"{key}.obj")]
                    write(actor, fname[0])
                else:
                    # Get a single actor for each neuron component.
                    # If there's no data for the component create an empty actor
                    if not isinstance(actor, Mesh):
                        if isinstance(actor, (list, tuple)):
                            if len(actor) == 1:
                                actor = actor[0]
                            elif not actor or actor is None:
                                actor = Mesh()
                            else:
                                try:
                                    actor = merge(actor)
                                except:
                                    raise ValueError(
                                        f"{key} actor should be a mesh or a list of 1 mesh not {actor}"
                                    )

                    if actor is None:
                        actor = Mesh()

                    # Save to file
                    fname = [f for f in file_names if f.endswith(f"{key}.obj")]
                    if fname:
                        write(actor, fname[0])
                    else:
                        raise ValueError(
                            f"No filename found for {key}. Filenames {file_names}"
                        )
