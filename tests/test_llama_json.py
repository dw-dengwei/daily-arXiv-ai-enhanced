import unittest


class TestLlamaJsonParsing(unittest.TestCase):
    def test_parse_strict_json_success(self):
        from ai.llama_json import parse_llm_json, ensure_ai_fields

        obj = parse_llm_json('{"tldr":"a","motivation":"b","method":"c","result":"d","conclusion":"e"}')
        self.assertEqual(obj["tldr"], "a")
        self.assertEqual(set(obj.keys()), {"tldr", "motivation", "method", "result", "conclusion"})
        self.assertEqual(ensure_ai_fields(obj), obj)

    def test_parse_extract_object_from_text(self):
        from ai.llama_json import parse_llm_json

        text = 'prefix {"tldr":"a","motivation":"b","method":"c","result":"d","conclusion":"e"} suffix'
        obj = parse_llm_json(text)
        self.assertEqual(obj["result"], "d")

    def test_parse_trailing_comma_repair(self):
        from ai.llama_json import parse_llm_json

        text = '{"tldr":"a","motivation":"b","method":"c","result":"d","conclusion":"e",}'
        obj = parse_llm_json(text)
        self.assertEqual(obj["conclusion"], "e")

    def test_ensure_missing_fields_filled(self):
        from ai.llama_json import ensure_ai_fields

        obj = ensure_ai_fields({"tldr": "a"})
        self.assertEqual(obj["tldr"], "a")
        self.assertEqual(obj["motivation"], "")
        self.assertEqual(obj["method"], "")
        self.assertEqual(obj["result"], "")
        self.assertEqual(obj["conclusion"], "")


if __name__ == "__main__":
    unittest.main()

