import numpy as np
import rasterio
import pystac_client
import planetary_computer
from rasterio.windows import from_bounds


CATALOG_URL = (
    "https://planetarycomputer.microsoft.com/api/stac/v1"
)


def calculate_ndwi(green_band, nir_band):
    """Calculate NDWI from Green and NIR bands."""

    green_band = green_band.astype(float)
    nir_band = nir_band.astype(float)

    denominator = green_band + nir_band

    ndwi = np.full(
        green_band.shape,
        np.nan,
        dtype=float
    )

    valid = denominator != 0

    ndwi[valid] = (
        (green_band[valid] - nir_band[valid])
        / denominator[valid]
    )

    return ndwi


def create_water_mask(
    green_band,
    nir_band,
    threshold=0.2
):
    """Create a water mask from NDWI."""

    ndwi = calculate_ndwi(
        green_band,
        nir_band
    )

    water_mask = (
        np.isfinite(ndwi)
        & (ndwi >= threshold)
    )

    return water_mask, ndwi


def find_best_sentinel_image(
    bbox,
    start_date="2025-01-01",
    end_date="2025-12-31",
    maximum_cloud_cover=20
):
    """Find the lowest-cloud Sentinel-2 L2A image."""

    catalog = pystac_client.Client.open(
        CATALOG_URL
    )

    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{start_date}/{end_date}",
        query={
            "eo:cloud_cover": {
                "lt": maximum_cloud_cover
            }
        }
    )

    items = list(search.items())

    if not items:
        raise ValueError(
            "No suitable Sentinel-2 images found"
        )

    best_item = min(
        items,
        key=lambda item: item.properties.get(
            "eo:cloud_cover",
            100
        )
    )

    return planetary_computer.sign(
        best_item
    )


def get_water_mask_from_satellite(
    bbox,
    start_date="2025-01-01",
    end_date="2025-12-31",
    maximum_cloud_cover=20,
    threshold=0.2
):
    """
    Read Sentinel-2 B03, B08 and SCL data
    for only the supplied bounding box.
    """

    item = find_best_sentinel_image(
        bbox=bbox,
        start_date=start_date,
        end_date=end_date,
        maximum_cloud_cover=maximum_cloud_cover
    )

    green_asset = item.assets.get("B03")
    nir_asset = item.assets.get("B08")
    scl_asset = item.assets.get("SCL")

    if green_asset is None:
        raise ValueError(
            "Sentinel-2 B03 asset not available"
        )

    if nir_asset is None:
        raise ValueError(
            "Sentinel-2 B08 asset not available"
        )

    if scl_asset is None:
        raise ValueError(
            "Sentinel-2 SCL asset not available"
        )

    from rasterio.warp import transform_bounds

    # -------------------------------------------------
    # Read B03 (Green)
    # -------------------------------------------------

    with rasterio.open(green_asset.href) as green_src:

        satellite_bbox = transform_bounds(
            "EPSG:4326",
            green_src.crs,
            bbox[0],
            bbox[1],
            bbox[2],
            bbox[3]
        )

        green_window = from_bounds(
            *satellite_bbox,
            transform=green_src.transform
        )

        green_window = (
            green_window
            .round_offsets()
            .round_lengths()
        )

        green = green_src.read(
            1,
            window=green_window
        )

        green_transform = (
            green_src.window_transform(
                green_window
            )
        )

        crs = green_src.crs

    # -------------------------------------------------
    # Read B08 (NIR)
    # -------------------------------------------------

    with rasterio.open(nir_asset.href) as nir_src:

        nir_window = from_bounds(
            *satellite_bbox,
            transform=nir_src.transform
        )

        nir_window = (
            nir_window
            .round_offsets()
            .round_lengths()
        )

        nir = nir_src.read(
            1,
            window=nir_window
        )

    # -------------------------------------------------
    # Calculate NDWI
    # -------------------------------------------------

    rows = min(
        green.shape[0],
        nir.shape[0]
    )

    columns = min(
        green.shape[1],
        nir.shape[1]
    )

    green = green[:rows, :columns]
    nir = nir[:rows, :columns]

    water_mask, ndwi = create_water_mask(
        green_band=green,
        nir_band=nir,
        threshold=threshold
    )

    # -------------------------------------------------
    # Read SCL (Scene Classification Layer)
    # -------------------------------------------------

    with rasterio.open(scl_asset.href) as scl_src:

        scl_window = from_bounds(
            *satellite_bbox,
            transform=scl_src.transform
        )

        scl_window = (
            scl_window
            .round_offsets()
            .round_lengths()
        )

        scl = scl_src.read(
            1,
            window=scl_window
        )
        scl_transform = scl_src.window_transform(
         scl_window
         )
   
        scl_crs = scl_src.crs

    # -------------------------------------------------
    # Create SCL water mask
    # -------------------------------------------------

    scl_water_mask = create_scl_water_mask(
        scl
    )

    return {
    "water_mask": water_mask,
    "scl_water_mask": scl_water_mask,
    "ndwi": ndwi,
    "transform": green_transform,
    "crs": crs,
    "scl_transform": scl_transform,
    "scl_crs": scl_crs,
    "image_id": item.id,
    "image_date": item.datetime,
    "cloud_cover": item.properties.get(
        "eo:cloud_cover"
    )
}


def create_scl_water_mask(scl_band):
    """
    Create a water mask using Sentinel-2
    Scene Classification Layer (SCL).

    Sentinel-2 SCL class 6 represents water.
    """

    return scl_band == 6


def is_water_location(
    latitude,
    longitude,
    water_mask,
    transform,
    crs
):
    """
    Check whether a geographic location falls
    inside a detected water pixel.
    """

    from rasterio.warp import transform as transform_coordinates

    x, y = transform_coordinates(
        "EPSG:4326",
        crs,
        [longitude],
        [latitude]
    )

    row, column = rasterio.transform.rowcol(
        transform,
        x[0],
        y[0]
    )

    row = int(row)
    column = int(column)

    if (
        row < 0
        or row >= water_mask.shape[0]
        or column < 0
        or column >= water_mask.shape[1]
    ):
        return False

    return bool(
        water_mask[row, column]
    )


def is_near_water(
    latitude,
    longitude,
    water_mask,
    transform,
    crs,
    buffer_pixels=2
):
    """
    Check whether a location is inside or close to
    a satellite-detected water area.

    buffer_pixels:
        Number of pixels around the candidate to inspect.
    """

    from rasterio.warp import transform as transform_coordinates

    x, y = transform_coordinates(
        "EPSG:4326",
        crs,
        [longitude],
        [latitude]
    )

    row, column = rasterio.transform.rowcol(
        transform,
        x[0],
        y[0]
    )

    row = int(row)
    column = int(column)

    rows, columns = water_mask.shape

    if (
        row < 0
        or row >= rows
        or column < 0
        or column >= columns
    ):
        return False

    row_start = max(
        0,
        row - buffer_pixels
    )

    row_end = min(
        rows,
        row + buffer_pixels + 1
    )

    column_start = max(
        0,
        column - buffer_pixels
    )

    column_end = min(
        columns,
        column + buffer_pixels + 1
    )

    neighborhood = water_mask[
        row_start:row_end,
        column_start:column_end
    ]

    return bool(np.any(neighborhood))