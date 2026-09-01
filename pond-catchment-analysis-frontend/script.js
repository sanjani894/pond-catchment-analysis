const API_URL = "https://pond-catchment-analysis.onrender.com/analyzeContour";

const fileInput = document.getElementById("contourFile");
const analyzeButton = document.getElementById("analyzeButton");
const statusText = document.getElementById("status");

const resultsSection = document.getElementById("results");
const bestCandidate = document.getElementById("bestCandidate");
const terrainInfo = document.getElementById("terrainInfo");
const flowInfo = document.getElementById("flowInfo");
const satelliteInfo = document.getElementById("satelliteInfo");
const candidateTable = document.getElementById("candidateTable");

analyzeButton.addEventListener("click", async () => {
  const file = fileInput.files[0];

  if (!file) {
    statusText.textContent = "Please select a KML or KMZ file.";
    return;
  }

  const fileName = file.name.toLowerCase();

  if (!fileName.endsWith(".kml") && !fileName.endsWith(".kmz")) {
    statusText.textContent = "Please upload a KML or KMZ file.";
    return;
  }

  analyzeButton.disabled = true;
  statusText.textContent = "Analyzing contour map...";
  resultsSection.classList.add("hidden");

  const formData = new FormData();

  formData.append("contour_map", file);

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Analysis failed.");
    }

    displayResults(data);

    statusText.textContent = "Analysis completed successfully.";
  } catch (error) {
    console.error(error);

    statusText.textContent = "Error: " + error.message;
  } finally {
    analyzeButton.disabled = false;
  }
});

function displayResults(data) {
  resultsSection.classList.remove("hidden");

  const candidates = data.pond_candidates || [];

  if (candidates.length === 0) {
    bestCandidate.innerHTML = "<p>No pond candidates were found.</p>";
    return;
  }

  displayBestCandidate(candidates[0]);

  displayTerrain(data.terrain);

  displayFlow(data.flow_direction, data.flow_accumulation);

  displaySatellite(data.satellite_water_detection);

  displayCandidates(candidates);

  resultsSection.scrollIntoView({
    behavior: "smooth",
  });
}

function displayBestCandidate(candidate) {
  const catchment = candidate.catchment;
  const rainfall = candidate.rainfall;
  const runoff = candidate.runoff;
  const storage = candidate.pond_storage || candidate.pond_storage_estimate;
  const ranking = candidate.ranking;

  bestCandidate.innerHTML = `

        <div class="best-location">

            <div class="metric">
                <strong>Rank</strong>
                <span>#${candidate.rank}</span>
            </div>

            <div class="metric">
                <strong>Latitude</strong>
                <span>${candidate.latitude.toFixed(6)}</span>
            </div>

            <div class="metric">
                <strong>Longitude</strong>
                <span>${candidate.longitude.toFixed(6)}</span>
            </div>

            <div class="metric">
                <strong>Elevation</strong>
                <span>${candidate.elevation.toFixed(2)} m</span>
            </div>

            <div class="metric">
                <strong>Catchment Area</strong>
                <span>${catchment.area_hectares.toFixed(2)} ha</span>
            </div>

            <div class="metric">
                <strong>Flow Accumulation</strong>
                <span>${candidate.flow_accumulation}</span>
            </div>

            <div class="metric">
                <strong>Annual Rainfall</strong>
                <span>${rainfall.total_rainfall_mm.toFixed(1)} mm</span>
            </div>

            <div class="metric">
                <strong>Estimated Runoff</strong>
                <span>${formatNumber(
                  runoff.estimated_runoff_volume_m3,
                )} m³</span>
            </div>

            <div class="metric">
                <strong>Available Storage Estimate</strong>
                <span>${formatNumber(
                  storage.estimated_available_storage_m3,
                )} m³</span>
            </div>

            <div class="metric">
                <strong>Suitability</strong>
                <span>${ranking.recommendation}</span>
            </div>

            <div class="metric">
                <strong>Final Score</strong>
                <span>${ranking.final_score.toFixed(3)}</span>
            </div>

            <div class="metric">
                <strong>Existing Water Nearby</strong>
                <span>
                    ${
                      candidate.water_check.inside_or_near_existing_water
                        ? "Yes"
                        : "No"
                    }
                </span>
            </div>

        </div>
    `;
}

function displayTerrain(terrain) {
  terrainInfo.innerHTML = `

        <p>
            <strong>Grid:</strong>
            ${terrain.grid_size} × ${terrain.grid_size}
        </p>

        <p>
            <strong>Cell Width:</strong>
            ${terrain.cell_width_m.toFixed(2)} m
        </p>

        <p>
            <strong>Cell Height:</strong>
            ${terrain.cell_height_m.toFixed(2)} m
        </p>

        <p>
            <strong>Minimum Elevation:</strong>
            ${terrain.min_elevation.toFixed(2)} m
        </p>

        <p>
            <strong>Maximum Elevation:</strong>
            ${terrain.max_elevation.toFixed(2)} m
        </p>
    `;
}

function displayFlow(direction, accumulation) {
  flowInfo.innerHTML = `

        <p>
            <strong>Flow Grid:</strong>
            ${direction.grid_rows} ×
            ${direction.grid_columns}
        </p>

        <p>
            <strong>Maximum Accumulation:</strong>
            ${accumulation.max_accumulation}
        </p>

        <p>
            <strong>Mean Accumulation:</strong>
            ${accumulation.mean_accumulation.toFixed(2)}
        </p>
    `;
}

function displaySatellite(satellite) {
  satelliteInfo.innerHTML = `

        <p>
            <strong>Image Date:</strong>
            ${satellite.image_date}
        </p>

        <p>
            <strong>Cloud Cover:</strong>
            ${satellite.cloud_cover}
        </p>

        <p>
            <strong>Water Pixels:</strong>
            ${satellite.scl_water_pixels}
        </p>

        <p>
            <strong>Image ID:</strong>
            ${satellite.image_id}
        </p>
    `;
}

function displayCandidates(candidates) {
  candidateTable.innerHTML = "";

  candidates.forEach((candidate) => {
    const storageData =
      candidate.pond_storage || candidate.pond_storage_estimate;

    const storage = storageData.estimated_available_storage_m3;

    const runoff = candidate.runoff.estimated_runoff_volume_m3;

    const area = candidate.catchment.area_hectares;

    const recommendation = candidate.ranking.recommendation;

    let recommendationClass = "moderate";

    if (recommendation === "Highly suitable") {
      recommendationClass = "highly";
    } else if (recommendation === "Suitable") {
      recommendationClass = "suitable";
    }

    const row = document.createElement("tr");

    row.innerHTML = `

            <td>
                <strong>#${candidate.rank}</strong>
            </td>

            <td>
                ${candidate.latitude.toFixed(5)},
                ${candidate.longitude.toFixed(5)}
            </td>

            <td>
                ${candidate.elevation.toFixed(2)} m
            </td>

            <td>
                ${area.toFixed(2)} ha
            </td>

            <td>
                ${candidate.rainfall.total_rainfall_mm.toFixed(1)} mm
            </td>

            <td>
                ${formatNumber(runoff)} m³
            </td>

            <td>
                ${formatNumber(storage)} m³
            </td>

            <td class="recommendation ${recommendationClass}">
                ${recommendation}
            </td>
        `;

    candidateTable.appendChild(row);
  });
}

function formatNumber(value) {
  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  });
}
