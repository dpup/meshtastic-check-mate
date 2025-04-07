"""
Signal quality assessment module for Meshtastic radio communications.

This module provides tools to evaluate radio signal quality based on RSSI and SNR measurements.
Quality levels are classified from Excellent to Very Poor according to industry standard thresholds.
"""
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple


class QualityLevel(str, Enum):
    """
    Signal quality classification levels.
    
    Standard radio signal quality levels ranging from excellent to very poor,
    used to describe both individual metrics (RSSI, SNR) and overall quality.
    """
    EXCELLENT = "Excellent"
    VERY_GOOD = "Very Good"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"
    VERY_POOR = "Very Poor"


# RSSI thresholds in dBm
# Better (less negative) values indicate stronger signal
RSSI_THRESHOLDS: List[Tuple[float, QualityLevel]] = [
    (-80, QualityLevel.EXCELLENT),    # > -80 dBm: Excellent
    (-100, QualityLevel.GOOD),        # -80 to -100 dBm: Good
    (-110, QualityLevel.FAIR),        # -100 to -110 dBm: Fair
    (-120, QualityLevel.POOR),        # -110 to -120 dBm: Poor
    (float('-inf'), QualityLevel.VERY_POOR),  # < -120 dBm: Very Poor
]

# SNR thresholds in dB
# Higher values indicate better signal-to-noise ratio
SNR_THRESHOLDS: List[Tuple[float, QualityLevel]] = [
    (10, QualityLevel.EXCELLENT),     # > 10 dB: Excellent
    (5, QualityLevel.GOOD),           # 5 to 10 dB: Good
    (0, QualityLevel.FAIR),           # 0 to 5 dB: Fair
    (-5, QualityLevel.POOR),          # -5 to 0 dB: Poor
    (float('-inf'), QualityLevel.VERY_POOR),  # < -5 dB: Very Poor
]


@dataclass
class SignalQuality:
    """
    Container for signal quality assessments.
    
    Holds quality levels for RSSI, SNR and the computed overall quality.
    """
    rssi: QualityLevel
    snr: QualityLevel
    overall: QualityLevel


def classify_metric(value: float, thresholds: List[Tuple[float, QualityLevel]]) -> QualityLevel:
    """
    Classify a metric value based on provided thresholds.
    
    Args:
        value: The metric value to classify
        thresholds: List of (threshold, quality_level) tuples in descending order
        
    Returns:
        The appropriate quality level for the given value
    """
    for threshold, quality in thresholds:
        if value > threshold:
            return quality
    return QualityLevel.VERY_POOR


def classify_quality(rssi: float, snr: float) -> SignalQuality:
    """
    Classify radio signal quality based on RSSI and SNR values.
    
    This function evaluates both RSSI (signal strength) and SNR (signal-to-noise ratio)
    metrics to determine overall signal quality according to industry standard thresholds.
    
    Args:
        rssi: Received Signal Strength Indicator in dBm (typically negative)
        snr: Signal-to-Noise Ratio in dB
        
    Returns:
        SignalQuality object containing assessments for RSSI, SNR and overall quality
    """
    # Classify individual metrics
    rssi_quality = classify_metric(rssi, RSSI_THRESHOLDS)
    snr_quality = classify_metric(snr, SNR_THRESHOLDS)

    # Determine overall classification
    if (
        rssi_quality in [QualityLevel.EXCELLENT, QualityLevel.GOOD]
        and snr_quality == QualityLevel.EXCELLENT
    ):
        overall_quality = QualityLevel.EXCELLENT
    elif (
        rssi_quality in [QualityLevel.EXCELLENT, QualityLevel.GOOD]
        and snr_quality == QualityLevel.GOOD
    ):
        overall_quality = QualityLevel.VERY_GOOD
    elif (
        rssi_quality == QualityLevel.GOOD
        and snr_quality in [QualityLevel.GOOD, QualityLevel.FAIR]
    ) or (rssi_quality == QualityLevel.FAIR and snr_quality == QualityLevel.GOOD):
        overall_quality = QualityLevel.GOOD
    elif rssi_quality == QualityLevel.FAIR and snr_quality == QualityLevel.FAIR:
        overall_quality = QualityLevel.FAIR
    elif rssi_quality == QualityLevel.POOR or snr_quality == QualityLevel.POOR:
        overall_quality = QualityLevel.POOR
    else:
        overall_quality = QualityLevel.VERY_POOR

    return SignalQuality(
        rssi=rssi_quality,
        snr=snr_quality,
        overall=overall_quality,
    )
