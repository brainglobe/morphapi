
import json
import os 
from tqdm import tqdm
import pandas as pd
from collections import namedtuple
import numpy as np

from allensdk.core.mouse_connectivity_cache import MouseConnectivityCache

from morphapi.morphology.morphology import Neuron
from morphapi.utils.webqueries import post_mouselight, mouselight_base_url
from morphapi.paths_manager import Paths
from morphapi.utils.data_io import is_any_item_in_list
from morphapi.api.neuromorphorg import NeuroMorpOrgAPI


"""
    Collections of functions to query http://ml-neuronbrowser.janelia.org/ and get data about either the status of the API, 
    the brain regions or the neurons available. 
    Queries are sent by sending POST requests to http://ml-neuronbrowser.janelia.org/graphql
    with a string query. 
"""

# ---------------------------------------------------------------------------- #
#                                  QUERY UTILS                                 #
# ---------------------------------------------------------------------------- #

def mouselight_api_info():
    """
        Get the number of cells available in the database
    """
    # Get info from the ML API
    url = mouselight_base_url + "graphql"

    query =  \
            """
            query {
                queryData {
                    totalCount
                    }
                }
            """
    res =  post_mouselight(url, query=query)
    print("{} neurons on MouseLight database. ".format(res['queryData']['totalCount']))

def mouselight_get_brainregions():
    """
        Get metadata about the brain brain regions as they are known by Janelia's Mouse Light. 
        IDs and Names sometimes differ from Allen's CCF.
    """

    # Download metadata about brain regions from the ML API
    url = mouselight_base_url + "graphql"
    # query =  "systemSettings {apiVersion apiRelease neuronCount\}}"
    query =  \
            """
            query {
                brainAreas{
                    
                    acronym
                    name
                    id
                    atlasId
                    graphOrder
                    parentStructureId
                    structureIdPath
                }
            }
            """
    res =  post_mouselight(url, query=query)['brainAreas']

    # Clean up and turn into a dataframe
    keys = {k:[] for k in res[0].keys()}
    for r in res:
        for k in r.keys():
            keys[k].append(r[k])
    
    structures_data = pd.DataFrame.from_dict(keys)
    return structures_data

def mouselight_structures_identifiers():
    """
    When the data are downloaded as SWC, each node has a structure identifier ID to tell if it's soma, axon or dendrite.
    This function returns the ID number --> structure table. 
    """

    # Download the identifiers used in ML neurons tracers
    url = mouselight_base_url + "graphql"
    # query =  "systemSettings {apiVersion apiRelease neuronCount\}}"
    query =  \
        """
            query {
                structureIdentifiers{
                    id
                    name
                    value
                }
            }
        """
    res =  post_mouselight(url, query=query)['structureIdentifiers']

    keys = {k:[] for k in res[0].keys()}
    for r in res:
        for k in r.keys():
            keys[k].append(r[k])
    
    structures_identifiers = pd.DataFrame.from_dict(keys)
    return structures_identifiers

def make_query(filterby=None, filter_regions=None, invert=False):
    """
    Constructs the strings used to submit graphql queries to the mouse light api

    :param filterby: str, soma, axon on dendrite. Search by neurite structure (Default value = None)
    :param filter_regions:  list, tuple. list of strings. Acronyms of brain regions to use for query (Default value = None)
    :param invert:  If true the inverse of the query is return (i.e. the neurons NOT in a brain region) (Default value = False)

    """
    searchneurons = """
                queryTime
                totalCount
                
                neurons{
                tag
                id
                idNumber
                idString
                
                brainArea{
                    id
                    acronym
                    name
                    safeName
                    atlasId
                    aliases
                    structureIdPath
                }

                tracings{
                    soma{
                    x
                    y
                    z
                    radius
                    brainArea{
                        id
                        acronym
                    }
                    sampleNumber
                    parentNumber
                    
                    }
                
                id
                tracingStructure{
                    name
                    value
                    id
                }
                }
            }
    """


    if filterby is None or filterby == 'soma':
        query = """
                    query {{
                        searchNeurons {{
                            {}
                        }}
                    }}
                    """.format(searchneurons)
    else:
        raise NotImplementedError("This feature is not available yet")
        # Get predicate type
        if filterby.lower() in ['axon','axons', 'end point', 'branch point']:     
            predicateType = 1
            
        elif filterby.lower() in ['dendrite', 'apical dendrite', '(basal) dendrite']:
            raise NotImplementedError
            filterby = "(basal) dendrite"
            predicateType = 2
        else:
            raise ValueError("invalid search by argument")

        # Get neuron structure id
        structures_identifiers = mouselight_structures_identifiers()
        structureid = str(structures_identifiers.loc[structures_identifiers.name == filterby]['id'].values[0])

        # Get brain regions ids
        brainregions = mouselight_get_brainregions()
        brainareaids = [str(brainregions.loc[brainregions.acronym == a]['id'].values[0]) for a in filter_regions]

        # Get inversion
        if invert:
            invert = "true"
        else:
            invert = "false"

        query = """
        query {{
            searchNeurons (
                context: {{
                scope: 6
                predicates: [{{
                    predicateType: {predicate}
                    tracingIdsOrDOIs: []
                    tracingIdsOrDOIsExactMatch: false
                    tracingStructureIds: []
                    amount: 0
                    nodeStructureIds: ['{structure}']
                    brainAreaIds: {brainarea}
                    invert: {invert}
                    composition: 1
                    }}]
                }}
            ) {{
                {base}
            }}
        }}
        """.format(predicate=predicateType,  structure=str(structureid), brainarea=brainareaids, invert=invert, base=searchneurons)

        query = query.replace("\\t", "").replace("'", '"')
    return query
    



# ---------------------------------------------------------------------------- #
#                                  MAIN CLASS                                  #
# ---------------------------------------------------------------------------- #

class MouseLightAPI(Paths):
    def __init__(self, base_dir=None, **kwargs):
        """
            Handles the download of neurons morphology data from the Mouse Light project

            :param base_dir: path to directory to use for saving data (default value None)
            :param kwargs: can be used to pass path to individual data folders. See morphapi/utils /paths_manager.py
        """
        Paths.__init__(self, base_dir=base_dir, **kwargs)


    def fetch_neurons_metadata(self, filterby = None, filter_regions=None, **kwargs):
        """
        Download neurons metadata and data from the API. The downloaded metadata can be filtered to keep only
        the neurons whose soma is in a list of user selected brain regions.
        
        :param filterby: Accepted values: "soma". If it's "soma", neurons are kept only when their soma
                        is in the list of brain regions defined by filter_regions (Default value = None)
        :param filter_regions: List of brain regions acronyms. If filtering neurons, these specify the filter criteria. (Default value = None)
        :param **kwargs: 

        """
        # Download all metadata
        print("Querying MouseLight API...")
        url = mouselight_base_url + "graphql"
        query = make_query(filterby=filterby, filter_regions=filter_regions, **kwargs)

        res =  post_mouselight(url, query=query)['searchNeurons']
        print("     ... fetched metadata for {} neurons in {}s".format(res["totalCount"], round(res["queryTime"]/1000, 2)))

        # Process neurons to clean up the results and make them easier to handle
        neurons = res['neurons']
        node = namedtuple("node", "x y z r area_acronym sample_n parent_n")
        tracing_structure = namedtuple("tracing_structure", "id name value named_id")

        cleaned_nurons = [] # <- output is stored here
        for neuron in neurons:
            if neuron['brainArea'] is not None:
                brainArea_acronym = neuron['brainArea']['acronym']
                brainArea_id = neuron['brainArea']['id']
                brainArea_name = neuron['brainArea']['name']
                brainArea_safename = neuron['brainArea']['safeName']
                brainArea_atlasId = neuron['brainArea']['atlasId']
                brainArea_aliases = neuron['brainArea']['aliases']
                brainArea_structureIdPath = neuron['brainArea']['structureIdPath']
            else:
                brainArea_acronym = None
                brainArea_id = None
                brainArea_name = None
                brainArea_safename = None
                brainArea_atlasId = None
                brainArea_aliases = None
                brainArea_structureIdPath = None

            if len(neuron['tracings']) > 1:
                dendrite = tracing_structure(
                    neuron['tracings'][1]['id'],
                    neuron['tracings'][1]['tracingStructure']['name'],
                    neuron['tracings'][1]['tracingStructure']['value'],
                    neuron['tracings'][1]['tracingStructure']['id'],
                )
            else:
                dendrite = None

            clean_neuron = dict(
                brainArea_acronym = brainArea_acronym,
                brainArea_id = brainArea_id,
                brainArea_name = brainArea_name,
                brainArea_safename = brainArea_safename,
                brainArea_atlasId = brainArea_atlasId,
                brainArea_aliases = brainArea_aliases,
                brainArea_structureIdPath = brainArea_structureIdPath,

                id = neuron['id'],
                idNumber = neuron['idNumber'],
                idString = neuron['idString'],
                tag=neuron['tag'],
                soma = node(
                    neuron['tracings'][0]['soma']['x'],
                    neuron['tracings'][0]['soma']['y'],
                    neuron['tracings'][0]['soma']['z'],
                    neuron['tracings'][0]['soma']['radius'],
                    neuron['tracings'][0]['soma']['brainArea'],
                    neuron['tracings'][0]['soma']['sampleNumber'],
                    neuron['tracings'][0]['soma']['parentNumber']
                ),
                axon = tracing_structure(
                    neuron['tracings'][0]['id'],
                    neuron['tracings'][0]['tracingStructure']['name'],
                    neuron['tracings'][0]['tracingStructure']['value'],
                    neuron['tracings'][0]['tracingStructure']['id'],
                ),
                dendrite = dendrite,
            )
            cleaned_nurons.append(clean_neuron)

        # Filter neurons to keep only those matching the search criteria
        if filterby is not None:
            if filter_regions is None:
                raise ValueError("If filtering neuron by region, you need to pass a list of filter regions to use")

            # Get structure tree 
            smc = MouseConnectivityCache(manifest_file=os.path.join(self.mouse_connectivity_cache, "manifest.json"))
            structure_tree = smc.get_structure_tree()
            ancestors_tree = structure_tree.get_ancestor_id_map()
            filter_regions_ids = [struct['id'] for struct in structure_tree.get_structures_by_acronym(filter_regions)]

            # Filter by soma
            if filterby == "soma":
                filtered_neurons = []
                for neuron in cleaned_nurons:
                    if neuron['brainArea_acronym'] is None: 
                        continue

                    # Get region ID (of the soma) and the IDs of its ancestors
                    region = structure_tree.get_structures_by_acronym([neuron['brainArea_acronym']])[0]
                    region_ancestors = ancestors_tree[region['id']]

                    # If any of the ancestors are in the allowed regions, keep neuron.
                    if is_any_item_in_list(filter_regions_ids, region_ancestors):
                        filtered_neurons.append(neuron)
                print("	... selected {} neurons out of {}".format(len(filtered_neurons), res["totalCount"]))
                
                neurons =  filtered_neurons
            else:
                print("	... selected {} neurons out of {}".format(len(cleaned_nurons), res["totalCount"]))
                neurons =  cleaned_nurons
        else:
            neurons = cleaned_nurons

        return neurons


    def download_neurons(self, neurons_metadata):
        """
        Given a list of neurons metadata from self.fetch_neurons_metadata
        this funcition downloads the morphological data.
        The data are actually downloaded from neuromorpho.org
        
        :param neurons_metadata: list with metadata for neurons to download
        :returns: list of Neuron instances

        """

        nmapi = NeuroMorpOrgAPI()

        neurons = []
        for neuron in tqdm(neurons_metadata):
            neurons.append(nmapi.download_neurons(nmapi.get_neuron_by_name(neuron['idString'])))

        # ? Old code
        # def get(url, tracing_id): # send a query for a single tracing ID
        #     """
        #     Creates the URL for each neuron to download

        #     :param url: str with url
        #     :param tracing_id: str with the neuron's ID

        #     """
        #     query = {"ids":[tracing_id]}
        #     res = post_mouselight(url, query=query, clean=True)['tracings']
        #     return res

        # if neurons_metadata is None or not neurons_metadata:
        #     return None
        # print("Downloading neurons tracing data from Mouse Light")

        # # check arguments
        # if not isinstance(neurons_metadata, list): neurons_metadata = [neurons_metadata]

        # # URL used to fetch neurons
        # url = mouselight_base_url + "tracings/tracings"

        # # loop over neurons
        # neurons = []
        # for neuron in tqdm(neurons_metadata):
        #     # Check if a .swc file already exists for this neuron
        #     file_path = os.path.join(self.mouselight_cache, neuron['idString']+".swc")
            
        #     if not os.path.isfile(file_path): 
        #         # Download and save as swc
        #         # Get tracings by requests
        #         axon_tracing, dendrite_tracing = None, None
        #         if neuron['axon'] is not None:
        #             axon_tracing = get(url, neuron['axon'].id)
        #         if neuron['dendrite'] is not None:
        #             dendrite_tracing = get(url, neuron['dendrite'].id)

        #         self.make_swc(neuron, file_path, axon_tracing=axon_tracing, dendrite_tracing=dendrite_tracing)

        #     # Reconstruct from .swc
        #     neurons.append(Neuron(file_path,))

        return neurons







"""
Old code to fetch morphological data from mouselight database
"""
    # @staticmethod
    # def make_json(neuron, file_path,  axon_tracing=None, dendrite_tracing=None):
    #     """
    #     Creates a .json file with the neuron's data that can be read by the mouselight parser.

    #     :param neuron: dict with neuron's data
    #     :param file_path: str, path where to save the json file
    #     :param axon_tracing: list with data for axon tracing (Default value = None)
    #     :param dendrite_tracing: list with data for dendrite tracing (Default value = None)

    #     """
    #     # parse axon
    #     if axon_tracing is not None:
    #         nodes = axon_tracing[0]['nodes']
    #         axon = [
    #             dict(
    #                 sampleNumber = n['sampleNumber'],
    #                 x = n['x'],
    #                 y = n['y'],
    #                 z = n['z'],
    #                 radius = n['radius'],
    #                 parentNumber = n['parentNumber'],
    #             )
    #             for n in nodes]
    #     else:
    #         axon = []

    #     # parse dendrites
    #     if dendrite_tracing is not None:
    #         nodes = dendrite_tracing[0]['nodes']
    #         dendrite = [
    #             dict(
    #                 sampleNumber = n['sampleNumber'],
    #                 x = n['x'],
    #                 y = n['y'],
    #                 z = n['z'],
    #                 radius = n['radius'],
    #                 parentNumber = n['parentNumber'],
    #             )
    #             for n in nodes]
    #     else:
    #         dendrite = []

    #     content = dict(
    #         neurons = [
    #             dict(
    #                 idString = neuron['idString'],
    #                 soma = dict(
    #                     x = neuron['soma'].x,
    #                     y = neuron['soma'].y,
    #                     z = neuron['soma'].z,
    #                 ),
    #                 axon = axon, 
    #                 dendrite = dendrite,

    #             )
    #         ]
    #     )


    #     # save to file
    #     if not filepath.endswith('.json'):
    #         raise ValueError(f'Invalid file path {filepath}')
    #     with open(file_path, 'w') as f:
    #         json.dump(content, f)

    # @staticmethod
    # def make_swc(neuron, file_path,  axon_tracing=None, dendrite_tracing=None):
    #     """
    #     Creates a .swc file with the neuron's data that can be read by the mouselight parser.

    #     :param neuron: dict with neuron's data
    #     :param file_path: str, path where to save the swc file
    #     :param axon_tracing: list with data for axon tracing (Default value = None)
    #     :param dendrite_tracing: list with data for dendrite tracing (Default value = None)

    #     """

    #     if not file_path.endswith('.swc'):
    #         raise ValueError(f'Invalid file path {file_path}')

    #     # parse data
    #     if axon_tracing is not None:
    #         nodes = axon_tracing[0]['nodes']
    #         axon = [
    #             dict(
    #                 sampleNumber = n['sampleNumber'],
    #                 x = n['x'],
    #                 y = n['y'],
    #                 z = n['z'],
    #                 id = 2,
    #                 radius = n['radius'],
    #                 parentNumber = n['parentNumber'],
    #             )
    #             for n in nodes]
    #     else:
    #         axon = []

    #     if dendrite_tracing is not None:
    #         nodes = dendrite_tracing[0]['nodes']
    #         dendrite = [
    #             dict(
    #                 sampleNumber = n['sampleNumber'],
    #                 x = n['x'],
    #                 y = n['y'],
    #                 z = n['z'],
    #                 radius = n['radius'],
    #                 id = 3,
    #                 parentNumber = n['parentNumber'],
    #             )
    #             for n in nodes]
    #     else:
    #         dendrite = []

    #     # Save as swc
    #     with open(file_path, 'w') as out:
    #         out.write(f"# neuron: {neuron['idString']} downloaded from mouselight database [janelia campus]\n")
    #         out.write("# .swc reconstructed using morphapi python package https://github.com/brainglobe/morphapi\n\n")
    #         out.write("# id,type,x,y,z,r,pid\n")
    #         out.write(f" 1 1 {neuron['soma'].x} "+
    #                     f"{neuron['soma'].y} {neuron['soma'].z} "+
    #                     f"{neuron['soma'].r} -1\n")


    #         neurites = axon + dendrite
    #         sort_idx = np.argsort([n['parentNumber'] for n in neurites])
    #         neurites = list(np.array(neurites)[sort_idx])

    #         for n in neurites:
    #             if n['parentNumber'] == -1:
    #                 pn = 1
    #             else:
    #                 pn = n['parentNumber']
    #             out.write(f" {n['sampleNumber']} {n['id']} {n['x']} {n['y']} {n['z']} {n['radius']} {pn}\n")
