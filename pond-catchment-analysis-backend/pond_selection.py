import numpy as np


def normalize(values):
    """Normalize an array to the range 0 to 1."""

    minimum = np.min(values)
    maximum = np.max(values)

    if maximum == minimum:
        return np.zeros_like(values, dtype=float)

    return (values - minimum) / (maximum - minimum)


def calculate_suitability(
    elevation_grid,
    flow_accumulation,
    accumulation_weight=0.7,
    elevation_weight=0.3
):
    """
    Calculate suitability score for every terrain cell.

    Higher flow accumulation and lower elevation
    result in a higher suitability score.
    """

    valid = (
        ~np.isnan(elevation_grid)
        & ~np.isnan(flow_accumulation)
    )

    if not np.any(valid):
        raise ValueError(
            "No valid terrain cells available"
        )

    accumulation_score = normalize(
        flow_accumulation
    )

    elevation_score = 1.0 - normalize(
        elevation_grid
    )

    suitability = (
        accumulation_weight * accumulation_score
        + elevation_weight * elevation_score
    )

    suitability[~valid] = -np.inf

    return suitability


def _candidate_details(
    row,
    column,
    elevation_grid,
    flow_accumulation,
    suitability,
    x_grid,
    y_grid,
    transformer
):
    """Build details for one pond candidate."""

    x = x_grid[column]
    y = y_grid[row]

    longitude, latitude = transformer.transform(
        x,
        y,
        direction="INVERSE"
    )

    return {
        "row": int(row),
        "column": int(column),
        "latitude": float(latitude),
        "longitude": float(longitude),
        "elevation": float(
            elevation_grid[row, column]
        ),
        "flow_accumulation": float(
            flow_accumulation[row, column]
        ),
        "suitability_score": float(
            suitability[row, column]
        )
    }


def select_pond_candidate(
    elevation_grid,
    flow_accumulation,
    x_grid,
    y_grid,
    transformer,
    accumulation_weight=0.7,
    elevation_weight=0.3
):
    """
    Select the single best terrain-derived
    pond candidate.
    """

    suitability = calculate_suitability(
        elevation_grid=elevation_grid,
        flow_accumulation=flow_accumulation,
        accumulation_weight=accumulation_weight,
        elevation_weight=elevation_weight
    )

    candidate_row, candidate_column = np.unravel_index(
        np.argmax(suitability),
        suitability.shape
    )

    return _candidate_details(
        candidate_row,
        candidate_column,
        elevation_grid,
        flow_accumulation,
        suitability,
        x_grid,
        y_grid,
        transformer
    )


def select_pond_candidates(
    elevation_grid,
    flow_accumulation,
    x_grid,
    y_grid,
    transformer,
    number_of_candidates=5,
    minimum_distance_cells=10,
    accumulation_weight=0.7,
    elevation_weight=0.3,
    water_checker=None
):
    """
    Select multiple distinct pond candidates.

    Candidates are ranked by suitability score.

    If water_checker is supplied, candidates that
    are inside or near existing water are rejected.
    """

    if not 2 <= number_of_candidates <= 5:
        raise ValueError(
            "number_of_candidates must be between 2 and 5"
        )

    suitability = calculate_suitability(
        elevation_grid=elevation_grid,
        flow_accumulation=flow_accumulation,
        accumulation_weight=accumulation_weight,
        elevation_weight=elevation_weight
    )

    candidate_positions = np.argwhere(
        np.isfinite(suitability)
    )

    candidate_positions = sorted(
        candidate_positions,
        key=lambda position: suitability[
            position[0],
            position[1]
        ],
        reverse=True
    )

    selected = []

    for position in candidate_positions:

        row = int(position[0])
        column = int(position[1])

        # Convert grid coordinates to latitude/longitude.
        x = x_grid[column]
        y = y_grid[row]

        longitude, latitude = transformer.transform(
            x,
            y,
            direction="INVERSE"
        )

                # Check existing or nearby water.
        near_water = False

        if water_checker is not None:
            near_water = water_checker(
                latitude,
                longitude
            )

            if near_water:
                continue

        # Keep candidates spatially separated.
        too_close = False

        for existing in selected:

            row_difference = (
                row - existing["row"]
            )

            column_difference = (
                column - existing["column"]
            )

            distance = np.sqrt(
                row_difference ** 2
                + column_difference ** 2
            )

            if distance < minimum_distance_cells:
                too_close = True
                break

        if too_close:
            continue

        candidate = _candidate_details(
            row,
            column,
            elevation_grid,
            flow_accumulation,
            suitability,
            x_grid,
            y_grid,
            transformer
        )

        candidate["water_check"] = {
            "inside_or_near_existing_water": bool(
                near_water
            )
        }

        selected.append(candidate)

        if len(selected) == number_of_candidates:
            break

    return selected