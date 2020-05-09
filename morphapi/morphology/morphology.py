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

component = namedtuple("component", "x y z coords radius component")

class Neuron:
    _neurite_types = {'basal_dendrites':nm.core.types.NeuriteType.basal_dendrite, 
                        'apical_dendrites':nm.core.types.NeuriteType.apical_dendrite, 
                        'axon':nm.core.types.NeuriteType.axon}

    _ntypes = nm.core.types.NEURITES

    def __init__(self, swc_file=None, json_file=None):
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

        if self.data_file is not None:
            self.load_from_file()


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


    def load_from_file(self):
        if self.data_file_type is None:
            return
        elif self.data_file_type == 'json':
            raise NotImplementedError
        else:
            self.load_from_swc()

    def load_from_swc(self):
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


    def create_mesh(self, fixed_neurite_radius=False, **kwargs):
        if self.points is None:
            print('No data loaded, returning')
            return

        # Parse kwargs
        soma_color, apical_dendrites_color, basal_dendrites_color, \
                    axon_color, whole_neuron_color, kwargs = \
                                        self._parse_mesh_kwargs(**kwargs)

        if fixed_neurite_radius is None: fixed_neurite_radius = False
        if fixed_neurite_radius:
            if not isinstance(fixed_neurite_radius, (int, float)) or not fixed_neurite_radius > 0:
                raise ValueError(f'Invalid value for parameter fixed_neurite_radius, should be a float > 0')

        # Create soma actor
        neurites = {}
        soma = Sphere(pos=self.points['soma'].coords, r=self.points['soma'].radius, c=soma_color)
        neurites['soma'] = [soma.clone().c(soma_color)]

        # Create neurites actors
        for ntype in self._neurite_types:
            actors = []
            for neurite in self.points[ntype]:
                # Get tree segments
                section_segment_list = [(section, segment)
                                                for section in iter_sections(neurite.component)
                                                for segment in iter_segments(section)]
                segs = [(seg[0][COLS.XYZ], seg[1][COLS.XYZ]) for _, seg in section_segment_list]

                # Get segments radius
                if fixed_neurite_radius:
                    if not isinstance(fixed_neurite_radius, (float , int)): 
                        raise ValueError(f"When passsing fixed_neurite_radius it should be a number not: {fixed_neurite_radius.__type__}")
                    radiuses = [self.points['soma'].radius * fixed_neurite_radius 
                                            for i in np.arange(len(segs))]
                else:
                    radiuses = _get_linewidth(neurite.component, diameter_scale=1, linewidth=1)
                    if not isinstance(radiuses, (tuple, list)): 
                        radiuses = [radiuses for i in np.arange(len(segs))]

                tubes = []
                for seg, rad in zip(segs, radiuses):
                    tubes.append(Tube(seg, rad))
                actors.append(merge([t.scale(1.05) for t in tubes]))
            neurites[ntype] = actors

        # Merge actors to get the entire neuron
        actors = [act.clone() for actors in neurites.values() for act in actors] + [soma.clone()]
        whole_neuron = merge(actors).clean().smoothMLS2D(f=0.1).c(whole_neuron_color)

        # Color actors
        [act.c(basal_dendrites_color) for act in neurites['basal_dendrites']]
        [act.c(apical_dendrites_color) for act in neurites['apical_dendrites']]
        [act.c(axon_color) for act in neurites['axon']]

        return neurites, whole_neuron
