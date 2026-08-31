from runoff_analysis import calculate_runoff_volume


result = calculate_runoff_volume(
    rainfall_mm=1382.6,
    catchment_area_m2=171184.31905966267,
    runoff_coefficient=0.5
)


print("Runoff result:")

for key, value in result.items():
    print(f"{key}: {value}")