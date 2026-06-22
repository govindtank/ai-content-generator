"""OpenAI AI provider implementation."""

from app.providers import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI provider for text and image generation."""

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def slug(self) -> str:
        return "openai"

    def __init__(self, api_key: str = ""):
        self._api_key = api_key
        self._client = None
        if api_key:
            self._init_client()

    def _init_client(self):
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")

    def _ensure_client(self):
        if self._client is None:
            if self._api_key:
                self._init_client()
            else:
                raise ValueError("OpenAI API key not set")

    def generate_text(self, prompt: str, model: str | None = None, **kwargs) -> str:
        self._ensure_client()
        model_name = model or "gpt-4o"
        response = self._client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    def generate_image(
        self,
        prompt: str,
        model: str | None = None,
        aspect_ratio: str = "1:1",
        **kwargs,
    ) -> tuple[bytes, str] | None:
        self._ensure_client()
        model_name = model or "dall-e-3"
        size_map = {"1:1": "1024x1024", "16:9": "1792x1024", "9:16": "1024x1792",
                    "4:3": "1024x768", "3:4": "768x1024"}
        size = size_map.get(aspect_ratio, "1024x1024")
        response = self._client.images.generate(
            model=model_name,
            prompt=prompt,
            size=size,
            n=1,
        )
        from urllib.request import urlopen
        img_url = response.data[0].url
        img_bytes = urlopen(img_url).read()
        return img_bytes, "image/png"

    def validate_key(self, api_key: str) -> tuple[bool, str]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            client.models.list()
            return True, ""
        except ImportError:
            return False, "openai package not installed"
        except Exception as e:
            return False, str(e)
