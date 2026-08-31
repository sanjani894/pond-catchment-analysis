from external_apis import get_historical_rainfall


latitude = 21.244862382478587
longitude = 81.28897840326484


rainfall = get_historical_rainfall(
    latitude=latitude,
    longitude=longitude,
    start_date="2025-01-01",
    end_date="2025-12-31"
)


print("Rainfall result:")
print(rainfall)