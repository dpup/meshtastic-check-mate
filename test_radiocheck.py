import unittest
from radiocheck import getResponse
from quality import QualityLevel


class TestResponses(unittest.TestCase):
    def test_excellent_quality(self):
        result = getResponse(QualityLevel.EXCELLENT, "Alice", "London")
        self.assertIn(
            result,
            [
                "Alice, reading you 5 by 5 from London",
                "Good copy Alice, from London",
                "Ack Alice, got a strong signal from London",
            ],
        )

    def test_very_good_quality(self):
        result = getResponse(QualityLevel.VERY_GOOD, "Bob", "New York")
        self.assertIn(
            result,
            [
                "Bob, reading you 5 by 5 from New York",
                "Good copy Bob, from New York",
                "Ack Bob, got a strong signal from New York",
            ],
        )

    def test_good_quality(self):
        result = getResponse(QualityLevel.GOOD, "Charlie", "Paris")
        self.assertIn(
            result,
            [
                "Charlie, copy from Paris",
                "Ack Charlie from Paris",
                "Charlie, got you here in Paris",
            ],
        )

    def test_fair_quality(self):
        result = getResponse(QualityLevel.FAIR, "Dave", "Tokyo")
        self.assertIn(
            result,
            [
                "Dave, copy from Tokyo",
                "Ack Dave from Tokyo",
                "Dave, got you here in Tokyo",
            ],
        )

    def test_poor_quality(self):
        result = getResponse(QualityLevel.POOR, "Eve", "Sydney")
        self.assertIn(
            result,
            [
                "Copy Eve, weak signal from Sydney",
                "Eve, barely got you from Sydney",
                "Ack Eve, but weak signal from Sydney",
            ],
        )

    def test_very_poor_quality(self):
        result = getResponse(QualityLevel.VERY_POOR, "Frank", "Berlin")
        self.assertIn(
            result,
            [
                "Copy Frank, weak signal from Berlin",
                "Frank, barely got you from Berlin",
                "Ack Frank, but weak signal from Berlin",
            ],
        )

    def test_unknown_quality(self):
        result = getResponse("UNKNOWN", "Unknown", "Unknown")
        self.assertEqual(result, "Hola!")


if __name__ == "__main__":
    unittest.main()
