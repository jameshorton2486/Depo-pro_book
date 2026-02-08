from __future__ import annotations

import base64
from pathlib import Path

from openai import OpenAI

from agents.base_agent import BaseAgent


class ImageGenerator(BaseAgent):
    def generate_images(self, manifest: list[dict], chapter_dir: Path) -> list[Path]:
        if not manifest:
            return []

        output_dir = chapter_dir / "graphics"
        output_dir.mkdir(parents=True, exist_ok=True)

        client = OpenAI(api_key=self.config.openai_api_key)
        created = []

        for item in manifest:
            prompt = item.get("prompt", "").strip()
            file_name = item.get("file", f"{item.get('id', 'graphic')}.png")
            target_path = output_dir / file_name
            if target_path.exists():
                created.append(target_path)
                continue

            def _call():
                return client.images.generate(
                    model=self.config.image_model,
                    prompt=prompt,
                    n=1,
                    size=self.config.image_size,
                    quality=self.config.image_quality,
                    background=self.config.image_background,
                    output_format=self.config.image_format,
                )

            try:
                response = self._call_with_retry(_call, "graphics", int(item.get("section", 0)))
                payload = response.data[0].b64_json
                target_path.write_bytes(base64.b64decode(payload))
                self._log_api(self.config.image_model, "graphics", int(item.get("section", 0)), 0, 0, 0.0, True)
                created.append(target_path)
            except Exception as exc:
                self._log_api(self.config.image_model, "graphics", int(item.get("section", 0)), 0, 0, 0.0, False, str(exc))
                raise

        return created
