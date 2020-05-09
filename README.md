# morphapi
## Overview
Morphapi is a lightweight python package for downloading neurons
morphological reconstructions from publicly available datasets. 

Neuromorph api can be used to download data from the following sources:
  * [Allen brain atlas - Cell Types](https://celltypes.brain-map.org/)
  * [neuromorpho.org](http://neuromorpho.org/)
  * [Janelia Campus - Mouse Light project](https://www.janelia.org/project-team/mouselight)

Neuromorph relies on the [`neurom`](https://zenodo.org/record/209498#.XraWUsZ7l24) package from
the BlueBrain project ([github](https://github.com/BlueBrain/NeuroM)) to reconstruct morphology
from `.swc` files and on [`vtkplotter`](https://github.com/marcomusy/vtkplotter) to create 3d
rendering from morphological data.

## Installation
morphapi will be published on Pypi soon, meanwhile you can install with:

```
    pip install git+https://github.com/brainglobe/morphapi.git
```



## References
* Juan Palacios, lidakanari, Eleftherios Zisis, MikeG, Liesbeth Vanherpe, Jean-Denis Courcol, & Oren Amsalem. (2016, December 19). BlueBrain/NeuroM: v1.2.0 (Version v1.2.0). Zenodo. http://doi.org/10.5281/zenodo.209498
* M. Musy et al. "vtkplotter, a python module for scientific visualization and analysis of 3D objects and point clouds based on VTK (Visualization Toolkit)", Zenodo, 10 February 2019, doi: 10.5281/zenodo.2561402.
*  Winnubst, J. et al. (2019) Reconstruction of 1,000 Projection Neurons Reveals New Cell Types and Organization of Long-Range Connectivity in the Mouse Brain, Cell 179: 268-281