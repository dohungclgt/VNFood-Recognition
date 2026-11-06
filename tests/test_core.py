import io
import unittest
from PIL import Image
from core.gemini_handler import _normalize_box, normalize_result, _retryable
from core.image_tools import draw_bounding_boxes
from core.utils import get_cache_key

class RecognitionTests(unittest.TestCase):
    def test_multiple_dishes_preserved(self):
        result = normalize_result([{"food_name": "Phở", "confidence": 90, "bounding_box": [10, 20, 200, 300]},
                                  {"food_name": "Bún", "confidence": 70, "bounding_box": [300, 50, 900, 900]}])
        self.assertEqual(len(result["foods"]), 2)
    def test_legacy(self):
        result = normalize_result({"food_name": "Phở", "bounding_box": {"x": 100, "y": 200, "width": 200, "height": 300}})
        self.assertEqual(result["foods"][0]["bounding_box"], [200., 100., 500., 300.])
    def test_bad_boxes(self):
        for box in ([10, 20, 10, 80], [0, 2, 500, 1200], [float('nan'), 0, 200, 100], []):
            self.assertIsNone(_normalize_box(box))
    def test_empty_result(self):
        self.assertEqual(normalize_result({"foods": []}), {"foods": []})
    def test_duplicate_names(self):
        self.assertEqual(len(normalize_result({"foods": [{"food_name":"Phở"}, {"food_name":"phở"}]})["foods"]), 1)
    def test_bounding_boxes_render(self):
        b = io.BytesIO()
        Image.new("RGB", (200, 100), "white").save(b, format="JPEG")
        result = draw_bounding_boxes(b.getvalue(), [{"bounding_box": [0, 0, 500, 500]}, {"bounding_box": None}])
        self.assertEqual(result.size, (200, 100))
    def test_cache_changes_by_prompt(self):
        k1 = get_cache_key(b"img", "North", "English", "model", "multi-v1")
        k2 = get_cache_key(b"img", "North", "English", "model", "multi-v2")
        self.assertNotEqual(k1, k2)
    def test_invalid_payload(self):
        self.assertIn("error", normalize_result({"foods": "not a list"}))
        self.assertIn("error", normalize_result(None))
    def test_confidence_clamping(self):
        result = normalize_result({"foods": [{"food_name": "Phở", "confidence": 300}]})
        self.assertEqual(result["foods"][0]["confidence"], 100.0)
    def test_retry_logic(self):
        class Error(Exception):
            def __init__(self, code): self.code = code
        self.assertTrue(_retryable(Error(429)))
        self.assertTrue(_retryable(Error(503)))
        self.assertFalse(_retryable(Error(404)))
        self.assertFalse(_retryable(Error(403)))

if __name__ == "__main__": unittest.main()

class RichDetailsTests(unittest.TestCase):
    def test_rich_fields_are_preserved(self):
        data = normalize_result({"foods":[{
            "food_name":"Bún chả", "description":"Thịt nướng với bún",
            "origin_note":"Hà Nội", "taste_texture":"Mặn ngọt",
            "ingredients":["Bún", "Thịt lợn"], "cooking_steps":["Ướp thịt", "Nướng chín"],
            "serving_tips":["Ăn với rau"], "pairings":["Nước mắm"],
            "dietary_notes":"Có thể chứa nước mắm"
        }]})
        dish = data["foods"][0]
        self.assertEqual(dish["ingredients"], ["Bún", "Thịt lợn"])
        self.assertEqual(len(dish["cooking_steps"]), 2)
        self.assertEqual(dish["origin_note"], "Hà Nội")

    def test_legacy_dish_keeps_empty_new_fields(self):
        dish = normalize_result({"food_name":"Phở", "how_to_cook":"Nấu nước dùng"})["foods"][0]
        self.assertEqual(dish["cooking_steps"], [])
        self.assertEqual(dish["how_to_cook"], "Nấu nước dùng")

    def test_bad_ai_list_values_handled(self):
        dish = normalize_result({"food_name":"Phở", "ingredients":"not list", "cooking_steps":[None, 2, "Luộc bánh phở"]})["foods"][0]
        self.assertEqual(dish["ingredients"], [])
        self.assertEqual(dish["cooking_steps"], ["Luộc bánh phở"])

    def test_theme_query_roundtrip(self):
        from core.preferences import theme_from_query, theme_to_query
        self.assertEqual(theme_from_query(theme_to_query("Tối")), "Tối")
        self.assertEqual(theme_from_query(theme_to_query("Sáng")), "Sáng")
        self.assertEqual(theme_from_query("nonsense"), "Sáng")
