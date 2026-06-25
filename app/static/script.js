const form = document.querySelector("#filters");
const resultsEl = document.querySelector("#results");
const emptyState = document.querySelector("#empty-state");
const resultCount = document.querySelector("#result-count");
const tagStrip = document.querySelector(".tag-strip");
let activeTag = "";

const detail = {
  image: document.querySelector("#detail-image"),
  area: document.querySelector("#detail-area"),
  name: document.querySelector("#detail-name"),
  description: document.querySelector("#detail-description"),
  address: document.querySelector("#detail-address"),
  hours: document.querySelector("#detail-hours"),
  phone: document.querySelector("#detail-phone"),
  maps: document.querySelector("#detail-maps"),
  tags: document.querySelector("#detail-tags"),
};
const sourceMessage = document.querySelector("#source-message");

function clearDetail(message = "Choose a restaurant") {
  detail.image.src = "/static/bengaluru-restaurant.svg";
  detail.image.alt = "Bengaluru restaurant placeholder";
  detail.area.textContent = "Bengaluru restaurants";
  detail.name.textContent = message;
  detail.description.textContent = "Adjust the filters or switch to demo data to see restaurant details.";
  detail.address.textContent = "-";
  detail.hours.textContent = "-";
  detail.phone.textContent = "-";
  detail.maps.textContent = "-";
  detail.tags.replaceChildren();
}

function paramsFromForm() {
  const params = new URLSearchParams();
  const values = new FormData(form);

  for (const [key, value] of values.entries()) {
    if (key === "open_now") continue;
    if (String(value).trim()) params.set(key, value);
  }

  if (document.querySelector("#open_now").checked) {
    params.set("open_now", "true");
  }

  if (activeTag) {
    params.set("tag", activeTag);
  }

  return params;
}

function addOption(select, value) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = value;
  select.appendChild(option);
}

function tagButton(tag) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "tag-button";
  button.dataset.tag = tag;
  button.textContent = tag;
  button.addEventListener("click", () => {
    activeTag = activeTag === button.dataset.tag ? "" : button.dataset.tag;
    document.querySelectorAll(".tag-button").forEach((item) => {
      item.classList.toggle("active", item.dataset.tag === activeTag);
    });
    loadRestaurants();
  });
  return button;
}

function renderStars(rating) {
  return rating ? `${rating.toFixed(1)} ★` : "No rating";
}

function restaurantCard(restaurant, index) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "restaurant-card";
  button.dataset.id = restaurant.id;
  button.innerHTML = `
    <span class="card-rank">${String(index + 1).padStart(2, "0")}</span>
    <span class="card-main">
      <strong>${restaurant.name}</strong>
      <span>${restaurant.cuisine} · ${restaurant.area}</span>
    </span>
    <span class="card-meta">
      <span>${renderStars(restaurant.rating)}</span>
      <span>${restaurant.distance_km ? `${restaurant.distance_km.toFixed(1)} km` : "Bengaluru"}</span>
      <span>${restaurant.price}</span>
    </span>
    <span class="status ${restaurant.open_now ? "open" : "closed"}">
      ${restaurant.open_now === true ? "Open" : restaurant.open_now === false ? "Closed" : "Maps"}
    </span>
  `;
  button.addEventListener("click", () => selectRestaurant(restaurant, button));
  return button;
}

function selectRestaurant(restaurant, selectedButton) {
  document.querySelectorAll(".restaurant-card").forEach((card) => {
    card.classList.toggle("selected", card === selectedButton);
  });

  detail.image.src = restaurant.image || "/static/bengaluru-restaurant.svg";
  detail.image.alt = `${restaurant.name} restaurant`;
  detail.area.textContent = `${restaurant.cuisine} · ${restaurant.area} · ${restaurant.price}`;
  detail.name.textContent = restaurant.name;
  detail.description.textContent = restaurant.description;
  detail.address.textContent = restaurant.address;
  detail.hours.textContent = restaurant.hours;
  detail.phone.textContent = restaurant.phone;
  detail.maps.innerHTML = restaurant.maps_url ? `<a href="${restaurant.maps_url}" target="_blank" rel="noreferrer">Open in Google Maps</a>` : "-";
  detail.tags.innerHTML = restaurant.tags.map((tag) => `<span>${tag}</span>`).join("");
}

async function loadRestaurants() {
  const response = await fetch(`/api/restaurants?${paramsFromForm().toString()}`);
  const data = await response.json();

  resultsEl.replaceChildren();
  resultCount.textContent = `${data.count} ${data.count === 1 ? "spot" : "spots"}`;
  emptyState.hidden = data.count !== 0;
  sourceMessage.hidden = !data.message;
  sourceMessage.textContent = data.message || "";

  data.restaurants.forEach((restaurant, index) => {
    resultsEl.appendChild(restaurantCard(restaurant, index));
  });

  if (data.restaurants.length) {
    resultsEl.firstElementChild.click();
  } else {
    clearDetail(data.configured === false ? "Google Maps needs an API key" : "No restaurant selected");
  }
}

async function loadMeta() {
  const response = await fetch("/api/meta");
  const meta = await response.json();
  const sourceSelect = document.querySelector("#source");
  const googleOption = sourceSelect.querySelector('option[value="google"]');

  if (!meta.google_places_enabled) {
    googleOption.textContent = "Google Maps (needs API key)";
    googleOption.disabled = true;
    sourceSelect.value = "local";
    sourceMessage.hidden = false;
    sourceMessage.textContent = "Demo data is showing now. Add GOOGLE_MAPS_API_KEY to enable live Google Maps results.";
  }

  meta.cuisines.forEach((cuisine) => addOption(document.querySelector("#cuisine"), cuisine));
  meta.areas.forEach((area) => addOption(document.querySelector("#area"), area));
  meta.tags.slice(0, 10).forEach((tag) => tagStrip.appendChild(tagButton(tag)));
}

form.addEventListener("input", loadRestaurants);
form.addEventListener("change", loadRestaurants);

loadMeta().then(loadRestaurants);
