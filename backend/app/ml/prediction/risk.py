def calculate_risk(
    probability: float
) -> str:

    if probability >= 0.70:

        return "HIGH"


    if probability >= 0.40:

        return "MEDIUM"


    return "LOW"