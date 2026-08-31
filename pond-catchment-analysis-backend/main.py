import numpy as np
import requests

from fastapi import FastAPI, UploadFile, File, HTTPException
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
    file: UploadFile = File(...)
):
    try:

        # -------------------------------------------------
        # 1. Read uploaded contour file
        # -------------------------------------------------

        file_bytes = await file.read()

        # -------------------------------------------------
        # 2. Parse contour map
        # -------------------------------------------------

        result = parse_contours(
            file_bytes=file_bytes,
            filename=file.filename or ""
        )

        # -------------------------------------------------
        # 3. Build DEM
        # -------------------------------------------------

        terrain = build_dem(
            contours=result["contours"],
            bounds=result["bounds"]
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

        satellite_water = get_water_mask_from_satellite(
            bbox=satellite_bbox,
            start_date="2025-01-01",
            end_date="2025-12-31",
            maximum_cloud_cover=20,
            threshold=0.2
        )

        # -------------------------------------------------
        # 7. Create water checker
        # -------------------------------------------------

        def water_checker(
            latitude,
            longitude
        ):
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

        pond_candidates = select_pond_candidates(
            elevation_grid=terrain["elevation_grid"],
            flow_accumulation=flow_accumulation,
            x_grid=terrain["x_grid"],
            y_grid=terrain["y_grid"],
            transformer=terrain["transformer"],
            number_of_candidates=5,
            minimum_distance_cells=10,
            water_checker=water_checker
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

            api_elevation = get_elevation(
                latitude=candidate["latitude"],
                longitude=candidate["longitude"]
            )

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
                    ]
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

        response["satellite_water_detection"] = {
            "image_id": satellite_water[
                "image_id"
            ],
            "image_date": str(
                satellite_water["image_date"]
            ),
            "cloud_cover": float(
                satellite_water["cloud_cover"]
            ),
            "scl_water_pixels": int(
                np.sum(
                    satellite_water[
                        "scl_water_mask"
                    ]
                )
            )
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