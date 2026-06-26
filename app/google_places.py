import time

import requests

# Two public Overpass mirrors. The main overpass-api.de instance is
# notorious for throttling/blocking requests from cloud & CI IP ranges.
# Falling back to a second mirror makes this much more reliable from Render.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Overpass's fair-use policy asks clients to identify themselves. Requests
# with the default "python-requests/x.x" User-Agent get throttled much more
# aggressively than ones that identify the app.
HEADERS = {
    "User-Agent": "RestroFinder/1.0 (https://the-hungry-bird.onrender.com)"
}

# A bounding box around Bengaluru. Querying by bounding box is faster and
# far more reliable than `area[name="Bengaluru"]->.searchArea;`, which makes
# Overpass resolve administrative boundaries first and is much more likely
# to time out or get rate-limited on the shared public instance.
BENGALURU_BBOX = (12.83, 77.46, 13.14, 77.78)  # south, west, north, east

OVERPASS_QUERY = f"""
[out:json][timeout:25];
node["amenity"="restaurant"]{BENGALURU_BBOX};
out center 100;
"""

# The Overpass query itself never changes — it always pulls every
# restaurant in the bbox, and filtering happens afterwards in Python. So
# there's no reason to re-hit Overpass on every page load / filter change.
# A short in-memory cache cuts request volume drastically, which is the
# single biggest lever for avoiding the rate limit.
_CACHE = {"elements": None, "fetched_at": 0}
_CACHE_TTL_SECONDS = 600  # 10 minutes


def _fetch_osm_elements():
    now = time.time()
    if _CACHE["elements"] is not None and (now - _CACHE["fetched_at"]) < _CACHE_TTL_SECONDS:
        return _CACHE["elements"]

    last_error = None
    for overpass_url in OVERPASS_URLS:
        for attempt in range(2):  # one retry per mirror before giving up on it
            try:
                response = requests.get(
                    overpass_url,
                    params={"data": OVERPASS_QUERY},
                    headers=HEADERS,
                    timeout=30,
                )
                response.raise_for_status()
                elements = response.json().get("elements", [])
                _CACHE["elements"] = elements
                _CACHE["fetched_at"] = now
                return elements
            except Exception as exc:  # network error, timeout, rate limit, bad JSON, etc.
                last_error = exc
                print(f"Overpass mirror {overpass_url} attempt {attempt + 1} failed: {exc}")
                time.sleep(1.5)

    print(f"Error fetching live OSM data, all mirrors failed: {last_error}")
    # Serve a stale cache rather than nothing, if we have one
    return _CACHE["elements"] or []


def _restaurant_from_osm(element):
    tags = element.get("tags", {})
    name = tags.get("name")
    if not name:
        return None

    cuisine = tags.get("cuisine", "Local").replace(";", ", ").replace("_", " ").title()

    address_parts = [tags.get("addr:housenumber"), tags.get("addr:street")]
    address = " ".join(part for part in address_parts if part) or tags.get("addr:full") or "Bengaluru, India"

    return {
        "id": f"osm-{element.get('id')}",
        "name": name,
        "cuisine": cuisine,
        "area": "Bengaluru (Live OSM Data)",
        "price": "$$",
        "rating": 4.5,
        "distance_km": None,
        "open_now": True,
        "address": address,
        "phone": tags.get("phone", tags.get("contact:phone", "-")),
        "hours": tags.get("opening_hours", "Not listed on OpenStreetMap"),
        "tags": [t for t in [cuisine.lower(), "live", "openstreetmap"] if t],
        "description": f"A {cuisine.lower()} spot in Bengaluru, pulled live from OpenStreetMap.",
        "image": None,
        "maps_url": f"https://www.openstreetmap.org/node/{element.get('id')}" if element.get("id") else "",
    }


def search_osm_restaurants(query=None, cuisine=None, area=None, tag=None, open_now=None, min_rating=0, **kwargs):
    elements = _fetch_osm_elements()

    restaurants = []
    for element in elements:
        restaurant = _restaurant_from_osm(element)
        if restaurant:
            restaurants.append(restaurant)

    if query:
        needle = query.strip().lower()
        if needle:
            restaurants = [
                r for r in restaurants
                if needle in r["name"].lower() or needle in r["cuisine"].lower()
            ]

    if cuisine:
        restaurants = [r for r in restaurants if r["cuisine"].lower() == cuisine.lower()]

    if min_rating:
        restaurants = [r for r in restaurants if r["rating"] >= min_rating]

    return restaurants[:20]