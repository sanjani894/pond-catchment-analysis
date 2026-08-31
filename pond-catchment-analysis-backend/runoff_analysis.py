def calculate_runoff_volume(
    rainfall_mm,
    catchment_area_m2,
    runoff_coefficient=0.5
):
    """
    Estimate runoff volume from rainfall and catchment area.

    Parameters:
        rainfall_mm:
            Rainfall depth in millimetres.

        catchment_area_m2:
            Catchment area in square metres.

        runoff_coefficient:
            Fraction of rainfall that becomes surface runoff.
            Must be between 0 and 1.

    Returns:
        Dictionary containing runoff calculation details.
    """

    if rainfall_mm < 0:
        raise ValueError(
            "Rainfall cannot be negative"
        )

    if catchment_area_m2 <= 0:
        raise ValueError(
            "Catchment area must be greater than zero"
        )

    if not 0 <= runoff_coefficient <= 1:
        raise ValueError(
            "Runoff coefficient must be between 0 and 1"
        )

    rainfall_m = rainfall_mm / 1000.0

    rainfall_volume_m3 = (
        rainfall_m * catchment_area_m2
    )

    runoff_volume_m3 = (
        rainfall_volume_m3
        * runoff_coefficient
    )

    return {
        "rainfall_mm": float(rainfall_mm),
        "runoff_coefficient": float(
            runoff_coefficient
        ),
        "rainfall_volume_m3": float(
            rainfall_volume_m3
        ),
        "estimated_runoff_volume_m3": float(
            runoff_volume_m3
        )
    }