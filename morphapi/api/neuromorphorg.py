import logging
import os

import requests

from morphapi.morphology.morphology import Neuron
from morphapi.paths_manager import Paths
from morphapi.utils.webqueries import connected_to_internet, request

logger = logging.getLogger(__name__)


class NeuroMorpOrgAPI(Paths):
    # Use the URL as advised in the API docs:
    # https://neuromorpho.org/apiReference.html#introduction
    _base_url = "http://cng.gmu.edu:8080/api/neuron"

    _version = "CNG version"  # which swc version, standardized or original

    def __init__(self, *args, **kwargs):
        if not connected_to_internet():
            raise ConnectionError(
                "You will need to be connected to the internet to "
                "use the NeuroMorpOrgAPI class to download neurons"
            )

        Paths.__init__(self, *args, **kwargs)

        # Check that neuromorpho.org is not down
        try:
            health_url = "/".join(self._base_url.split("/")[:-1]) + "/health"
            request(health_url, verify=False)
        except (requests.exceptions.RequestException, ValueError):
            try:
                self._base_url = "http://neuromorpho.org/api/neuron"
                health_url = (
                    "/".join(self._base_url.split("/")[:-1]) + "/health"
                )
                request(health_url, verify=False)
            except (
                requests.exceptions.RequestException,
                ValueError,
            ) as e:
                raise ConnectionError(
                    f"It seems that neuromorpho API is down: {e}"
                )

        self._fields = None

    @property
    def fields(self):
        """
        Fields contains the types of fields that can be used to
        restrict queries
        """
        if self._fields is None:
            self._fields = request(
                self._base_url + "/fields", verify=False
            ).json()["Neuron Fields"]
        return self._fields

    def get_fields_values(self, field):
        """
        Returns the list of allowed values for a given query field
        """
        current_page = 0
        max_page = 1
        values = []
        while current_page < max_page:
            req = request(
                self._base_url
                + f"/fields/{field}?&size=1000&page={current_page}",
                verify=False,
            ).json()
            values.extend(req["fields"])
            max_page = req.get("page", {}).get("totalPages", max_page)
            current_page += 1
        return values

    def get_neurons_metadata(self, size=100, page=0, **criteria):
        """
        Uses the neuromorpho API to download metadata about neurons.
        Criteria can be used to restrict the search to neurons of interest/
        https://neuromorpho.org/apiReference.html

        Neuromorpho.org  paginates it's requests so not all neurons metadata
        can be returned at once

        :param size: int in range [0, 500]. Number of neurons whose
        metadata can be returned at the same time
        :param page: int > 0. Page number. The number of pages depends
        on size and on how many neurons match the criteria
        :param criteria: use keywords to restrict the query to neurons
        that match given criteria.
        keywords should be pass as "field=value".
        Then only neuron's whose 'field'
        attribute has value 'value' will be returned.
        """

        if size < 0 or size > 500:
            raise ValueError(
                f"Invalid size argument: {size}. Size should be an "
                f"integer between 0 and 500"
            )
        if page < 0:
            raise ValueError(
                f"Invalid page argument: {page}. Page should be an "
                f"integer >= 0"
            )

        url = self._base_url + "/select?q="

        for num, (crit, val) in enumerate(criteria.items()):
            if isinstance(val, list):
                raise NotImplementedError("Need to join the list")

            if num > 0:
                url += "&fq="
            url += f"{crit}:{val}"

        url += f"&size={int(size)}&page={int(page)}"

        try:
            req = request(url, verify=False)
            neurons = req.json()
            valid_url = req.ok and "error" not in neurons
        except ValueError:
            valid_url = False

        if not valid_url:
            # Check each criteria
            for crit, val in criteria.items():
                if crit not in self.fields:
                    raise ValueError(
                        f"Query criteria {crit} not in "
                        f"available fields: {self.fields}"
                    )
                field_values = self.get_fields_values(crit)
                if val not in field_values:
                    raise ValueError(
                        f"Query criteria value {val} for "
                        f"field {crit} not valid."
                        + f"Valid values include: {field_values}"
                    )

            # If all criteria look valid, then raise a generic error
            raise ValueError(f"Invalid query with url: {url}")

        page = neurons["page"]
        neurons = neurons["_embedded"]["neuronResources"]

        logger.info(
            f"Found metadata for {page['totalElements']} neurons "
            f"[{page['totalPages']} pages in total]. "
            f"Returning metadata about {len(neurons)} neurons "
            f"from page {page['number']}"
        )

        return neurons, page

    def get_neuron_by_id(self, nid):
        """
        Get a neuron's metadata given it's id number
        """
        return request(self._base_url + f"/id/{nid}", verify=False).json()

    def get_neuron_by_name(self, nname):
        """
        Get a neuron's metadata given it's name
        """
        return request(self._base_url + f"/name/{nname}", verify=False).json()

    def build_filepath(self, neuron_id):
        """
        Build a filepath from a neuron ID.
        """
        return os.path.join(self.neuromorphorg_cache, f"{neuron_id}.swc")

    def download_neurons(
        self,
        neurons,
        _name=None,
        load_neurons=True,
        use_neuron_names=False,
        **kwargs,
    ):
        """
        Downloads neuronal morphological data and saves it to .swc files.
        It then returns a list of Neuron instances with
        morphological data for each neuron.

        :param neurons: list of neurons metadata (as
        returned by one of the functions used to fetch metadata)
        :param _name: used internally to save cached neurons
        with a different prefix when the
            class is used to download neurons for other APIs
        :param load_neurons: if set to True, the neurons are loaded into a
            `morphapi.morphology.morphology.Neuron` object and returned
        :param use_neuron_names: if set to True, the filenames
        use the names of the neurons instead
            of their IDs
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

            if use_neuron_names:
                filepath = self.build_filepath(
                    neuron.get("neuron_name", neuron["neuron_id"])
                )
            else:
                filepath = self.build_filepath(neuron["neuron_id"])
            load_current_neuron = load_neurons

            if not os.path.isfile(filepath):
                # Download and write to file
                if self._version == "CNG version":
                    url = (
                        f"https://neuromorpho.org/dableFiles/{neuron['archive'].lower()}/"
                        f"CNG version/{neuron['neuron_name']}.CNG.swc"
                    )
                else:
                    url = (
                        f"https://neuromorpho.org/dableFiles/{neuron['archive'].lower()}/"
                        f"{self._version}/{neuron['neuron_name']}.swc"
                    )

                try:
                    req = request(url, verify=False)
                    with open(filepath, "w") as f:
                        f.write(req.content.decode("utf-8"))
                except ValueError as exc:
                    logger.error(
                        "Could not fetch the neuron %s for the "
                        "following reason: %s",
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
