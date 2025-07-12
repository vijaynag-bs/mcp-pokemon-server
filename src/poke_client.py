import logging
from typing import Optional, Dict, Any
from pydantic import HttpUrl, Field, BaseModel
from pydantic_settings import BaseSettings
import requests

logger = logging.getLogger(__name__)


class PokeClientSettings(BaseSettings):
    """Configuration for PokeClient."""

    base_url: HttpUrl = Field("https://pokeapi.co/api/v2", env="POKE_API_SERVER")
    api_key: Optional[str] = Field(None, env="POKE_API_KEY")

    class Config:
        env_file = ".env"


class Auth:
    """Placeholder for authentication logic."""

    pass


class PokemonResponse(BaseModel):
    """Example Pydantic model for validating Pokemon API responses."""

    name: str
    id: int
    # Add more fields as needed


class PokeClient:
    """Client for interacting with the PokeAPI."""

    def __init__(
        self,
        settings: Optional[PokeClientSettings] = None,
        auth: Optional[Auth] = None,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize the PokeClient.

        Args:
            settings: Configuration for the client.
            auth: Optional authentication handler.
            session: Optional requests.Session for connection pooling/testing.
        """
        self.settings = settings or PokeClientSettings()
        self.auth = auth
        self.session = session or requests.Session()

    def get_pokemon_data(self, name: str, endpoint: str = "/pokemon") -> Dict[str, Any]:
        """
        Fetch data for a given Pokémon by name.

        Args:
            name: The name of the Pokémon.

        Returns:
            A dictionary with Pokémon data.

        Raises:
            requests.HTTPError: If the request fails.
            ValueError: If the response is invalid.
        """
        url = f"{self.settings.base_url}{endpoint}/{name}"
        logger.info(f"Requesting Pokémon data from %s", url)
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Optionally validate with Pydantic:
            # validated = PokemonResponse.parse_obj(data)
            return data
        except requests.HTTPError as http_err:
            logger.error("HTTP error occurred: %s", http_err)
            raise
        except Exception as err:
            logger.error("Unexpected error occurred: %s", err)
            raise

    def close(self):
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
