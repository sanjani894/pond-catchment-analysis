import numpy as np

from water_detection import create_water_mask


green = np.array([
    [0.40, 0.20, 0.10],
    [0.35, 0.30, 0.15],
    [0.10, 0.20, 0.25]
])

nir = np.array([
    [0.10, 0.30, 0.20],
    [0.10, 0.25, 0.40],
    [0.30, 0.20, 0.20]
])


water_mask, ndwi = create_water_mask(
    green_band=green,
    nir_band=nir,
    threshold=0.2
)


print("NDWI:")
print(ndwi)

print()
print("Water mask:")
print(water_mask.astype(int))

print()
print(
    "Detected water cells:",
    int(np.sum(water_mask))
)