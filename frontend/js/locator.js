let map = L.map("map").setView([51.5074, -0.1278], 12);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

let markers = [];
let current = null; // { lat, lon, label }
let debounceTimer = null;

const cityInput = document.getElementById("city-input");
const suggestionsBox = document.getElementById("suggestions");
const statusBanner = document.getElementById("status-banner");
const resultsList = document.getElementById("results-list");

const TYPE_LABELS = { bin: "Recycling bin", charity_shop: "Charity shop", secondhand_store: "Second-hand store" };

function showBanner(message, kind = "info") {
  statusBanner.innerHTML = message
    ? `<div class="banner banner-${kind}">${escapeHtml(message)}</div>`
    : "";
}

function clearMarkers() {
  markers.forEach((m) => map.removeLayer(m));
  markers = [];
}

function renderResults(results) {
  clearMarkers();
  resultsList.innerHTML = "";

  results.forEach((r) => {
    const marker = L.marker([r.lat, r.lon]).addTo(map);
    marker.bindPopup(
      `<strong>${escapeHtml(r.name)}</strong><br>${escapeHtml(TYPE_LABELS[r.type] || r.type)}<br>${escapeHtml(r.address || "")}<br>${r.distance_km} km away`
    );
    markers.push(marker);

    const card = document.createElement("div");
    card.className = "result-card";
    card.innerHTML = `
      <div class="name">${escapeHtml(r.name)}</div>
      <div class="muted">${escapeHtml(r.address || "")}</div>
      <div class="row" style="justify-content:space-between; margin-top:6px;">
        <span class="badge badge-${r.type}">${escapeHtml(TYPE_LABELS[r.type] || r.type)}</span>
        <span class="muted">${r.distance_km} km${r.rating ? " · ★" + r.rating : ""}</span>
      </div>
    `;
    card.addEventListener("click", () => {
      map.flyTo([r.lat, r.lon], 16);
      marker.openPopup();
    });
    resultsList.appendChild(card);
  });
}

function getActiveTypes() {
  return Array.from(document.querySelectorAll(".type-filter:checked")).map((c) => c.value);
}

async function runSearch() {
  if (!current) return;
  const types = getActiveTypes();
  const radius_km = document.getElementById("radius-select").value;
  const sort = document.getElementById("sort-select").value;

  showBanner("Searching…", "info");
  resultsList.innerHTML = "";

  try {
    const params = { lat: current.lat, lon: current.lon, radius_km, sort, label: current.label || "" };
    if (types.length) params.types = types.join(",");
    const data = await Api.search(params);

    renderResults(data.results);

    if (data.stale) {
      showBanner("Showing cached results. Live data may be outdated right now.", "warn");
    } else if (data.message) {
      showBanner(data.message, "info");
    } else {
      showBanner("");
    }

    if (data.results.length) {
      const group = L.featureGroup(markers);
      map.fitBounds(group.getBounds().pad(0.25));
    } else {
      map.setView([current.lat, current.lon], 12);
    }
  } catch (err) {
    showBanner(err.message, "warn");
  }
}

cityInput.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  const q = cityInput.value.trim();
  if (q.length < 2) {
    suggestionsBox.style.display = "none";
    return;
  }
  debounceTimer = setTimeout(async () => {
    try {
      const data = await Api.geocode(q);
      suggestionsBox.innerHTML = "";
      data.suggestions.forEach((s) => {
        const btn = document.createElement("button");
        btn.textContent = s.label;
        btn.addEventListener("click", () => {
          cityInput.value = s.label;
          suggestionsBox.style.display = "none";
          current = { lat: s.lat, lon: s.lon, label: s.label };
          runSearch();
        });
        suggestionsBox.appendChild(btn);
      });
      suggestionsBox.style.display = data.suggestions.length ? "block" : "none";
      if (data.stale) showBanner("Showing cached location results that may be outdated.", "warn");
    } catch (err) {
      suggestionsBox.innerHTML = `<div style="padding:10px; font-size:0.85rem;">${escapeHtml(err.message)}</div>`;
      suggestionsBox.style.display = "block";
    }
  }, 350);
});

document.addEventListener("click", (e) => {
  if (!e.target.closest(".search-wrap")) suggestionsBox.style.display = "none";
});

document.getElementById("use-location-btn").addEventListener("click", () => {
  if (!navigator.geolocation) {
    showBanner("Your browser doesn't support location sharing. Try searching a city instead.", "warn");
    return;
  }
  showBanner("Getting your location…", "info");
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      current = { lat: pos.coords.latitude, lon: pos.coords.longitude, label: "My location" };
      cityInput.value = "My location";
      runSearch();
    },
    () => showBanner("Couldn't get your location. Check permissions, or search a city instead.", "warn")
  );
});

["radius-select", "sort-select"].forEach((id) =>
  document.getElementById(id).addEventListener("change", runSearch)
);
document.querySelectorAll(".type-filter").forEach((c) => c.addEventListener("change", runSearch));
