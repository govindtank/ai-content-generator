"""Anthropic AI provider implementation."""

from app.providers import BaseProvider


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider for text generation."""

    @property
    def name(self) -> str:
        return "Anthropic Claude"

    @property
    def slug(self) -> str:
        return "anthropic"

    def __init__(self, api_key: str = ""):
        self._api_key = api_key
        self._client = None
        if api_key:
            self._init_client()

    def _init_client(self):
        try:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self._api_key)
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")

    def _ensure_client(self):
        if self._client is None:
            if self._api_key:
                self._init_client()
            else:
                raise ValueError("Anthropic API key not set")

    def generate_text(self, prompt: str, model: str | None = None, **kwargs) -> str:
        self._ensure_client()
        model_name = model or "claude-sonnet-4-20250514"
        response = self._client.messages.create(
            model=model_name,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    def generate_image(
        self,
        prompt: str,
        **kwargs,
    ) -> tuple[bytes, str] | None:
        return None  # Anthropic doesn't support image generation via API

    def validate_key(self, api_key: str) -> tuple[bool, str]:
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True, ""
        except ImportError:
            return False, "anthropic package not installed"
        except Exception as e:
            return False, str(e)
