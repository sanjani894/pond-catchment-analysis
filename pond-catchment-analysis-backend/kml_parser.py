import io
import zipfile
import xml.etree.ElementTree as ET


KML_NAMESPACE = {"kml": "http://www.opengis.net/kml/2.2"}


def _get_kml_content(file_bytes: bytes, filename: str) -> bytes:
    """Return the KML XML content from a KML or KMZ file."""

    if filename.lower().endswith(".kmz"):
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as kmz:
            kml_files = [
                name for name in kmz.namelist()
                if name.lower().endswith(".kml")
            ]

            if not kml_files:
                raise ValueError("No KML file found inside KMZ")

            return kmz.read(kml_files[0])

    if filename.lower().endswith(".kml"):
        return file_bytes

    raise ValueError("Only KML and KMZ files are supported")

def parse_contours(file_bytes: bytes, filename: str) -> dict:
    """Parse contour features and return terrain and geometry information."""

    kml_content = _get_kml_content(file_bytes, filename)

    root = ET.fromstring(kml_content)

    placemarks = root.findall(".//kml:Placemark", KML_NAMESPACE)

    elevations = []
    all_coordinates = []
    contours = []

    for placemark in placemarks:
        name = placemark.find("kml:name", KML_NAMESPACE)

        if name is None or name.text is None:
            continue

        try:
            elevation = float(name.text.strip())
        except ValueError:
            continue

        coordinate_elements = placemark.findall(
            ".//kml:coordinates",
            KML_NAMESPACE
        )

        contour_coordinates = []

        for element in coordinate_elements:
            if element.text is None:
                continue

            for coordinate in element.text.strip().split():
                parts = coordinate.split(",")

                if len(parts) < 2:
                    continue

                longitude = float(parts[0])
                latitude = float(parts[1])

                contour_coordinates.append(
                    (longitude, latitude)
                )

        if not contour_coordinates:
            continue

        contours.append({
            "elevation": elevation,
            "coordinates": contour_coordinates
        })
        elevations.append(elevation)
        all_coordinates.extend(contour_coordinates)

    if not elevations:
        raise ValueError("No contour elevations found in the input file")

    longitudes = [point[0] for point in all_coordinates]
    latitudes = [point[1] for point in all_coordinates]

    return {
        "filename": filename,
        "contour_count": len(elevations),
        "min_elevation": min(elevations),
        "max_elevation": max(elevations),
        "coordinate_count": len(all_coordinates),
        "bounds": {
            "min_longitude": min(longitudes),
            "min_latitude": min(latitudes),
            "max_longitude": max(longitudes),
            "max_latitude": max(latitudes)
        },
        "contours": contours
    }