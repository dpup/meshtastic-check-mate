from enum import Enum
from dataclasses import dataclass


class QualityLevel(str, Enum):
    EXCELLENT = "Excellent"
    VERY_GOOD = "Very Good"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"
    VERY_POOR = "Very Poor"


@dataclass
class SignalQuality:
    rssi: QualityLevel
    snr: QualityLevel
    overall: QualityLevel


def classifyQuality(rssi: float, snr: float) -> SignalQuality:
    """Classify the RSSI and SNR values into quality levels."""
    # Classify RSSI
    if rssi > -80:
        rssiQuality = QualityLevel.EXCELLENT
    elif -80 >= rssi > -100:
        rssiQuality = QualityLevel.GOOD
    elif -100 >= rssi > -110:
        rssiQuality = QualityLevel.FAIR
    elif -110 >= rssi > -120:
        rssiQuality = QualityLevel.POOR
    else:
        rssiQuality = QualityLevel.VERY_POOR

    # Classify SNR
    if snr > 10:
        snrQuality = QualityLevel.EXCELLENT
    elif 10 >= snr > 5:
        snrQuality = QualityLevel.GOOD
    elif 5 >= snr > 0:
        snrQuality = QualityLevel.FAIR
    elif 0 >= snr > -5:
        snrQuality = QualityLevel.POOR
    else:
        snrQuality = QualityLevel.VERY_POOR

    # Overall classification
    if (
        rssiQuality in [QualityLevel.EXCELLENT, QualityLevel.GOOD]
        and snrQuality == QualityLevel.EXCELLENT
    ):
        overallQuality = QualityLevel.EXCELLENT
    elif (
        rssiQuality in [QualityLevel.EXCELLENT, QualityLevel.GOOD]
        and snrQuality == QualityLevel.GOOD
    ):
        overallQuality = QualityLevel.VERY_GOOD
    elif (
        rssiQuality == QualityLevel.GOOD
        and snrQuality in [QualityLevel.GOOD, QualityLevel.FAIR]
    ) or (rssiQuality == QualityLevel.FAIR and snrQuality == QualityLevel.GOOD):
        overallQuality = QualityLevel.GOOD
    elif rssiQuality == QualityLevel.FAIR and snrQuality == QualityLevel.FAIR:
        overallQuality = QualityLevel.FAIR
    elif rssiQuality == QualityLevel.POOR or snrQuality == QualityLevel.POOR:
        overallQuality = QualityLevel.POOR
    else:
        overallQuality = QualityLevel.VERY_POOR

    return SignalQuality(
        rssi=rssiQuality,
        snr=snrQuality,
        overall=overallQuality,
    )
