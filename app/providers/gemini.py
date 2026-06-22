"""Gemini AI provider implementation."""

from app.providers import BaseProvider
from google import genai as genai_client
from google.genai import types


class GeminiProvider(BaseProvider):
    """Google Gemini provider for text and image generation."""

    @property
    def name(self) -> str:
        return "Google Gemini"

    @property
    def slug(self) -> str:
        return "gemini"

    def __init__(self, api_key: str = ""):
        self._api_key = api_key
        self._client = None
        if api_key:
            self._client = genai_client.Client(api_key=api_key)

    def _ensure_client(self):
        if self._client is None:
            if self._api_key:
                self._client = genai_client.Client(api_key=self._api_key)
            else:
                raise ValueError("Gemini API key not set")

    def generate_text(self, prompt: str, model: str | None = None, **kwargs) -> str:
        self._ensure_client()
        model_name = model or "gemini-2.0-flash"
        response = self._client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return response.text

    def generate_image(
        self,
        prompt: str,
        model: str | None = None,
        aspect_ratio: str = "1:1",
        **kwargs,
    ) -> tuple[bytes, str] | None:
        self._ensure_client()
        model_name = model or "gemini-2.5-flash-image"
        config = types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=aspect_ratio,
        )
        response = self._client.models.generate_images(
            model=model_name,
            prompt=prompt,
            config=config,
        )
        if response.generated_images:
            img = response.generated_images[0].image
            if img and img.image_bytes:
                return img.image_bytes, img.mime_type or "image/png"
        return None

    def validate_key(self, api_key: str) -> tuple[bool, str]:
        try:
            client = genai_client.Client(api_key=api_key)
            client.models.list()
            return True, ""
        except Exception as e:
            return False, str(e)
