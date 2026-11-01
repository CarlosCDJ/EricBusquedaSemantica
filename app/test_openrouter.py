"""Offline tests: the OpenRouter API is simulated; no credentials are needed."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import numpy as np
from PIL import Image
import pymupdf

import search


class FakeResponse:
    def __enter__(self):
        return io.BytesIO(json.dumps({"data": [{"embedding": [3.0, 4.0]}]}).encode())

    def __exit__(self, *args):
        pass


class OpenRouterTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"})
        self.env.start()
        self.model = search.Model()

    def tearDown(self):
        self.env.stop()

    def test_requests_for_query_document_and_image(self):
        requests = []

        def respond(request, timeout):
            requests.append(json.loads(request.data))
            return FakeResponse()

        with tempfile.TemporaryDirectory() as tmp, patch.object(search, "urlopen", side_effect=respond):
            image = Path(tmp) / "example.jpg"
            Image.new("RGB", (10, 10)).save(image)
            query = self.model.embed_query("factura")
            document = self.model.embed_documents(["texto"])
            picture = self.model.embed_images([str(image)])
        np.testing.assert_allclose(query, [0.6, 0.8])
        self.assertEqual(document.shape, (1, 2))
        self.assertEqual(picture.shape, (1, 2))
        self.assertEqual([r["input_type"] for r in requests], ["query", "passage", "passage"])
        self.assertTrue(all(r["model"] == search.MODEL_ID for r in requests))
        self.assertTrue(requests[2]["input"][0]["content"][0]["image_url"]["url"].startswith("data:image/jpeg;base64,"))

    def test_errors_do_not_expose_provider_response(self):
        error = HTTPError(search.EMBEDDINGS_URL, 401, "error", {}, io.BytesIO(b"test-key"))
        with patch.object(search, "urlopen", side_effect=error):
            with self.assertRaises(RuntimeError) as result:
                self.model.embed_query("test")
        self.assertIn("401", str(result.exception))
        self.assertNotIn("test-key", str(result.exception))

    def test_index_search_reuse_and_incompatible_index(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(search, "urlopen", return_value=FakeResponse()):
            root = Path(tmp)
            folder = root / "examples"
            folder.mkdir()
            Image.new("RGB", (20, 20)).save(folder / "photo.jpg")
            with pymupdf.open() as pdf:
                page = pdf.new_page()
                page.insert_text((72, 72), "Example invoice 2026-0931")
                pdf.save(folder / "example.pdf")
            with patch.object(search, "INDEXES", root / "indexes"):
                search.INDEXES.mkdir()
                index = search.Index()
                index.build(folder, self.model)
                self.assertEqual(index.progress["phase"], "Done")
                self.assertGreaterEqual(len(index.rows), 3)
                self.assertEqual(len(index.rank(self.model.embed_query("invoice"), 10)), 2)
                self.assertEqual(len(index.rank(self.model.embed_images([str(folder / "photo.jpg")])[0], 10)), 2)
                self.assertTrue(search.Index.previous(search.index_dir(folder)))
                data_path = search.index_dir(folder) / "index.json"
                data = json.loads(data_path.read_text(encoding="utf-8"))
                data["settings"]["model"] = "google/embeddinggemma-2"
                data_path.write_text(json.dumps(data), encoding="utf-8")
                self.assertFalse(search.Index().load(folder))
                self.assertFalse(search.Index.previous(search.index_dir(folder)))

    def test_missing_key(self):
        with patch.dict(os.environ, {}, clear=True):
            model = search.Model()
        self.assertFalse(model.ready())
        with self.assertRaises(RuntimeError):
            model.embed_query("test")

    def test_small_demo_with_simulated_api(self):
        folder = Path(__file__).resolve().parent.parent / "demo-pequena"
        with tempfile.TemporaryDirectory() as tmp, patch.object(search, "urlopen", return_value=FakeResponse()):
            with patch.object(search, "INDEXES", Path(tmp)):
                index = search.Index()
                index.build(folder, self.model)
                self.assertEqual(index.progress["phase"], "Done", index.progress.get("error"))
                self.assertEqual(index.stats["photos"], 2)
                self.assertEqual(index.stats["screenshots"], 2)
                self.assertEqual(index.stats["pdfs"], 3)
                self.assertTrue(index.rank(self.model.embed_query("factura"), 10))


if __name__ == "__main__":
    unittest.main()
