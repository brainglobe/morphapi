
from brainrender.Utils.webqueries import request


class NeuroMorpOrgAPI():
    _base_url = 'http://neuromorpho.org/api/neuron'

    def __init__(self):
        self.fields = request(self._base_url+'/fields').json()['Neuron Fields']

    def get_fields_values(self, field):
        return list(request(self._base_url+f'/fields/{field}').json()['fields'])

    def get_neurons_metadata(self, size=100, page=0,  **criteria):
        """
            http://neuromorpho.org/apiReference.html
        """

        url = self._base_url+'/select?q='

        for n, (crit, val) in enumerate(criteria.items()):
            if crit not in self.fields:
                raise ValueError(f"Query criteria {crit} not in available fields: {self.fields}")
            elif val not in self.get_fields_values(crit):
                raise ValueError(f"Query criteria value {val} for field {crit} not valid.")

            if isinstance(val, list):
                raise NotImplementedError('Need to join the list')

            if n>0:
                url += '&'
            url += f'{crit}:{val}'

        url += f'&size={size}&page={page}'
        print(url)
        req = request(url)

        if not req.ok:
            raise ValueError(f'Invalid query with url: {url}')
        else:
            neurons = req.json()

        page = neurons['page']    
        neurons = neurons['_embedded']['neuronResources']
        

        print(f"Found metadata for {pages['totalElements']} neurons [{page['totalPages']} pages in total]"+
                f"\nReturning metadata about {len(neurons)} neurons from page {page['number']}")

        return neurons, page

    def get_neuron_by_id(self, nid):
        return request(self._base_url+f'/id/{nid}').json()

    def get_neuron_by_name(self, nname):
        return request(self._base_url+f'/name/{nname}').json()

    def get_neuron_swc(self, neuron):
        if not isinstance(neuron, dict):
            raise ValueError

        # TODO if .swc file exists already load it otherwise download data and save

        url = f"http://neuromorpho.org/dableFiles/{neuron['archive'].lower()}/CNG version/{neuron['neuron_name']}.CNG.swc"

        with open('test.swc', 'w') as f:
            f.write(req.content.decode('utf-8'))



api = NeuroMorpOrgAPI()

# neurons, pages = api.get_neurons_metadata(species='mouse', 
#                         cell_type= 'astrocyte',
#                         page=2)


neuron = api.get_neuron_by_id('1000')



url = f"http://neuromorpho.org/dableFiles/{neuron['archive'].lower()}/CNG version/{neuron['neuron_name']}.CNG.swc"
print(url)
req = request(url)

with open('test.swc', 'w') as f:
    f.write(req.content.decode('utf-8'))


