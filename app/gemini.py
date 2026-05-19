from google import genai as genai_client
from google.genai import types

from app.config import Config


class GeminiClient:
    def __init__(self, api_key: str):
        self._client = genai_client.Client(api_key=api_key)

    def generate_text(self, prompt: str, model: str | None = None) -> str:
        model_name = model or Config.GEMINI_TEXT_MODEL
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
    ) -> tuple[bytes, str] | None:
        model_name = model or Config.GEMINI_IMAGE_MODEL
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

    @staticmethod
    def validate_api_key(api_key: str) -> tuple[bool, str]:
        try:
            client = genai_client.Client(api_key=api_key)
            client.models.list()
            return True, ""
        except Exception as e:
            return False, str(e)
