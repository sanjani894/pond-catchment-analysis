import numpy as np
import requests

from rasterio.features import shapes
from rasterio.transform import Affine

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from external_apis import (
    get_elevation,
    get_historical_rainfall
)

from kml_parser import parse_contours
from terrain_builder import build_dem

from flow_analysis import (
    calculate_flow_direction,
    calculate_flow_accumulation,
    delineate_catchment
)

from pond_selection import select_pond_candidates

from water_detection import (
    get_water_mask_from_satellite,
    is_near_water
)

from runoff_analysis import calculate_runoff_volume
from pond_capacity import estimate_pond_storage


app = FastAPI(
    title="Pond Catchment Analysis Backend"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
) 

def catchment_mask_to_geojson(
    mask,
    x_grid,
    y_grid,
    transformer,
    cell_width_m,
    cell_height_m
):
    """Convert a projected catchment mask into WGS84 GeoJSON."""

    raster_mask = np.flipud(
        mask.astype(np.uint8)
    )

    transform = Affine(
        cell_width_m,
        0,
        x_grid[0] - cell_width_m / 2,
        0,
        -cell_height_m,
        y_grid[-1] + cell_height_m / 2
    )

    geometries = [
        geometry
        for geometry, value in shapes(
            raster_mask,
            mask=raster_mask.astype(bool),
            transform=transform
        )
        if value
    ]

    def convert_coordinates(value):
        if (
            isinstance(value, (list, tuple))
            and len(value) >= 2
            and isinstance(value[0], (int, float))
        ):
            longitude, latitude = transformer.transform(
                value[0],
                value[1],
                direction="INVERSE"
            )
            return [float(longitude), float(latitude)]

        return [
            convert_coordinates(item)
            for item in value
        ]

    features = []

    for geometry in geometries:
        converted = {
            "type": geometry["type"],
            "coordinates": convert_coordinates(
                geometry["coordinates"]
            )
        }

        features.append({
            "type": "Feature",
            "properties": {},
            "geometry": converted
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


def normalize_score(values):
    minimum = min(values)
    maximum = max(values)

    if maximum == minimum:
        return [1.0] * len(values)

    return [
        (value - minimum) / (maximum - minimum)
        for value in values
    ]


@app.get("/")
def root():
    return {
        "message": "Pond Catchment Analysis Backend is running"
    }


@app.post("/analyzeContour")
async def analyze_contour(
    contour_map: UploadFile = File(...),
    min_latitude: float | None = Form(None),
    max_latitude: float | None = Form(None),
    min_longitude: float | None = Form(None),
    max_longitude: float | None = Form(None)
):
    print(">>> ENTERED analyze_contour", flush=True)
    try:

        # -------------------------------------------------
        # 1. Read uploaded contour file
        # -------------------------------------------------

        file_bytes = await contour_map.read()
        print(">>> FILE READ:", len(file_bytes), "bytes", flush=True)

        # -------------------------------------------------
        # 2. Parse contour map
        # -------------------------------------------------

        print(">>> BEFORE PARSE", flush=True)
        result = parse_contours(
            file_bytes=file_bytes,
            filename=contour_map.filename or ""
        )

        # -------------------------------------------------
        # 3. Build DEM
        # -------------------------------------------------

        # Use the user-selected map area when provided.
        analysis_bounds = result["bounds"]

        if all(value is not None for value in [
            min_latitude,
            max_latitude,
            min_longitude,
            max_longitude
        ]):
            analysis_bounds = {
                "min_latitude": min_latitude,
                "max_latitude": max_latitude,
                "min_longitude": min_longitude,
                "max_longitude": max_longitude
            }

        terrain = build_dem(
            contours=result["contours"],
            bounds=analysis_bounds
        )

        # -------------------------------------------------
        # 4. Calculate flow direction
        # -------------------------------------------------

        flow_direction = calculate_flow_direction(
            elevation_grid=terrain["elevation_grid"],
            cell_width_m=terrain["cell_width_m"],
            cell_height_m=terrain["cell_height_m"]
        )

        # -------------------------------------------------
        # 5. Calculate flow accumulation
        # -------------------------------------------------

        flow_accumulation = calculate_flow_accumulation(
            flow_direction
        )

        # -------------------------------------------------
        # 6. Get satellite water mask
        # -------------------------------------------------

        bounds = result["bounds"]

        satellite_bbox = [
            bounds["min_longitude"],
            bounds["min_latitude"],
            bounds["max_longitude"],
            bounds["max_latitude"]
        ]

        # Satellite water detection is optional.
        # The lab server cannot reach the external satellite service,
        # so skip it to keep the analysis API responsive.
        satellite_water = None
        satellite_available = False

        # -------------------------------------------------
        # 7. Create water checker
        # -------------------------------------------------

        def water_checker(
            latitude,
            longitude
        ):
            if not satellite_available:
                return False

            return is_near_water(
                latitude=latitude,
                longitude=longitude,
                water_mask=satellite_water[
                    "scl_water_mask"
                ],
                transform=satellite_water[
                    "scl_transform"
                ],
                crs=satellite_water[
                    "scl_crs"
                ],
                buffer_pixels=2
            )

        # -------------------------------------------------
        # 8. Select 2-5 pond candidates
        # -------------------------------------------------

        # Dynamically exclude extreme drainage-channel cells.
        drainage_threshold = float(
            np.percentile(flow_accumulation, 98)
        )

        if np.max(flow_accumulation) <= drainage_threshold:
            drainage_threshold = None

        pond_candidates = select_pond_candidates(
            elevation_grid=terrain["elevation_grid"],
            flow_accumulation=flow_accumulation,
            x_grid=terrain["x_grid"],
            y_grid=terrain["y_grid"],
            transformer=terrain["transformer"],
            number_of_candidates=5,
            minimum_distance_cells=10,
            water_checker=water_checker,
            max_flow_accumulation=drainage_threshold
        )

        if not pond_candidates:
            raise ValueError(
                "No suitable pond candidates found "
                "after waterbody filtering"
            )

        # -------------------------------------------------
        # 9. Analyze every candidate
        # -------------------------------------------------

        analyzed_candidates = []

        for candidate in pond_candidates:

            # -------------------------------------------------
            # Elevation API
            # -------------------------------------------------

            # Use elevation derived from the uploaded contour map.
            # External elevation API is unavailable on the lab network.
            api_elevation = float(candidate["elevation"])

            # -------------------------------------------------
            # Catchment
            # -------------------------------------------------

            catchment = delineate_catchment(
                flow_direction=flow_direction,
                outlet_row=candidate["row"],
                outlet_column=candidate["column"],
                cell_width_m=terrain["cell_width_m"],
                cell_height_m=terrain["cell_height_m"]
            )
            catchment_geojson = catchment_mask_to_geojson(
                mask=catchment["mask"],
                x_grid=terrain["x_grid"],
                y_grid=terrain["y_grid"],
                transformer=terrain["transformer"],
                cell_width_m=terrain["cell_width_m"],
                cell_height_m=terrain["cell_height_m"]
            )

            # -------------------------------------------------
            # Historical rainfall API
            # -------------------------------------------------

            rainfall = get_historical_rainfall(
                latitude=candidate["latitude"],
                longitude=candidate["longitude"],
                start_date="2025-01-01",
                end_date="2025-12-31"
            )

            # -------------------------------------------------
            # Runoff calculation
            # -------------------------------------------------

            runoff = calculate_runoff_volume(
                rainfall_mm=rainfall["total_rainfall_mm"],
                catchment_area_m2=catchment["area_m2"],
                runoff_coefficient=0.5
            )
            pond_storage = estimate_pond_storage(
               estimated_runoff_volume_m3=runoff[
                   "estimated_runoff_volume_m3"
                ],
                storage_fraction=0.30
            )

            # -------------------------------------------------
            # Candidate result
            # -------------------------------------------------

            analyzed_candidates.append({
                **candidate,

                "api_elevation_m": api_elevation,

                "catchment": {
                    "cell_count": catchment[
                        "cell_count"
                    ],
                    "cell_area_m2": catchment[
                        "cell_area_m2"
                    ],
                    "area_m2": catchment[
                        "area_m2"
                    ],
                    "area_hectares": catchment[
                        "area_hectares"
                    ],
                    "geojson": catchment_geojson,
                },

                "rainfall": {
                    "start_date": rainfall[
                        "start_date"
                    ],
                    "end_date": rainfall[
                        "end_date"
                    ],
                    "total_rainfall_mm": rainfall[
                        "total_rainfall_mm"
                    ],
                    "days": rainfall["days"]
                },

                "runoff": runoff,
                "pond_storage": pond_storage


            })

                # -------------------------------------------------
        # Final ranking
        # -------------------------------------------------

        catchment_scores = normalize_score([
            candidate["catchment"]["area_m2"]
            for candidate in analyzed_candidates
        ])

        runoff_scores = normalize_score([
            candidate["runoff"][
                "estimated_runoff_volume_m3"
            ]
            for candidate in analyzed_candidates
        ])

        storage_scores = normalize_score([
           candidate["pond_storage"][
             "estimated_available_storage_m3"
            ]
             for candidate in analyzed_candidates
         ])

        for index, candidate in enumerate(
            analyzed_candidates
        ):

            terrain_score = candidate[
                "suitability_score"
            ]

            final_score = (
                0.40 * terrain_score
                + 0.25 * catchment_scores[index]
                + 0.20 * runoff_scores[index]
                + 0.15 * storage_scores[index]
            )

            candidate["ranking"] = {
                "final_score": float(final_score)
            }

        # Sort highest final score first.
        analyzed_candidates.sort(
            key=lambda candidate:
                candidate["ranking"]["final_score"],
            reverse=True
        )

        # Add rank and recommendation.
        for index, candidate in enumerate(
            analyzed_candidates,
            start=1
        ):

            candidate["rank"] = index

            score = candidate[
                "ranking"]["final_score"
            ]

            if score >= 0.75:
                recommendation = "Highly suitable"
            elif score >= 0.50:
                recommendation = "Suitable"
            else:
                recommendation = "Moderately suitable"

            candidate["ranking"][
                "recommendation"
            ] = recommendation    
       
        # -------------------------------------------------
        # 10. Create response
        # -------------------------------------------------

        response = {
            key: value
            for key, value in result.items()
            if key != "contours"
        }

        # -------------------------------------------------
        # 11. Terrain
        # -------------------------------------------------

        response["terrain"] = {
            "grid_size": terrain["grid_size"],
            "cell_width_m": terrain[
                "cell_width_m"
            ],
            "cell_height_m": terrain[
                "cell_height_m"
            ],
            "min_elevation": terrain[
                "min_elevation"
            ],
            "max_elevation": terrain[
                "max_elevation"
            ]
        }

        # -------------------------------------------------
        # 12. Flow direction
        # -------------------------------------------------

        response["flow_direction"] = {
            "grid_rows": int(
                flow_direction.shape[0]
            ),
            "grid_columns": int(
                flow_direction.shape[1]
            )
        }

        # -------------------------------------------------
        # 13. Flow accumulation
        # -------------------------------------------------

        response["flow_accumulation"] = {
            "max_accumulation": float(
                np.max(flow_accumulation)
            ),
            "mean_accumulation": float(
                np.mean(flow_accumulation)
            )
        }

        # -------------------------------------------------
        # 14. Satellite information
        # -------------------------------------------------

        if satellite_available:
            response["satellite_water_detection"] = {
                "image_id": satellite_water["image_id"],
                "image_date": str(
                    satellite_water["image_date"]
                ),
                "cloud_cover": float(
                    satellite_water["cloud_cover"]
                ),
                "scl_water_pixels": int(
                    np.sum(
                        satellite_water["scl_water_mask"]
                    )
                )
            }
        else:
            response["satellite_water_detection"] = {
                "image_id": "Unavailable - external service not reachable",
                "image_date": "Unavailable",
                "cloud_cover": "Unavailable",
                "scl_water_pixels": 0
            }

        # -------------------------------------------------
        # 15. Pond recommendations
        # -------------------------------------------------

        response["pond_candidates"] = analyzed_candidates

         # Keep the highest-ranked candidate for compatibility
         # with the previous API response.
        response["pond_candidate"] = analyzed_candidates[0]

        return response

    except requests.RequestException as error:

        raise HTTPException(
            status_code=502,
            detail=(
                "External API error: "
                f"{error}"
            )
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )