import unittest
from checkmate.quality import classify_quality, QualityLevel


class TestQuality(unittest.TestCase):
    def test_excellent_quality(self):
        result = classify_quality(-70, 15)
        self.assertEqual(result.rssi, QualityLevel.EXCELLENT)
        self.assertEqual(result.snr, QualityLevel.EXCELLENT)
        self.assertEqual(result.overall, QualityLevel.EXCELLENT)

    def test_very_good_quality(self):
        result = classify_quality(-85, 8)
        self.assertEqual(result.rssi, QualityLevel.GOOD)
        self.assertEqual(result.snr, QualityLevel.GOOD)
        self.assertEqual(result.overall, QualityLevel.VERY_GOOD)

    def test_good_quality(self):
        result = classify_quality(-95, 3)
        self.assertEqual(result.rssi, QualityLevel.GOOD)
        self.assertEqual(result.snr, QualityLevel.FAIR)
        self.assertEqual(result.overall, QualityLevel.GOOD)

    def test_fair_good_quality(self):
        result = classify_quality(-105, 6)
        self.assertEqual(result.rssi, QualityLevel.FAIR)
        self.assertEqual(result.snr, QualityLevel.GOOD)
        self.assertEqual(result.overall, QualityLevel.GOOD)

    def test_poor_quality(self):
        result = classify_quality(-115, -7)
        self.assertEqual(result.rssi, QualityLevel.POOR)
        self.assertEqual(result.snr, QualityLevel.VERY_POOR)
        self.assertEqual(result.overall, QualityLevel.POOR)

    def test_very_poor_quality(self):
        result = classify_quality(-135, -12)
        self.assertEqual(result.rssi, QualityLevel.VERY_POOR)
        self.assertEqual(result.snr, QualityLevel.VERY_POOR)
        self.assertEqual(result.overall, QualityLevel.VERY_POOR)


if __name__ == "__main__":
    unittest.main()
