
import os

from morphapi.utils.webqueries import request, connected_to_internet
from morphapi.paths_manager import Paths
from morphapi.morphology.morphology import Neuron


class NeuroMorpOrgAPI(Paths):
    _base_url = 'http://neuromorpho.org/api/neuron'

    _version = 'CNG version' # which swc version, standardized or original

    def __init__(self, *args, **kwargs):
        if not connected_to_internet():
            raise ConnectionError("You will need to be connected to the internet to use the NeuroMorpOrgAPI class to download neurons")

        Paths.__init__(self, *args, **kwargs)

        # Fields contains the types of fields that can be used to restrict queries
        self.fields = request(self._base_url+'/fields').json()['Neuron Fields']

    def get_fields_values(self, field):
        """
            Returns the list of allowed values for a given query field
        """
        return list(request(self._base_url+f'/fields/{field}').json()['fields'])

    def get_neurons_metadata(self, size=100, page=0,  **criteria):
        """
            Uses the neuromorpho API to download metadata about neurons.
            Criteri can be used to restrict the search to neurons of interest/
            http://neuromorpho.org/apiReference.html

            Neuromorpho.org  paginates it's requests so not all neurons metadata
            can be returned at once

            :param size: int in range [0, 500]. Number of neurons whose metadata can be returned at the same time
            :param page: int > 0. Page number. The number of pages depends on size and on how many neurons match the criteria
            :param criteria: use keywords to restrict the query to neurons that match given criteria.
                    keywords should be pass as "field=value". Then only neuron's whose 'field'
                    attribute has value 'value' will be returned.
        """

        if size < 0 or size>500:
            raise ValueError(f"Invalid size argument: {size}. Size should be an integer between 0 and 500")
        if page < 0:
            raise ValueError(f"Invalid page argument: {page}. Page should be an integer >= 0")


        url = self._base_url+'/select?q='

        for n, (crit, val) in enumerate(criteria.items()):
            if crit not in self.fields:
                raise ValueError(f"Query criteria {crit} not in available fields: {self.fields}")
            elif val not in self.get_fields_values(crit):
                raise ValueError(f"Query criteria value {val} for field {crit} not valid."+
                        f"Valid values include: {self.get_fields_values(crit)}")

            if isinstance(val, list):
                raise NotImplementedError('Need to join the list')

            if n>0:
                url += '&'
            url += f'{crit}:{val}'

        url += f'&size={int(size)}&page={int(page)}'
        req = request(url)

        if not req.ok:
            raise ValueError(f'Invalid query with url: {url}')
        else:
            neurons = req.json()

        page = neurons['page']    
        neurons = neurons['_embedded']['neuronResources']

        print(f"Found metadata for {page['totalElements']} neurons [{page['totalPages']} pages in total]"+
                f"\nReturning metadata about {len(neurons)} neurons from page {page['number']}")

        return neurons, page

    def get_neuron_by_id(self, nid):
        """
            Get a neuron's metadata given it's id number
        """
        return request(self._base_url+f'/id/{nid}').json()

    def get_neuron_by_name(self, nname):
        """
            Get a neuron's metadata given it's name
        """
        return request(self._base_url+f'/name/{nname}').json()

    def download_neurons(self, neurons, _name=None, **kwargs):
        """
            Downloads neuronal morphological data and saves it to .swc files. 
            It then returns a list of Neuron instances with morphological data for each neuron.

            :param neurons: list of neurons metadata (as returned by one of the functions
                        used to fetch metadata)
            :param _name: used internally to save cached neurons with a different prefix when the 
                    class is used to download neurons for other APIs
        """
        if not isinstance(neurons, (list, tuple)):
            neurons  = [neurons]
        
        to_return = []
        for neuron in neurons:

            if not isinstance(neuron, dict):
                raise ValueError()

            filepath = os.path.join(self.neuromorphorg_cache, f"{neuron['neuron_id']}.swc")

            if not os.path.isfile(filepath):
                # Download and write to file
                url = f"http://neuromorpho.org/dableFiles/{neuron['archive'].lower()}/{self.version}/{neuron['neuron_name']}.CNG.swc"

                req = request(url)
                if not req.ok:
                    raise ValueError(f"Failed to getch morphology data for neuron: {neuron['name']}")

                with open(filepath, 'w') as f:
                    f.write(req.content.decode('utf-8'))

            if _name is None: 
                _name = 'neuromorpho_'

            to_return.append(Neuron(filepath, neuron_name=_name+str(neuron['neuron_id'])))
            
        return to_return



# TODO fix bug with caching paths and finish brainrender update