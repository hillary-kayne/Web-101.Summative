if (!Auth.isLoggedIn()) {
  window.location.href = "/auth.html";
}

const DEFAULT_WEIGHTS = {
  cotton_tshirt: 0.2, jeans: 0.8, wool_sweater: 0.6, synthetic_jacket: 0.9,
  dress: 0.4, shoes: 0.9, bedding_linens: 1.2, other: 0.5,
};

document.getElementById("username-label").textContent = Auth.getUsername() || "";
document.getElementById("entry-date").valueAsDate = new Date();

document.getElementById("logout-btn").addEventListener("click", () => {
  Auth.clearSession();
  window.location.href = "/";
});

const categorySelect = document.getElementById("category");
const customCategoryField = document.getElementById("custom-category-field");
const weightInput = document.getElementById("weight");

function updateCategoryUI() {
  const val = categorySelect.value;
  customCategoryField.classList.toggle("hidden", val !== "other");
  const defaultKg = DEFAULT_WEIGHTS[val] ?? 0.5;
  weightInput.placeholder = `Default: ${defaultKg} kg`;
}
categorySelect.addEventListener("change", updateCategoryUI);
updateCategoryUI();

const money = (n) => `£${Number(n).toFixed(2)}`;
const num = (n, decimals = 0) => Number(n).toLocaleString(undefined, { maximumFractionDigits: decimals });

async function loadSummary() {
  try {
    const s = await Api.summary();
    document.getElementById("total-earned").textContent = money(s.total_earned);
    document.getElementById("total-water").textContent = `${num(s.total_water_l)} L water`;
    document.getElementById("total-co2").textContent = `${num(s.total_co2_kg, 1)} kg CO2e avoided`;
    document.getElementById("drinking-days").textContent =
      `≈ ${num(s.drinking_water_days_equivalent, 1)} days of an adult's drinking water`;

    const wk = s.trend_week;
    if (wk.length >= 2) {
      const last = wk[wk.length - 1], prev = wk[wk.length - 2];
      document.getElementById("trend-earned").textContent =
        `This week: ${money(last.earned)} · Last week: ${money(prev.earned)}`;
    } else if (wk.length === 1) {
      document.getElementById("trend-earned").textContent = `This week: ${money(wk[0].earned)}`;
    } else {
      document.getElementById("trend-earned").textContent = "Log your first item to start a trend";
    }
  } catch (err) {
    console.error(err);
  }
}

function entryRowHtml(e) {
  const methodLabel = e.method === "resold" ? "Resold" : "Recycled";
  const payer = e.payer_name ? ` · ${escapeHtml(e.payer_name)}` : "";
  return `
    <div class="entry-row" data-id="${e.id}">
      <div class="entry-main">
        <div class="entry-desc">${escapeHtml(e.description)}</div>
        <div class="entry-meta">${e.entry_date} · ${methodLabel}${payer} · ${e.weight_kg} kg</div>
      </div>
      <div class="entry-figures">
        <span class="earned">${money(e.amount_earned)}</span>
        <span class="saved">${num(e.water_saved_l)} L · ${num(e.co2_saved_kg, 1)} kg CO2e</span>
        <button class="btn btn-danger btn-sm" data-delete="${e.id}">Delete</button>
      </div>
    </div>
  `;
}

function currentFilters() {
  const f = {};
  const search = document.getElementById("f-search").value.trim();
  const category = document.getElementById("f-category").value;
  const method = document.getElementById("f-method").value;
  const from = document.getElementById("f-from").value;
  const to = document.getElementById("f-to").value;
  const sort = document.getElementById("f-sort").value;
  if (search) f.q = search;
  if (category) f.category = category;
  if (method) f.method = method;
  if (from) f.date_from = from;
  if (to) f.date_to = to;
  if (sort) f.sort = sort;
  return f;
}

async function loadEntries() {
  const list = document.getElementById("entries-list");
  const empty = document.getElementById("empty-state");
  try {
    const data = await Api.listEntries(currentFilters());
    list.innerHTML = data.entries.map(entryRowHtml).join("");
    empty.style.display = data.entries.length ? "none" : "block";
    list.querySelectorAll("[data-delete]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this entry?")) return;
        await Api.deleteEntry(btn.dataset.delete);
        await Promise.all([loadEntries(), loadSummary()]);
      });
    });
  } catch (err) {
    list.innerHTML = `<div class="banner banner-warn">${escapeHtml(err.message)}</div>`;
  }
}

let filterDebounce = null;
["f-search"].forEach((id) =>
  document.getElementById(id).addEventListener("input", () => {
    clearTimeout(filterDebounce);
    filterDebounce = setTimeout(loadEntries, 300);
  })
);
["f-category", "f-method", "f-from", "f-to", "f-sort"].forEach((id) =>
  document.getElementById(id).addEventListener("change", loadEntries)
);
document.getElementById("clear-filters-btn").addEventListener("click", () => {
  ["f-search", "f-from", "f-to"].forEach((id) => (document.getElementById(id).value = ""));
  ["f-category", "f-method"].forEach((id) => (document.getElementById(id).value = ""));
  document.getElementById("f-sort").value = "date";
  loadEntries();
});

document.getElementById("entry-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorBox = document.getElementById("entry-error");
  errorBox.innerHTML = "";

  const categoryVal = categorySelect.value === "other"
    ? (document.getElementById("custom-category").value.trim() || "other")
    : categorySelect.value;

  const payload = {
    description: document.getElementById("description").value.trim(),
    category: categoryVal,
    method: document.getElementById("method").value,
    payer_name: document.getElementById("payer").value.trim(),
    entry_date: document.getElementById("entry-date").value,
  };
  const weightVal = weightInput.value;
  if (weightVal) payload.weight_kg = weightVal;
  const amountVal = document.getElementById("amount").value;
  if (amountVal) payload.amount_earned = amountVal;

  try {
    await Api.createEntry(payload);
    e.target.reset();
    document.getElementById("entry-date").valueAsDate = new Date();
    updateCategoryUI();
    await Promise.all([loadEntries(), loadSummary()]);
  } catch (err) {
    errorBox.innerHTML = `<div class="banner banner-warn">${escapeHtml(err.message)}</div>`;
  }
});

loadSummary();
loadEntries();
