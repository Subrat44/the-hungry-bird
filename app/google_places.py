import os
from typing import Any

import httpx

BENGALURU_CENTER = {"latitude": 12.9716, "longitude": 77.5946}
PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.googleMapsUri",
        "places.internationalPhoneNumber",
        "places.priceLevel",
        "places.rating",
        "places.currentOpeningHours",
        "places.types",
    ]
)


def google_places_enabled() -> bool:
    return bool(os.getenv("GOOGLE_MAPS_API_KEY"))


def build_bengaluru_query(q: str | None, cuisine: str | None, area: str | None, tag: str | None) -> str:
    terms = [item for item in [q, cuisine, tag] if item]
    base = " ".join(terms) if terms else "Indian restaurant"
    neighborhood = f" in {area}" if area else ""
    return f"{base}{neighborhood}, Bengaluru, Karnataka, India"


def map_price(price_level: str | None) -> str:
    return {
        "PRICE_LEVEL_INEXPENSIVE": "$",
        "PRICE_LEVEL_MODERATE": "$$",
        "PRICE_LEVEL_EXPENSIVE": "$$$",
        "PRICE_LEVEL_VERY_EXPENSIVE": "$$$",
    }.get(price_level or "", "$$")


def map_place(place: dict[str, Any]) -> dict[str, Any]:
    name = place.get("displayName", {}).get("text", "Unnamed restaurant")
    types = [item.replace("_", " ") for item in place.get("types", [])[:4]]

    return {
        "id": f"google-{place.get('id', name).replace(' ', '-').lower()}",
        "name": name,
        "cuisine": "Indian",
        "area": "Bengaluru",
        "price": map_price(place.get("priceLevel")),
        "rating": float(place.get("rating") or 0),
        "distance_km": None,
        "open_now": place.get("currentOpeningHours", {}).get("openNow"),
        "address": place.get("formattedAddress", "Bengaluru, Karnataka, India"),
        "phone": place.get("internationalPhoneNumber") or "-",
        "hours": "See Google Maps for current hours",
        "tags": types or ["restaurant"],
        "description": "Google Maps restaurant result for Bengaluru.",
        "image": "",
        "maps_url": place.get("googleMapsUri", ""),
        "source": "google_maps",
    }


def search_bengaluru_restaurants(
    q: str | None = None,
    cuisine: str | None = None,
    area: str | None = None,
    tag: str | None = None,
    open_now: bool | None = None,
    min_rating: float = 0,
) -> dict[str, Any]:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {
            "configured": False,
            "count": 0,
            "restaurants": [],
            "message": "Set GOOGLE_MAPS_API_KEY to search Google Maps restaurants in Bengaluru.",
        }

    payload: dict[str, Any] = {
        "textQuery": build_bengaluru_query(q, cuisine, area, tag),
        "includedType": "restaurant",
        "strictTypeFiltering": True,
        "languageCode": "en",
        "regionCode": "IN",
        "maxResultCount": 20,
        "locationBias": {
            "circle": {
                "center": BENGALURU_CENTER,
                "radius": 35000.0,
            }
        },
    }

    if open_now is True:
        payload["openNow"] = True

    response = httpx.post(
        PLACES_TEXT_SEARCH_URL,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        },
        timeout=10,
    )
    response.raise_for_status()

    restaurants = [map_place(place) for place in response.json().get("places", [])]
    if min_rating:
        restaurants = [restaurant for restaurant in restaurants if restaurant["rating"] >= min_rating]

    return {
        "configured": True,
        "count": len(restaurants),
        "restaurants": restaurants,
        "message": "Results from Google Places Text Search.",
    }
