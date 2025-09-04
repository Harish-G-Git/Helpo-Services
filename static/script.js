// ----------------------------
// Vendor Listing (index.html)
// ----------------------------
document.addEventListener("DOMContentLoaded", function () {
  const vendorList = document.getElementById("vendorList");
  const searchInput = document.getElementById("searchInput");
  const categoryFilter = document.getElementById("categoryFilter");

  // Show loading spinner
  function showLoader() {
    if (!vendorList) return; // skip if not on vendor listing page
    vendorList.innerHTML = `
      <div class="text-center py-4">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>`;
  }

  // Fetch vendors from API
  function fetchVendors(query = "", category = "") {
    if (!vendorList) return;
    showLoader();
    fetch(`/api/vendors?query=${encodeURIComponent(query)}&category=${encodeURIComponent(category)}`)
      .then(res => res.json())
      .then(data => {
        const filtered = data.filter(v => !v.average_rating || v.average_rating >= 4);
        const sorted = filtered.sort((a, b) => (b.average_rating || 0) - (a.average_rating || 0));
        displayVendors(sorted);
      })
      .catch(() => {
        vendorList.innerHTML = "<p class='text-danger text-center'>Failed to load vendor list.</p>";
      });
  }

  // Convert numeric rating → stars
  function getStars(rating) {
    const full = Math.floor(rating);
    const half = rating % 1 >= 0.5;
    let stars = '⭐'.repeat(full);
    if (half) stars += '✩';
    return stars.padEnd(5, '☆');
  }

  // Render vendor cards
  function displayVendors(vendors) {
    if (!vendorList) return;
    if (!vendors.length) {
      vendorList.innerHTML = "<p class='text-muted text-center'>No vendors found.</p>";
      return;
    }

    vendorList.innerHTML = vendors.map(v => {
      const address = [
        v.plot_info, v.building_info, v.street, v.landmark,
        v.area, v.city, v.state, v.pincode
      ].filter(Boolean).join(", ");

      const photo = v.photos ? v.photos.split(",")[0] : "default.jpg";
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
              <img src="/static/uploads/${photo}" alt="${v.business_name}" class="rounded" style="max-width: 100%; max-height: 140px; object-fit: cover;">
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

  // Event listeners for live search + filter
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      fetchVendors(searchInput.value, categoryFilter?.value || "");
    });
  }

  if (categoryFilter) {
    categoryFilter.addEventListener("change", () => {
      fetchVendors(searchInput?.value || "", categoryFilter.value);
    });
  }

  // Initial vendor load (only if vendor list exists)
  if (vendorList) {
    fetchVendors();
  }
});

// ----------------------------
// Callback Form + Modal (all pages)
// ----------------------------
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("callbackForm");
  const modal = document.getElementById("contactModal");

  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!document.getElementById("termsCheck").checked) {
        alert("Please accept Terms & Conditions");
        return;
      }
      fetch("/submit_callback", { method: "POST", body: new FormData(form) })
        .then(res => res.json())
        .then(data => {
          alert(data.message);
          form.reset();
          bootstrap.Modal.getInstance(modal).hide();
        })
        .catch(() => alert("Server error"));
    });
  }

  if (modal) {
    modal.addEventListener("show.bs.modal", e => {
      const btn = e.relatedTarget;
      if (btn) {
        document.getElementById("vendorPhoneInput").value = btn.dataset.phone;
      }
    });
  }
});

// ----------------------------
// Search & Location Helpers
// ----------------------------
function useMyLocation() {
  navigator.geolocation.getCurrentPosition(async (pos) => {
    const lat = pos.coords.latitude, lon = pos.coords.longitude;
    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
    const data = await res.json();
    const city = data.address.city || data.address.town || data.address.village || "";
    document.getElementById("locationInput").value = city;
  });
}

function searchVendors() {
  const q = document.getElementById("searchInput")?.value.trim() || "";
  const city = document.getElementById("locationInput")?.value.trim() || "";
  if (!q && !city) { alert("Please enter a service or location"); return; }
  window.location.href = `/?query=${encodeURIComponent(q)}&location=${encodeURIComponent(city)}`;
}
