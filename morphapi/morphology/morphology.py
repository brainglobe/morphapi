import logging
from pathlib import Path
from collections import namedtuple
import numpy as np

from vedo.shapes import Sphere, Tube
from vedo import merge
from vedo.colors import colorMap

import neurom as nm
from neurom.core.dataformat import COLS

try:
    # For NeuroM >= 3
    from neurom.core.morphology import iter_sections
except ImportError:
    # For NeuroM < 2
    try:
        from neurom.core import iter_sections
    except ImportError:
        # For NeuroM >= 2, < 3
        from neurom import iter_sections


from morphapi.morphology.cache import NeuronCache

import warnings

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)

component = namedtuple("component", "x y z coords radius component")


class Neuron(NeuronCache):
    _neurite_types = {
        "basal_dendrites": nm.core.types.NeuriteType.basal_dendrite,
        "apical_dendrites": nm.core.types.NeuriteType.apical_dendrite,
        "axon": nm.core.types.NeuriteType.axon,
    }

    _ntypes = nm.core.types.NEURITES

    def __init__(
        self,
        data_file,
        neuron_name=None,
        invert_dims=False,
        load_file=True,
        **kwargs,
    ):
        super().__init__(**kwargs)  # path to data caches

        self.invert_dims = invert_dims
        self.neuron_name = neuron_name

        self.data_file = Path(data_file)
        self.data_file_type = self.data_file.suffix[1:]

        if self.data_file_type not in ["swc", "json"]:
            raise ValueError("Invalid data file type, should be swc or jon")

        if self.neuron_name is None:
            self.neuron_name = self.data_file.name

        if load_file:
            self.load_from_file()
        else:
            self.points = None

    def load_from_file(self):
        if not self.data_file.exists():
            raise ValueError("The specified path does not exist!")

        if self.data_file_type is None:
            return
        elif self.data_file_type == "json":
            raise NotImplementedError
        else:
            self.load_from_swc()

    def repair_swc_file(self):
        """
            Fixes this: https://github.com/BlueBrain/NeuroM/issues/835
        """
        with open(self.data_file, "r") as read:
            content = read.readlines()

        clean = []
        for line in content:
            if not len(line):
                clean.append(line)
                continue

            line = line.replace("\n", "").replace("\t", " ")
            vals = line.split(" ")
            if len(vals) < 2:
                clean.append(line)
                continue

            if vals[1] != "1" and vals[-1] == "-1":
                vals[-1] = "0"
                clean.append(" ".join(vals))
            else:
                clean.append(line)

        if len(clean) != len(content):
            raise ValueError

        with open(self.data_file, "w") as write:
            for line in clean:
                write.write(f"{line}\n")

    def load_from_swc(self):
        if self.neuron_name is None:
            self.neuron_name = self.data_file.name

        self.repair_swc_file()

        nrn = nm.load_neuron(self.data_file)

        # Get position and radius of some
        soma_pos = nrn.soma.points[0, :3]
        soma_radius = nrn.soma.points[0, -1]

        # Get the rest of the data and store it
        self.morphology = nrn
        self.points = dict(
            soma=component(
                soma_pos[0],
                soma_pos[1],
                soma_pos[2],
                soma_pos,
                soma_radius,
                nrn.soma,
            ),
        )

        for ntype, nclass in self._neurite_types.items():
            self.points[ntype] = [
                component(
                    n.points[:, 0],
                    n.points[:, 1],
                    n.points[:, 2],
                    n.points[:, :3],
                    n.points[:, -1],
                    n,
                )
                for n in nrn.neurites
                if n.type == nclass
            ]

    def _parse_mesh_kwargs(self, **kwargs):
        # To give the entire neuron the same color
        neuron_color = kwargs.pop("neuron_color", None)

        # To give the entire neuron a color based on a cmap
        neuron_number = kwargs.pop("neuron_number", None)
        cmap_lims = kwargs.pop("cmap_lims", (-1, 1))
        cmap = kwargs.pop("cmap", None)

        # To color each component individually
        soma_color = kwargs.pop("soma_color", "salmon")
        apical_dendrites_color = kwargs.pop("apical_dendrites_color", "salmon")
        basal_dendrites_color = kwargs.pop(
            "basal_dendrites_color", apical_dendrites_color
        )
        axon_color = kwargs.pop("axon_color", "salmon")
        whole_neuron_color = kwargs.pop("whole_neuron_color", None)

        # Get each components color from args
        if neuron_color is not None:  # uniform color
            soma_color = (
                apical_dendrites_color
            ) = basal_dendrites_color = axon_color = neuron_color
        elif cmap is not None:  # color according to cmap
            if neuron_number is None:
                neuron_number = 0

            soma_color = colorMap(
                neuron_number, name=cmap, vmin=cmap_lims[0], vmax=cmap_lims[1]
            )
            apical_dendrites_color = (
                basal_dendrites_color
            ) = axon_color = soma_color

        else:  # Use color specified for each component
            pass

        if whole_neuron_color is None:
            whole_neuron_color = soma_color
        return (
            soma_color,
            apical_dendrites_color,
            basal_dendrites_color,
            axon_color,
            whole_neuron_color,
            kwargs,
        )

    def create_mesh(
        self, neurite_radius=2, soma_radius=4, use_cache=True, **kwargs
    ):
        if self.points is None:
            logger.warning(
                "No data loaded, you can use the 'load_from_file' method to try to load the file."
            )
            return

        # Parse kwargs
        (
            soma_color,
            apical_dendrites_color,
            basal_dendrites_color,
            axon_color,
            whole_neuron_color,
            kwargs,
        ) = self._parse_mesh_kwargs(**kwargs)

        if (
            not isinstance(neurite_radius, (int, float))
            or not neurite_radius > 0
        ):
            raise ValueError(
                f"Invalid value for parameter neurite_radius, should be a float > 0"
            )
        if not isinstance(soma_radius, (int, float)) or not soma_radius > 0:
            raise ValueError(
                f"Invalid value for parameter soma_radius, should be a float > 0"
            )
        # prepare params dict for caching
        _params = dict(neurite_radius=neurite_radius, soma_radius=soma_radius)

        # Check if cached files already exist
        if use_cache:
            neurites = self.load_cached_neuron(self.neuron_name, _params)
        else:
            neurites = None

        # Render
        if neurites is not None:
            whole_neuron = neurites.pop("whole_neuron")
            neurites["soma"].c(soma_color)
        else:
            # Create soma actor
            neurites = {}
            if not self.invert_dims:
                coords = self.points["soma"].coords
            else:
                coords = self.points["soma"].coords
                z, y, x = coords[0], coords[1], coords[2]
                coords = np.hstack([x, y, z]).T

            soma = Sphere(
                pos=coords,
                r=self.points["soma"].radius * soma_radius,
                c=soma_color,
            ).computeNormals()
            neurites["soma"] = soma.clone().c(soma_color)

            # Create neurites actors
            for ntype in self._neurite_types:
                actors = []
                for neurite in self.points[ntype]:
                    for section in iter_sections(neurite.component):
                        for child in section.children:
                            if not child.children:
                                coords = child.points[:, COLS.XYZ]
                                if self.invert_dims:
                                    z, y, x = (
                                        coords[:, 0],
                                        coords[:, 1],
                                        coords[:, 2],
                                    )
                                    coords = np.hstack([x, y, z]).T
                                actors.append(Tube(coords, r=neurite_radius))
                            else:
                                for grandchild in child.children:
                                    coords = grandchild.points[:, COLS.XYZ]
                                    if self.invert_dims:
                                        z, y, x = (
                                            coords[:, 0],
                                            coords[:, 1],
                                            coords[:, 2],
                                        )
                                        coords = np.vstack([x, y, z]).T
                                    actors.append(
                                        Tube(coords, r=neurite_radius)
                                    )

                if actors:
                    neurites[ntype] = merge(
                        actors
                    ).computeNormals()  # .smoothMLS2D(f=0.1)
                else:
                    neurites[ntype] = None

            # Merge actors to get the entire neuron
            actors = [
                act.clone() for act in neurites.values() if act is not None
            ]
            whole_neuron = merge(actors).clean().computeNormals()

            # Write to cache
            to_write = neurites.copy()
            to_write["whole_neuron"] = whole_neuron
            self.write_neuron_to_cache(self.neuron_name, to_write, _params)

        # Color actors
        colors = [basal_dendrites_color, apical_dendrites_color, axon_color]
        for n, key in enumerate(
            ["basal_dendrites", "apical_dendrites", "axon"]
        ):
            if neurites[key] is not None:
                neurites[key] = neurites[key].c(colors[n])
        whole_neuron.c(whole_neuron_color)

        return neurites, whole_neuron
