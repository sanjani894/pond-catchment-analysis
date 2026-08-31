import numpy as np


# D8 neighbor directions.
# Each tuple contains:
# (row_change, column_change)
DIRECTIONS = [
    (-1, 0),   # North
    (-1, 1),   # North-East
    (0, 1),    # East
    (1, 1),    # South-East
    (1, 0),    # South
    (1, -1),   # South-West
    (0, -1),   # West
    (-1, -1)   # North-West
]


def calculate_flow_direction(elevation_grid, cell_width_m, cell_height_m):
    """
    Calculate the D8 flow direction for an elevation grid.

    Each cell flows toward the neighboring cell with the
    steepest downward slope.

    Returns:
        A grid containing the direction index for each cell.
        -1 means no lower neighboring cell was found.
    """

    rows, columns = elevation_grid.shape

    flow_direction = np.full(
        (rows, columns),
        -1,
        dtype=int
    )

    for row in range(rows):
        for column in range(columns):

            current_elevation = elevation_grid[row, column]

            if np.isnan(current_elevation):
                continue

            best_direction = -1
            best_slope = 0.0

            for direction_index, (dr, dc) in enumerate(DIRECTIONS):

                neighbor_row = row + dr
                neighbor_column = column + dc

                # Skip neighbors outside the grid.
                if (
                    neighbor_row < 0
                    or neighbor_row >= rows
                    or neighbor_column < 0
                    or neighbor_column >= columns
                ):
                    continue

                neighbor_elevation = elevation_grid[
                    neighbor_row,
                    neighbor_column
                ]

                if np.isnan(neighbor_elevation):
                    continue

                elevation_drop = (
                    current_elevation - neighbor_elevation
                )

                if elevation_drop <= 0:
                    continue

                # Calculate horizontal distance.
                if dr != 0 and dc != 0:
                    distance = np.sqrt(
                        cell_width_m ** 2
                        + cell_height_m ** 2
                    )
                elif dc != 0:
                    distance = cell_width_m
                else:
                    distance = cell_height_m

                slope = elevation_drop / distance

                if slope > best_slope:
                    best_slope = slope
                    best_direction = direction_index

            flow_direction[row, column] = best_direction

    return flow_direction



def calculate_flow_accumulation(flow_direction):
    """
    Calculate the number of upstream cells contributing
    to each cell.

    Parameters:
        flow_direction: D8 flow-direction grid.

    Returns:
        A grid containing flow accumulation values.
    """

    rows, columns = flow_direction.shape

    accumulation = np.ones(
        (rows, columns),
        dtype=float
    )

    # Count how many cells flow into each cell.
    incoming = [
        [] for _ in range(rows * columns)
    ]

    for row in range(rows):
        for column in range(columns):

            direction = flow_direction[row, column]

            if direction < 0:
                continue

            dr, dc = DIRECTIONS[direction]

            next_row = row + dr
            next_column = column + dc

            if (
                next_row < 0
                or next_row >= rows
                or next_column < 0
                or next_column >= columns
            ):
                continue

            current_index = row * columns + column
            next_index = next_row * columns + next_column

            incoming[next_index].append(
                current_index
            )

    # Process cells from upstream toward downstream.
    processed = set()

    def accumulate(index):
        if index in processed:
            return accumulation[
                index // columns,
                index % columns
            ]

        row = index // columns
        column = index % columns

        total = 1.0

        for upstream_index in incoming[index]:
            total += accumulate(upstream_index)

        accumulation[row, column] = total
        processed.add(index)

        return total

    for index in range(rows * columns):
        accumulate(index)

    return accumulation


def delineate_catchment(
    flow_direction,
    outlet_row,
    outlet_column,
    cell_width_m,
    cell_height_m
):
    """
    Identify all cells that eventually drain into
    the selected outlet cell.

    Returns:
        Dictionary containing the catchment mask
        and estimated catchment area.
    """

    rows, columns = flow_direction.shape

    catchment = np.zeros(
        (rows, columns),
        dtype=bool
    )

    catchment[outlet_row, outlet_column] = True

    changed = True

    while changed:
        changed = False

        for row in range(rows):
            for column in range(columns):

                if catchment[row, column]:
                    continue

                direction = flow_direction[row, column]

                if direction < 0:
                    continue

                dr, dc = DIRECTIONS[direction]

                next_row = row + dr
                next_column = column + dc

                if (
                    next_row < 0
                    or next_row >= rows
                    or next_column < 0
                    or next_column >= columns
                ):
                    continue

                if catchment[next_row, next_column]:
                    catchment[row, column] = True
                    changed = True

    cell_count = int(np.sum(catchment))

    cell_area_m2 = (
        cell_width_m * cell_height_m
    )

    area_m2 = (
        cell_count * cell_area_m2
    )

    area_hectares = area_m2 / 10000.0

    return {
        "mask": catchment,
        "cell_count": cell_count,
        "cell_area_m2": float(cell_area_m2),
        "area_m2": float(area_m2),
        "area_hectares": float(area_hectares)
    }