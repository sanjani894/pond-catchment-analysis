import numpy as np


from water_detection import (
    get_water_mask_from_satellite,
    is_water_location,
    is_near_water
)


bbox = [
    81.2814044952393,
    21.2398224433387,
    81.3126468658447,
    21.2635806472203
]


result = get_water_mask_from_satellite(
    bbox=bbox,
    start_date="2025-01-01",
    end_date="2025-12-31",
    maximum_cloud_cover=20,
    threshold=0.2
)


water_mask = result["water_mask"]
ndwi = result["ndwi"]
scl_water_mask = result["scl_water_mask"]
pond_latitude = 21.244862382478587
pond_longitude = 81.28897840326484


candidate_is_water = is_water_location(
    latitude=pond_latitude,
    longitude=pond_longitude,
    water_mask=scl_water_mask,
    transform=result["scl_transform"],
    crs=result["scl_crs"]
)
candidate_near_water = is_near_water(
    latitude=pond_latitude,
    longitude=pond_longitude,
    water_mask=scl_water_mask,
    transform=result["scl_transform"],
    crs=result["scl_crs"],
    buffer_pixels=2
)

print(
    "Current pond candidate near water:",
    candidate_near_water
)


print()
print(
    "Current pond candidate detected as water:",
    candidate_is_water
)


print("Satellite image:")
print("ID:", result["image_id"])
print("Date:", result["image_date"])
print("Cloud cover:", result["cloud_cover"])

print()
print("CRS:", result["crs"])
print("Raster shape:", water_mask.shape)

print()
print(
    "Detected water pixels:",
    int(np.sum(water_mask))
)

print(
    "Total valid pixels:",
    int(np.sum(np.isfinite(ndwi)))
)

print(
    "Water percentage:",
    round(
        100 * np.sum(water_mask)
        / np.sum(np.isfinite(ndwi)),
        2
    ),
    "%"
)

valid_ndwi = ndwi[np.isfinite(ndwi)]

print()
print("NDWI statistics:")
print("Minimum:", float(np.min(valid_ndwi)))
print("Maximum:", float(np.max(valid_ndwi)))
print("Mean:", float(np.mean(valid_ndwi)))
print("90th percentile:", float(np.percentile(valid_ndwi, 90)))
print("95th percentile:", float(np.percentile(valid_ndwi, 95)))
print("99th percentile:", float(np.percentile(valid_ndwi, 99)))

print()
print(
    "SCL water pixels:",
    int(np.sum(scl_water_mask))
)

print(
    "SCL mask shape:",
    scl_water_mask.shape
)