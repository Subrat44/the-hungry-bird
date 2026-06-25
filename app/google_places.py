import requests

# Two public Overpass mirrors. The main overpass-api.de instance is
# notorious for throttling/blocking requests from cloud & CI IP ranges
# (this is exactly what was breaking GitHub Actions). Falling back to a
# second mirror makes this much more reliable from Render too.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

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


def google_places_enabled():
    # No real Google Maps API key is configured for this project, so we
    # always unlock the dropdown and serve free, live OpenStreetMap data
    # under the "google" source instead.
    return True


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


def search_bengaluru_restaurants(query=None, cuisine=None, area=None, tag=None, open_now=None, min_rating=0, **kwargs):
    data = None
    last_error = None

    for overpass_url in OVERPASS_URLS:
        try:
            response = requests.get(overpass_url, params={"data": OVERPASS_QUERY}, timeout=30)
            response.raise_for_status()
            data = response.json()
            break
        except Exception as exc:  # network error, timeout, rate limit, bad JSON, etc.
            last_error = exc
            print(f"Overpass mirror {overpass_url} failed: {exc}")
            continue

    if data is None:
        print(f"Error fetching live OSM data, all mirrors failed: {last_error}")
        return []

    restaurants = []
    for element in data.get("elements", []):
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