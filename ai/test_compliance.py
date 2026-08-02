import unittest

from ai.compliance import SensitiveCheckUnavailable, check_sensitive


class ComplianceTest(unittest.TestCase):
    def test_unavailable_service_fails_closed(self):
        class Response:
            status_code = 503

        def post(*_args, **_kwargs):
            return Response()

        with self.assertRaises(SensitiveCheckUnavailable):
            check_sensitive("paper", post=post)

    def test_explicit_sensitive_decision_is_returned(self):
        class Response:
            status_code = 200

            @staticmethod
            def json():
                return {"sensitive": True}

        def post(*_args, **_kwargs):
            return Response()

        self.assertTrue(check_sensitive("paper", post=post))

    def test_non_boolean_decision_is_rejected(self):
        class Response:
            status_code = 200

            @staticmethod
            def json():
                return {"sensitive": "false"}

        with self.assertRaises(SensitiveCheckUnavailable):
            check_sensitive("paper", post=lambda *_args, **_kwargs: Response())


if __name__ == "__main__":
    unittest.main()
