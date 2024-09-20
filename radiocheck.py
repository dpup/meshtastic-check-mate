import random
from quality import QualityLevel


responses = {
    QualityLevel.EXCELLENT: [
        "{name}, reading you 5 by 5 from {loc}",
        "Good copy {name}, from {loc}",
        "Ack {name}, got a strong signal from {loc}",
    ],
    QualityLevel.VERY_GOOD: [
        "reading you 5 by 5 {name} from {loc}",
        "Good copy {name}, from {loc}",
        "Ack {name}, got a strong signal from {loc}",
    ],
    QualityLevel.GOOD: [
        "{name}, copy from {loc}",
        "Ack {name} from {loc}",
        "{name}, got you here in {loc}",
    ],
    QualityLevel.FAIR: [
        "{name}, copy from {loc}",
        "Ack {name} from {loc}",
        "{name}, got you here in {loc}",
    ],
    QualityLevel.POOR: [
        "Copy {name}, weak signal from {loc}",
        "{name}, barely got you from {loc}",
        "Ack {name}, but weak signal from {loc}",
    ],
    QualityLevel.VERY_POOR: [
        "Copy {name}, weak signal from {loc}",
        "{name}, barely got you from {loc}",
        "Ack {name}, but weak signal from {loc}",
    ],
}


def getResponse(qualityLevel, name, loc):
    if qualityLevel not in responses:
        return "Hola!"

    response = random.choice(responses[qualityLevel])
    return response.format(name=name, loc=loc)
