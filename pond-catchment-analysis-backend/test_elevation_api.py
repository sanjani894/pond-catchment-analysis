from external_apis import get_elevation


latitude = 21.244862382478587
longitude = 81.28897840326484


elevation = get_elevation(
    latitude,
    longitude
)


print("Latitude:", latitude)
print("Longitude:", longitude)
print("API elevation:", elevation, "m")