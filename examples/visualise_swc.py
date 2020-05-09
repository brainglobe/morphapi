from vtkplotter import show

fp = '/Users/federicoclaudi/Documents/Github/brainrenderscenes/morphologies/bailey/CNG version/Layer-2-3-Ethanol-7.CNG.swc'


neuro = Neuron(swc_file=fp)

_, neuron = neuro.create_mesh()

show(neuron)

