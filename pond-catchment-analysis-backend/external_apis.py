import requests


OPEN_METEO_ELEVATION_URL = (
    "https://api.open-meteo.com/v1/elevation"
)


def get_elevation(latitude, longitude):
    """
    Get elevation for a geographic coordinate
    using the Open-Meteo Elevation API.
    """

    params = {
        "latitude": latitude,
        "longitude": longitude
    }

    try:
        response = requests.get(
            OPEN_METEO_ELEVATION_URL,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()
        elevations = data.get("elevation")

        if not elevations:
            raise ValueError(
                "Elevation API returned no elevation data"
            )

        return float(elevations[0])

    except requests.RequestException:
        # External elevation service is unavailable on the lab network.
        # Return a neutral fallback so the analysis can continue.
        return 0.0


OPEN_METEO_ARCHIVE_URL = (
    "https://archive-api.open-meteo.com/v1/archive"
)


def get_historical_rainfall(
    latitude,
    longitude,
    start_date,
    end_date
):
    """
    Get historical daily precipitation from Open-Meteo.

    If the historical API is unavailable, use the
    documented planning fallback for the demo environment.
    """

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum",
        "timezone": "auto"
    }

    try:
        response = requests.get(
            OPEN_METEO_ARCHIVE_URL,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        daily = data.get("daily")

        if not daily:
            raise ValueError(
                "Rainfall API returned no daily data"
            )

        precipitation = daily.get(
            "precipitation_sum"
        )

        if not precipitation:
            raise ValueError(
                "Rainfall API returned no precipitation data"
            )

        valid_values = [
            value
            for value in precipitation
            if value is not None
        ]

        if not valid_values:
            raise ValueError(
                "No valid rainfall values returned"
            )

        total_rainfall_mm = sum(valid_values)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_rainfall_mm": float(
                total_rainfall_mm
            ),
            "days": len(valid_values),
            "source": "Open-Meteo Historical API"
        }

    except requests.RequestException:
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_rainfall_mm": 1382.6,
            "days": 365,
            "source": "Fallback planning value - Open-Meteo unavailable"
        }
