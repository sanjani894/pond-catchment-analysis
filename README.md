# Pond Catchment Analysis

## Overview

Pond Catchment Analysis is a backend-based application that analyzes an uploaded contour map in KML/KMZ format and identifies suitable locations for pond planning.

The system derives terrain information, flow characteristics, catchment area, rainfall, runoff and an estimated storage value from the uploaded contour map.

The implementation is designed to work with different contour maps rather than using hard-coded locations or results from a particular sample map.

## Features

- Upload KML/KMZ contour maps
- Parse contour and elevation information
- Generate a terrain elevation model (DEM)
- Calculate flow direction
- Calculate flow accumulation
- Identify suitable pond candidate locations
- Delineate the catchment area for each candidate
- Obtain elevation using an external elevation API
- Obtain historical rainfall using the Open-Meteo API
- Detect nearby existing water using satellite data
- Estimate runoff volume
- Estimate available pond storage
- Rank multiple pond candidates
- Return structured JSON results through a REST API

## Project Structure

pond-catchment-analysis/
│
├── pond-catchment-analysis-backend/
│ ├── main.py
│ ├── kml_parser.py
│ ├── terrain_builder.py
│ ├── flow_analysis.py
│ ├── pond_selection.py
│ ├── water_detection.py
│ ├── runoff_analysis.py
│ ├── pond_capacity.py
│ └── external_apis.py
│
├── pond-catchment-analysis-frontend/
│ ├── index.html
│ ├── script.js
│ └── style.css
│
└── README.md

## Technologies Used

### Backend

- Python
- FastAPI
- Uvicorn
- NumPy
- Requests

### Frontend

- HTML
- CSS
- JavaScript

### External APIs and Data

- Open-Meteo Elevation API
- Open-Meteo Historical Weather API
- Satellite-based water detection

## API Documentation

### POST `/analyzeContour`

This endpoint accepts a contour map in KML or KMZ format and analyzes the terrain to identify suitable pond locations and their catchment information.

### Request

The request uses:

multipart/form-data

The uploaded file must be provided using the field:

file

### Local API URL

http://127.0.0.1:8000/analyzeContour

### Example Request

POST /analyzeContour

with a KML or KMZ file uploaded using the `file` field.

## Processing Workflow

The uploaded contour map is processed using the following workflow:

KML/KMZ Upload
↓
Contour Parsing
↓
Terrain / DEM Generation
↓
Flow Direction Calculation
↓
Flow Accumulation Calculation
↓
Pond Candidate Selection
↓
Catchment Delineation
↓
Elevation and Rainfall Data
↓
Runoff Estimation
↓
Storage Estimation
↓
Candidate Ranking
↓
JSON Response

## Catchment Estimation Approach

The system first extracts contour lines and their elevation values from the uploaded contour map.

A terrain elevation grid is then generated from the contour information.

Flow direction is calculated from the terrain elevation grid. Flow accumulation is subsequently calculated to determine locations where drainage converges.

Locations with suitable terrain and high flow accumulation are considered pond candidates.

For each selected candidate, the upstream cells contributing water to that location are identified.

The catchment area is calculated using:

Catchment Area = Number of Catchment Cells × Area of One Cell

The resulting catchment area is reported in square metres and hectares.

## Elevation Data

For each selected pond candidate, an external elevation API is used to obtain elevation information based on the candidate's calculated latitude and longitude.

This allows elevation information to be obtained dynamically for the selected location instead of hard-coding a value for the sample contour map.

## Rainfall Estimation

Historical rainfall data is obtained using the Open-Meteo Historical Weather API.

The current implementation uses the period:

2025-01-01 to 2025-12-31

The total daily precipitation is summed to obtain the total rainfall in millimetres.

## Runoff Estimation

Runoff is estimated using:

Runoff Volume = Rainfall Depth × Catchment Area × Runoff Coefficient

Rainfall depth in millimetres is converted to metres before calculating the volume.

The current implementation uses:

Runoff Coefficient = 0.5

This is a planning assumption used for preliminary runoff estimation.

## Pond Storage Estimate

A preliminary pond storage estimate is calculated using:

Estimated Available Storage = Estimated Runoff Volume × Storage Fraction

The current implementation uses:

Storage Fraction = 30%

Therefore:

Estimated Available Storage = Estimated Runoff Volume × 0.30

The 30% value is an assumed planning fraction and does not represent the actual physical storage capacity or final engineered dimensions of a pond.

Actual pond design would require detailed hydrological, geological and engineering analysis.

## Satellite Water Detection

Satellite data is used to check whether a selected pond candidate is inside or near an existing waterbody.

Candidates that are detected as being inside or near existing water are filtered during pond candidate selection.

The API response also provides satellite image information such as:

- Image ID
- Image date
- Cloud cover
- Number of detected water pixels

## Pond Candidate Ranking

Multiple suitable pond candidates are analyzed and ranked.

The final suitability score combines:

- Terrain suitability
- Catchment area
- Estimated runoff
- Estimated storage

The current ranking weights are:

Terrain suitability = 40%
Catchment area = 25%
Runoff volume = 20%
Storage estimate = 15%

The candidates are sorted from highest to lowest final score.

Recommendations are generated according to the final score:

Score >= 0.75
Highly suitable

Score >= 0.50
Suitable

Score < 0.50
Moderately suitable

## Sample Demonstration

The system was tested using the provided assignment contour map:

contours_1m.kml

Example result from the analysis:

Best Pond Location:
Latitude: 21.244862
Longitude: 81.288978

Catchment Area: 17.12 ha
Flow Accumulation: 170
Annual Rainfall: 1382.6 mm
Estimated Runoff: 118,339.72 m³
Estimated Available Storage: 35,501.92 m³
Suitability: Highly suitable
Final Score: 0.996

The API also returns multiple pond candidates with their corresponding:

- Location
- Elevation
- Flow accumulation
- Catchment area
- Rainfall
- Estimated runoff
- Estimated storage
- Suitability score
- Ranking

## Generalization and Reusability

The implementation does not hard-code the coordinates or final results of the provided sample contour map.

The contour information is read from the uploaded KML/KMZ file.

Terrain and flow calculations are performed using the uploaded contour data.

Pond candidate locations are generated from the resulting terrain and flow analysis.

Therefore, another KML/KMZ contour map can be uploaded and processed through the same analysis pipeline.

## Backend Setup

### 1. Navigate to the backend

cd pond-catchment-analysis-backend

### 2. Activate the virtual environment

.\.venv\Scripts\Activate.ps1

### 3. Start the FastAPI server

python -m uvicorn main:app --reload

The backend will run at:

http://127.0.0.1:8000

## FastAPI Documentation

After starting the backend, interactive API documentation is available at:

http://127.0.0.1:8000/docs

The `/docs` page can be used to test the `/analyzeContour` endpoint by uploading a KML or KMZ file.

## Frontend Setup

Open another PowerShell terminal and navigate to the frontend directory:

cd pond-catchment-analysis-frontend

Start the local frontend server:

python -m http.server 5501

Open the frontend in a browser:

http://127.0.0.1:5501/index.html

Select a KML/KMZ contour map and click:

Analyze Contour Map

The frontend sends the uploaded file to:

http://127.0.0.1:8000/analyzeContour

and displays the returned analysis results.

## API Response

The API returns structured JSON containing:

- File information
- Contour information
- Terrain information
- Flow direction information
- Flow accumulation information
- Satellite water detection information
- Pond candidates
- Catchment information
- Rainfall information
- Runoff estimation
- Pond storage estimate
- Candidate ranking
- Recommendation

## Example API Response Structure

{
"filename": "contours_1m.kml",
"terrain": {
"grid_size": 100,
"cell_width_m": 22.48,
"cell_height_m": 12.06,
"min_elevation": 267.0,
"max_elevation": 297.64
},
"flow_direction": {
"grid_rows": 100,
"grid_columns": 100
},
"flow_accumulation": {
"max_accumulation": 170
},
"pond_candidates": [
{
"latitude": 21.244862,
"longitude": 81.288978,
"catchment": {
"area_hectares": 17.12
},
"rainfall": {
"total_rainfall_mm": 1382.6
},
"runoff": {
"estimated_runoff_volume_m3": 118339.72
},
"pond_storage": {
"estimated_available_storage_m3": 35501.92
},
"ranking": {
"recommendation": "Highly suitable"
}
}
]
}

## Project Limitations

The current implementation provides a preliminary pond suitability and catchment estimation system.

The following values are currently modelling assumptions:

- Runoff coefficient = 0.5
- Storage fraction = 30%
- Historical rainfall period = 2025

These values can be made configurable in future phases.

The estimated storage value should not be interpreted as the final engineered pond capacity.

## Future Improvements

Possible future improvements include:

- Configurable rainfall period
- Configurable runoff coefficient
- Configurable storage fraction
- More detailed hydrological modelling
- Improved DEM interpolation
- GIS map visualization
- Interactive pond candidate markers
- Detailed catchment boundary visualization
- Terrain and elevation maps
- Improved pond dimension estimation
- Public cloud deployment

## GitHub Repository

Repository:

https://github.com/sanjani894/pond-catchment-analysis
