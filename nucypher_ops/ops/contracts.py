from typing import Union

import requests


class NuCypherContractRegistry:

    """
    A simple/dumber version of nucypher/nucypher/blockchain/eth/registry.py
    """

    _PUBLICATION_REPO = "nucypher/nucypher"
    _BASE_URL = f'https://raw.githubusercontent.com/{_PUBLICATION_REPO}'

    name = "GitHub Registry Source"
    is_primary = True

    def __init__(self, domain='mainnet'):
        self.domain = domain

    def get_publication_endpoint(self) -> str:
        url = f"{self._BASE_URL}/development/nucypher/blockchain/eth/contract_registry/{self.domain}.json"
        return url

    def fetch_latest_publication(self) -> Union[str, bytes]:
        # Setup
        publication_endpoint = self.get_publication_endpoint()
        try:
            # Fetch
            response = requests.get(publication_endpoint)
        except requests.exceptions.ConnectionError as e:
            raise

        if response.status_code != 200:
            raise AttributeError(f"No registry found at {self.get_publication_endpoint()}")

        registry_data = response.json()
        return registry_data
