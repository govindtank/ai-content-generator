"""Multi-provider AI content generation system.

Architecture:
- BaseProvider: abstract interface for text + image generation
- ProviderRouter: routes requests to the right provider, manages fallback
- Each provider implements the BaseProvider interface
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """Abstract base class for AI content providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g. 'Gemini', 'OpenAI')."""
        ...

    @property
    @abstractmethod
    def slug(self) -> str:
        """URL-safe provider slug (e.g. 'gemini', 'openai')."""
        ...

    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text content from a prompt."""
        ...

    @abstractmethod
    def generate_image(self, prompt: str, **kwargs) -> Optional[tuple[bytes, str]]:
        """Generate an image from a prompt. Returns (image_bytes, mime_type) or None."""
        ...

    @abstractmethod
    def validate_key(self, api_key: str) -> tuple[bool, str]:
        """Test if an API key is valid. Returns (is_valid, error_message)."""
        ...


class ProviderRouter:
    """Routes generation requests to the appropriate provider."""

    def __init__(self):
        self._providers: dict[str, type[BaseProvider]] = {}

    def register(self, provider_cls: type[BaseProvider]) -> None:
        instance = provider_cls(api_key="")  # temp instance just for slug
        self._providers[instance.slug] = provider_cls
        logger.info(f"Registered provider: {instance.slug}")

    def get_provider(self, slug: str, api_key: str) -> BaseProvider:
        cls = self._providers.get(slug)
        if not cls:
            raise ValueError(f"Unknown provider: {slug}. Available: {list(self._providers.keys())}")
        return cls(api_key=api_key)

    def get_available(self) -> list[dict]:
        """Return list of registered provider metadata."""
        result = []
        for slug, cls in self._providers.items():
            inst = cls(api_key="")
            result.append({
                "slug": slug,
                "name": inst.name,
                "supports_text": hasattr(inst, "generate_text"),
                "supports_image": hasattr(inst, "generate_image"),
            })
        return result

    def list_slugs(self) -> list[str]:
        return list(self._providers.keys())


# Global router instance
router = ProviderRouter()


def guess_provider_from_key(api_key: str) -> Optional[str]:
    """Try to guess which provider an API key belongs to based on format."""
    if api_key.startswith("AIza"):
        return "gemini"
    if api_key.startswith("sk-"):
        return "openai"
    if api_key.startswith("sk-ant-"):
        return "anthropic"
    return None
