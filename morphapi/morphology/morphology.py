import os
from collections import namedtuple

from vtkplotter.shapes import Sphere, Tube
from vtkplotter import merge, write

import neurom as nm
from neurom.core import iter_neurites, iter_segments, iter_sections
from neurom.core.dataformat import COLS
from neurom.morphmath import segment_radius
from neurom.view.view import _get_line_width

component = namedtuple("soma", "x y z coords radius component")

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
            self.loaded = None
            self.points = None

        if self.data_file is not None:
            self.load_from_file()


    def load_from_file(self):
        print('Loading neuron morphology data')
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
        self.loaded = nrn
        self.points = dict(
            soma=component(soma_pos[0], soma_pos[1], soma_pos[2], soma_pos, soma_radius, nrn.soma),
            )

        for ntype, nclass in self._neurite_types.items():
            self.points[ntype] = [component(n.points[:, 0], n.points[:, 1], n.points[:, 2], n.points[:, :3], n.points[:, -1], n) 
                                        for n in nrn.neurites if n.type == nclass]


    def create_mesh(self, ):
        if self.points is None:
            print('No data loaded, returning')
            return

        # Create soma actor
        soma = Sphere(pos=self.points['soma'].coords, r=self.points['soma'].radius)

        # Create neurites actors
        neurites = {}
        for ntype in self._neurite_types:
            actors = []
            for neurite in self.points[ntype]:
                section_segment_list = [(section, segment)
                                                for section in iter_sections(neurite.component)
                                                for segment in iter_segments(section)]
                segs = [(seg[0][COLS.XYZ], seg[1][COLS.XYZ]) for _, seg in section_segment_list]

                radiuses = _get_linewidth(neurite.component, diameter_scale=1, linewidth=1)
                # TODO create neurons better

                tubes = []
                for seg in segs:
                    rad = segment_radius(seg)



                tree = [Tree(seg)]
                actors.append(Tube(neurite.coords, r=neurite.radius))
            neurites[ntype] = actors

        actors = [act for actors in neurites.values() for act in actors] + [soma]

        whole_neuron = merge(actors)

        a = 1





        
        

