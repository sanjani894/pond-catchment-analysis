from pond_capacity import estimate_pond_storage


runoff_volume = 118339.71976594478

result = estimate_pond_storage(
    estimated_runoff_volume_m3=runoff_volume,
    storage_fraction=0.30
)

print("Pond storage result:")
print(result)