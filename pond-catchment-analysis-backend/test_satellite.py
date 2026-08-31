import pystac_client
import planetary_computer
import rasterio


CATALOG_URL = (
    "https://planetarycomputer.microsoft.com/api/stac/v1"
)

bbox = [
    81.2814044952393,
    21.2398224433387,
    81.3126468658447,
    21.2635806472203
]


catalog = pystac_client.Client.open(
    CATALOG_URL
)


search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=bbox,
    datetime="2025-01-01/2025-12-31",
    query={
        "eo:cloud_cover": {
            "lt": 20
        }
    }
)


items = list(search.items())

if not items:
    raise ValueError(
        "No Sentinel-2 images found"
    )


# Select the image with the lowest cloud cover.
best_item = min(
    items,
    key=lambda item: item.properties.get(
        "eo:cloud_cover",
        100
    )
)


print("Selected Sentinel-2 image:")
print("ID:", best_item.id)
print("Date:", best_item.datetime)
print(
    "Cloud cover:",
    best_item.properties.get("eo:cloud_cover")
)


# Sign the asset URLs so they can be accessed.
signed_item = planetary_computer.sign(
    best_item
)


print()
print("Available assets:")
for asset_name in signed_item.assets:
    print("-", asset_name)


# Check that the required Sentinel-2 bands exist.
required_bands = ["B03", "B08"]

for band in required_bands:

    if band not in signed_item.assets:
        raise ValueError(
            f"Required band {band} not found"
        )

    asset = signed_item.assets[band]

    print()
    print(f"{band} asset found:")
    print(asset.href)

    with rasterio.open(asset.href) as src:
        print(
            f"{band} shape:",
            src.width,
            "x",
            src.height
        )

        print(
            f"{band} CRS:",
            src.crs
        )

        print(
            f"{band} resolution:",
            src.res
        )