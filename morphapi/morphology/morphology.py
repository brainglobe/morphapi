import os
from collections import namedtuple
import numpy as np

from vtkplotter.shapes import Sphere, Tube
from vtkplotter import merge, write
from vtkplotter.colors import colorMap

import neurom as nm
from neurom.core import iter_neurites, iter_segments, iter_sections
from neurom.core.dataformat import COLS
from neurom.morphmath import segment_radius
from neurom.view.view import _get_linewidth

from morphapi.morphology.cache import NeuronCache
from morphapi.utils.data_io import get_file_name

component = namedtuple("component", "x y z coords radius component")

class Neuron(NeuronCache):
    _neurite_types = {'basal_dendrites':nm.core.types.NeuriteType.basal_dendrite, 
                        'apical_dendrites':nm.core.types.NeuriteType.apical_dendrite, 
                        'axon':nm.core.types.NeuriteType.axon}

    _ntypes = nm.core.types.NEURITES

    def __init__(self, swc_file=None, json_file=None, neuron_name=None, invert_dims=False):
        NeuronCache.__init__(self) # path to data caches

        self.invert_dims = invert_dims

        # Parse agruments
        if swc_file is not None and json_file is not None:
            raise ValueError('Pass eithr swc or json file, not both')
        elif swc_file is not None:
            if not os.path.exists(swc_file) or not swc_file.endswith('.swc'):
                raise ValueError(f'Invalid swc file: {swc_file}')
            self.data_file = swc_file
            self.data_file_type = 'swc'
        elif json_file is not None:
            if not os.path.exists(json_file) or not json_file.endswith('.json'):
                raise ValueError(f'Invalid json file: {json_file}')
            self.data_file = json_file
            self.data_file_type = 'json'
        else:
            self.data_file = None
            self.data_file_type = None
            self.morphology = None
            self.points = None

        self.neuron_name = neuron_name

        if self.data_file is not None:
            self.load_from_file()

    def load_from_file(self):
        if self.data_file_type is None:
            return
        elif self.data_file_type == 'json':
            raise NotImplementedError
        else:
            self.load_from_swc()

    def load_from_swc(self):
        if self.neuron_name is None:
            self.neuron_name = get_file_name(self.data_file)

        nrn = nm.load_neuron(self.data_file)

        # Get position and radius of some
        soma_pos = nrn.soma.points[0, :3]
        soma_radius = nrn.soma.points[0, -1]

        # Get the rest of the data and store it
        self.morphology = nrn
        self.points = dict(
            soma=component(soma_pos[0], soma_pos[1], soma_pos[2], soma_pos, soma_radius, nrn.soma),
            )

        for ntype, nclass in self._neurite_types.items():
            self.points[ntype] = [component(n.points[:, 0], n.points[:, 1], n.points[:, 2], n.points[:, :3], n.points[:, -1], n) 
                                        for n in nrn.neurites if n.type == nclass]

    def _parse_mesh_kwargs(self, **kwargs):
        # To give the entire neuron the same color
        neuron_color = kwargs.pop('neuron_color', None)

        # To give the entire neuron a color based on a cmap 
        neuron_number = kwargs.pop('neuron_number', None)
        cmap_lims = kwargs.pop('cmap_lims', (-1, 1))
        cmap = kwargs.pop('cmap', None)

        # To color each component individually
        soma_color = kwargs.pop('soma_color', 'salmon')
        apical_dendrites_color = kwargs.pop('apical_dendrites_color', 'salmon')
        basal_dendrites_color = kwargs.pop('basal_dendrites_color', apical_dendrites_color) 
        axon_color = kwargs.pop('axon_color', 'salmon')
        whole_neuron_color = kwargs.pop('whole_neuron_color', None)

        # Get each components color from args
        if neuron_color is not None:  # uniform color
            soma_color = apical_dendrites_color = basal_dendrites_color = axon_color = neuron_color
        elif cmap is not None:  # color according to cmap
            if neuron_number is None:
                neuron_number = 0
            
            soma_color = colorMap(neuron_number, name=cmap, vmin=cmap_lims[0], vmax=cmap_lims[1])
            apical_dendrites_color = basal_dendrites_color = axon_color = soma_color

        else: # Use color specified for each component
            pass

        if whole_neuron_color is None: whole_neuron_color = soma_color
        return soma_color, apical_dendrites_color, basal_dendrites_color, axon_color, whole_neuron_color, kwargs



    def create_mesh(self, neurite_radius=2, **kwargs):
        if self.points is None:
            print('No data loaded, returning')
            return

        # Parse kwargs
        soma_color, apical_dendrites_color, basal_dendrites_color, \
                    axon_color, whole_neuron_color, kwargs = \
                                        self._parse_mesh_kwargs(**kwargs)

        if not isinstance(neurite_radius, (int, float)) or not neurite_radius > 0:
            raise ValueError(f'Invalid value for parameter neurite_radius, should be a float > 0')

        # prepare params dict for caching
        _params = dict(
            neurite_radius = neurite_radius,
        )

        # Check if cached files already exist
        neurites = self.load_cached_neuron(self.neuron_name, _params)
        if neurites is not None:
            whole_neuron = neurites.pop('whole_neuron')
            neurites['soma'].c(soma_color)
        else:
            # Create soma actor
            neurites = {}
            if not self.invert_dims:
                coords = self.points['soma'].coords
            else:
                coords = self.points['soma'].coords
                z, y, x = coords[0], coords[1], coords[2]
                coords = np.hstack([x, y, z]).T
            soma = Sphere(pos=coords, r=self.points['soma'].radius * neurite_radius * 2,
                                        c=soma_color).computeNormals()
            neurites['soma'] = soma.clone().c(soma_color)

            # Create neurites actors
            for ntype in self._neurite_types:
                actors = []
                for neurite in self.points[ntype]:
                    for section in iter_sections(neurite.component):
                        for child in section.children:
                            if not child.children:
                                coords = child.points[:, COLS.XYZ]
                                if self.invert_dims:
                                    z, y, x = coords[:, 0], coords[:, 1], coords[:, 2]
                                    coords = np.hstack([x, y, z]).T
                                actors.append(Tube(coords, r=neurite_radius))                        
                            else:
                                for grandchild in child.children:
                                    coords = grandchild.points[:, COLS.XYZ]
                                    if self.invert_dims:
                                        z, y, x = coords[:, 0], coords[:, 1], coords[:, 2]
                                        coords = np.vstack([x, y, z]).T
                                    actors.append(Tube(coords, r=neurite_radius))     

                if actors:
                    neurites[ntype] = merge(actors).computeNormals() # .smoothMLS2D(f=0.1)
                else:
                    neurites[ntype] = None

            # Merge actors to get the entire neuron
            actors = [act.clone() for act in neurites.values() if act is not None] 
            whole_neuron = merge(actors).clean().computeNormals()

            # Write to cache
            to_write = neurites.copy()
            to_write['whole_neuron'] = whole_neuron
            self.write_neuron_to_cache(self.neuron_name, to_write, _params)

        # Color actors
        colors = [basal_dendrites_color, apical_dendrites_color, axon_color]
        for n, key in enumerate(['basal_dendrites', 'apical_dendrites', 'axon']):
            if neurites[key] is not None:
                neurites[key] = neurites[key].c(colors[n])
        whole_neuron.c(whole_neuron_color)

        return neurites, whole_neuron
