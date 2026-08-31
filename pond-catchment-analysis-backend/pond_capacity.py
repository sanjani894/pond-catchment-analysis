def estimate_pond_storage(
    estimated_runoff_volume_m3,
    storage_fraction=0.30
):
    """
    Estimate a target pond storage volume from
    the estimated runoff volume.

    This is a planning estimate, not the actual
    physical storage capacity of a designed pond.

    Parameters:
        estimated_runoff_volume_m3:
            Estimated runoff entering the catchment.

        storage_fraction:
            Fraction of estimated runoff used as
            the target storage volume.

    Returns:
        Dictionary containing storage estimate.
    """

    if estimated_runoff_volume_m3 < 0:
        raise ValueError(
            "Runoff volume cannot be negative"
        )

    if not 0 < storage_fraction <= 1:
        raise ValueError(
            "Storage fraction must be greater than 0 "
            "and less than or equal to 1"
        )

    storage_volume_m3 = (
        estimated_runoff_volume_m3
        * storage_fraction
    )

    return {
    "estimated_runoff_volume_m3": float(
        estimated_runoff_volume_m3
    ),
    "assumed_storage_fraction": float(
        storage_fraction
    ),
    "estimated_available_storage_m3": float(
        storage_volume_m3
    )
}