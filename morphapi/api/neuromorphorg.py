import os
import logging

from morphapi.utils.webqueries import request, connected_to_internet
from morphapi.paths_manager import Paths
from morphapi.morphology.morphology import Neuron

logger = logging.getLogger(__name__)


class NeuroMorpOrgAPI(Paths):
    _base_url = "http://neuromorpho.org/api/neuron"

    _version = "CNG version"  # which swc version, standardized or original

    def __init__(self, *args, **kwargs):
        if not connected_to_internet():
            raise ConnectionError(
                "You will need to be connected to the internet to use the NeuroMorpOrgAPI class to download neurons"
            )

        Paths.__init__(self, *args, **kwargs)

        # Check that neuromorpho.org is not down
        try:
            request("http://neuromorpho.org/api/health")
        except Exception as e:
            raise ConnectionError(
                f"It seems that neuromorphos API is down: {e}"
            )

        # Fields contains the types of fields that can be used to restrict queries
        self.fields = request(self._base_url + "/fields").json()[
            "Neuron Fields"
        ]

    def get_fields_values(self, field):
        """
            Returns the list of allowed values for a given query field
        """
        return list(
            request(self._base_url + f"/fields/{field}").json()["fields"]
        )

    def get_neurons_metadata(self, size=100, page=0, **criteria):
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

        if size < 0 or size > 500:
            raise ValueError(
                f"Invalid size argument: {size}. Size should be an integer between 0 and 500"
            )
        if page < 0:
            raise ValueError(
                f"Invalid page argument: {page}. Page should be an integer >= 0"
            )

        url = self._base_url + "/select?q="

        for n, (crit, val) in enumerate(criteria.items()):
            if crit not in self.fields:
                raise ValueError(
                    f"Query criteria {crit} not in available fields: {self.fields}"
                )
            elif val not in self.get_fields_values(crit):
                raise ValueError(
                    f"Query criteria value {val} for field {crit} not valid."
                    + f"Valid values include: {self.get_fields_values(crit)}"
                )

            if isinstance(val, list):
                raise NotImplementedError("Need to join the list")

            if n > 0:
                url += "&fq="
            url += f"{crit}:{val}"

        url += f"&size={int(size)}&page={int(page)}"
        req = request(url)

        if not req.ok:
            raise ValueError(f"Invalid query with url: {url}")
        else:
            neurons = req.json()

        page = neurons["page"]
        neurons = neurons["_embedded"]["neuronResources"]

        logger.info(
            f"Found metadata for {page['totalElements']} neurons [{page['totalPages']} pages in total]. "
            f"Returning metadata about {len(neurons)} neurons from page {page['number']}"
        )

        return neurons, page

    def get_neuron_by_id(self, nid):
        """
            Get a neuron's metadata given it's id number
        """
        return request(self._base_url + f"/id/{nid}").json()

    def get_neuron_by_name(self, nname):
        """
            Get a neuron's metadata given it's name
        """
        return request(self._base_url + f"/name/{nname}").json()

    def build_filepath(self, neuron_id):
        """
            Build a filepath from a neuron ID.
        """
        return os.path.join(self.neuromorphorg_cache, f"{neuron_id}.swc")

    def download_neurons(
        self, neurons, _name=None, load_neurons=True, **kwargs
    ):
        """
            Downloads neuronal morphological data and saves it to .swc files.
            It then returns a list of Neuron instances with morphological data for each neuron.

            :param neurons: list of neurons metadata (as returned by one of the functions
                        used to fetch metadata)
            :param _name: used internally to save cached neurons with a different prefix when the
                    class is used to download neurons for other APIs
        """
        if not isinstance(neurons, (list, tuple)):
            neurons = [neurons]

        to_return = []
        for neuron in neurons:
            if not isinstance(neuron, dict):
                raise ValueError()

            try:
                neuron["status"] == 500  # download went wrong
                continue
            except KeyError:
                pass

            filepath = self.build_filepath(neuron["neuron_id"])
            load_current_neuron = load_neurons

            if not os.path.isfile(filepath):
                # Download and write to file
                if self._version == "CNG version":
                    url = f"http://neuromorpho.org/dableFiles/{neuron['archive'].lower()}/CNG version/{neuron['neuron_name']}.CNG.swc"
                else:
                    url = f"http://neuromorpho.org/dableFiles/{neuron['archive'].lower()}/{self._version}/{neuron['neuron_name']}.swc"

                try:
                    req = request(url)
                    with open(filepath, "w") as f:
                        f.write(req.content.decode("utf-8"))
                except ValueError as exc:
                    logger.error(
                        "Could not fetch the neuron %s for the following reason: %s",
                        neuron["neuron_name"],
                        str(exc),
                    )
                    load_current_neuron = False

            if _name is None:
                _name = "neuromorpho_"

            to_return.append(
                Neuron(
                    filepath,
                    neuron_name=_name + str(neuron["neuron_id"]),
                    load_file=load_current_neuron,
                    **kwargs,
                )
            )

        return to_return
