<script>
document.addEventListener("DOMContentLoaded", function () {
  const vendorList = document.getElementById("vendorList");
  const searchInput = document.getElementById("searchInput");
  const categoryFilter = document.getElementById("categoryFilter");

  function showLoader() {
    vendorList.innerHTML = `
      <div class="text-center py-4">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>`;
  }

  function fetchVendors(query = "", category = "") {
    showLoader();
    fetch(`/api/vendors?query=${encodeURIComponent(query)}&category=${encodeURIComponent(category)}`)
      .then(res => res.json())
      .then(data => {
        // Include vendors with no rating, exclude poorly rated ones
        const filtered = data.filter(v => v.average_rating === undefined || v.average_rating >= 4);
        const sorted = filtered.sort((a, b) => (b.average_rating || 0) - (a.average_rating || 0));
        displayVendors(sorted);
      })
      .catch(err => {
        console.error("Vendor fetch failed:", err);
        vendorList.innerHTML = "<p class='text-danger text-center'>Failed to load vendor list.</p>";
      });
  }

  function getStars(rating) {
    const full = Math.floor(rating);
    const half = rating % 1 >= 0.5;
    let stars = '⭐'.repeat(full);
    if (half) stars += '✩';
    return stars.padEnd(5, '☆');
  }

  function displayVendors(vendors) {
    if (!vendors.length) {
      vendorList.innerHTML = "<p class='text-muted text-center'>No vendors found.</p>";
      return;
    }

    vendorList.innerHTML = vendors.map(v => {
      const address = [
        v.plot_info, v.building_info, v.street, v.landmark,
        v.area, v.city, v.state, v.pincode
      ].filter(Boolean).join(", ");

      const photoFile = v.photos ? v.photos.split(",")[0] : "default.jpg";
      const photo = `/static/uploads/${photoFile}`;
      const rating = v.average_rating
        ? `${getStars(v.average_rating)} (${v.average_rating}/5, ${v.review_count} reviews)`
        : "No rating yet";

      const badge = v.average_rating >= 4.5 
        ? '<span class="badge bg-success ms-2">Top Rated</span>' 
        : "";

      return `
        <div class="card mb-4 p-3 shadow-sm">
          <div class="row g-0">
            <div class="col-md-3 d-flex align-items-center justify-content-center">
              <img src="${photo}" alt="${v.business_name}" class="rounded" style="max-width: 100%; max-height: 140px; object-fit: cover;">
            </div>
            <div class="col-md-9">
              <div class="card-body">
                <h5 class="fw-bold mb-1">
                  <a href="/vendor/${v.phone}" class="text-decoration-none text-dark">${v.business_name}</a>
                  ${badge}
                </h5>
                <p class="mb-1"><strong>📍 City:</strong> ${v.city || "N/A"}</p>
                <p class="mb-1"><strong>🛠 Category:</strong> ${v.category || "N/A"}</p>
                <p class="mb-1"><strong>⭐ Rating:</strong> ${rating}</p>
                <p class="mb-1"><strong>🏠 Address:</strong> ${address || "Not provided"}</p>
                <p class="mb-0"><strong>📞 Phone:</strong> 
                  <a href="tel:${v.phone}" class="text-primary fw-bold">+91 ${v.phone}</a>
                </p>
              </div>
            </div>
          </div>
        </div>`;
    }).join("");
  }

  // Live search
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      fetchVendors(searchInput.value, categoryFilter?.value || "");
    });
  }

  // Category filter
  if (categoryFilter) {
    categoryFilter.addEventListener("change", () => {
      fetchVendors(searchInput?.value || "", categoryFilter.value);
    });
  }

  // Initial load
  fetchVendors();
});

// Trigger search via button click (consistent IDs)
function performSearch() {
  const query = document.getElementById("searchInput")?.value || "";
  const location = document.getElementById("locationInput")?.value || "";
  window.location.href = `/search?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}`;
}

// Callback request (placeholder)
function requestCallback(vendorId) {
  alert("Callback requested for Vendor ID: " + vendorId);
}

// Optional: Get user location only when explicitly called
function useMyLocation() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      console.log("Lat:", pos.coords.latitude, "Lng:", pos.coords.longitude);
      // TODO: send coords to backend for nearby vendor filtering
    });
  } else {
    alert("Geolocation is not supported by this browser.");
  }
}
</script>
