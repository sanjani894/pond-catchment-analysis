import numpy as np
from pyproj import Transformer
from scipy.interpolate import griddata


def build_dem(contours, bounds, grid_size=100):
    """
    Build a regular elevation grid from contour coordinates.

    Parameters:
        contours: list of contour dictionaries containing elevation
                   and coordinate points.
        bounds: geographic bounds of the contour map.
        grid_size: number of cells along each grid dimension.

    Returns:
        Dictionary containing the elevation grid and grid information.
    """

    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:3857",
        always_xy=True
    )

    points = []
    elevations = []

    # Reduce the number of interpolation points while preserving
    # information from every contour elevation.
    max_points = 15000

    points_per_contour = max(
        1,
        max_points // len(contours)
    )

    for contour in contours:
        elevation = contour["elevation"]
        coordinates = contour["coordinates"]

        if not coordinates:
            continue

        sample_count = min(
            points_per_contour,
            len(coordinates)
        )

        indices = np.linspace(
            0,
            len(coordinates) - 1,
            sample_count,
            dtype=int
        )

        for index in indices:
            longitude, latitude = coordinates[index]

            x, y = transformer.transform(
                longitude,
                latitude
            )

            points.append((x, y))
            elevations.append(elevation)

    if not points:
        raise ValueError(
            "No contour points available for terrain generation"
        )

    points = np.array(points)
    elevations = np.array(elevations)

    x_min = points[:, 0].min()
    x_max = points[:, 0].max()
    y_min = points[:, 1].min()
    y_max = points[:, 1].max()

    x_grid = np.linspace(
        x_min,
        x_max,
        grid_size
    )

    y_grid = np.linspace(
        y_min,
        y_max,
        grid_size
    )

    grid_x, grid_y = np.meshgrid(
        x_grid,
        y_grid
    )

    elevation_grid = griddata(
        points,
        elevations,
        (grid_x, grid_y),
        method="linear"
    )

    # Fill areas outside the linear interpolation region.
    missing = np.isnan(elevation_grid)

    if np.any(missing):
        elevation_grid[missing] = griddata(
            points,
            elevations,
            (grid_x[missing], grid_y[missing]),
            method="nearest"
        )

    cell_width = (
        (x_max - x_min)
        / (grid_size - 1)
    )

    cell_height = (
        (y_max - y_min)
        / (grid_size - 1)
    )

    return {
    "elevation_grid": elevation_grid,
    "grid_size": grid_size,
    "cell_width_m": cell_width,
    "cell_height_m": cell_height,
    "min_elevation": float(
        np.min(elevation_grid)
    ),
    "max_elevation": float(
        np.max(elevation_grid)
    ),
    "x_grid": x_grid,
    "y_grid": y_grid,
    "transformer": transformer
}