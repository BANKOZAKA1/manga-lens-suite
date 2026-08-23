import io
import json
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from PIL import Image

import app as gateway


def png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (32, 48), "white").save(output, "PNG")
    return output.getvalue()


class GatewayTests(unittest.TestCase):
    def test_default_config_targets_thai(self):
        options = gateway.parse_page_options("{}")
        config = gateway.build_mit_config(options)
        self.assertEqual(config["translator"]["target_lang"], "THA")
        self.assertEqual(config["inpainter"]["inpainter"], "lama_large")
        self.assertEqual(config["render"]["renderer"], "manga2eng_pillow")
        self.assertEqual(config["render"]["direction"], "horizontal")

    def test_japanese_uses_manga_ocr(self):
        options = gateway.PageOptions(source_language="ja")
        self.assertEqual(gateway.build_mit_config(options)["ocr"]["ocr"], "mocr")

    def test_korean_uses_multilingual_ocr(self):
        options = gateway.PageOptions(source_language="ko")
        self.assertEqual(gateway.build_mit_config(options)["ocr"]["ocr"], "48px_ctc")

    def test_bad_target_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            gateway.parse_page_options(json.dumps({"target_language": "ENG"}))
        self.assertEqual(raised.exception.status_code, 422)

    def test_image_hash_and_validation(self):
        digest, image_format = gateway.validate_image(png_bytes())
        self.assertEqual(len(digest), 64)
        self.assertEqual(image_format, "png")

    def test_invalid_image_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            gateway.validate_image(b"not-an-image")
        self.assertEqual(raised.exception.status_code, 422)

    def test_pairing_token_required(self):
        with patch.dict(os.environ, {"MANGALENS_PAIRING_TOKEN": "test-secret"}, clear=False):
            self.assertEqual(gateway.settings.token(), "test-secret")

    def test_translategemma_prompt_detects_korean_and_uses_one_user_role(self):
        adapted = gateway.adapt_translategemma_payload(
            {
                "messages": [
                    {"role": "system", "content": "Keep dialogue concise."},
                    {"role": "user", "content": "이번에는 내가 반드시 지킬 거야!"},
                ]
            }
        )
        self.assertEqual(len(adapted["messages"]), 1)
        self.assertEqual(adapted["messages"][0]["role"], "user")
        self.assertIn("Korean (ko) to Thai (th)", adapted["messages"][0]["content"])
        self.assertIn("Mandatory ambiguity rule", adapted["messages"][0]["content"])
        self.assertIn("never ทำตาม", adapted["messages"][0]["content"])
        self.assertIn("Mandatory terminology for this line", adapted["messages"][0]["content"])

    def test_explicit_korean_promise_does_not_force_protect(self):
        adapted = gateway.adapt_translategemma_payload(
            {"messages": [{"role": "user", "content": "이번에는 약속을 반드시 지킬 거야!"}]}
        )
        self.assertNotIn("Mandatory terminology for this line", adapted["messages"][0]["content"])
        self.assertIn("\n\n\n이번에는", adapted["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
