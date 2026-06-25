from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.data import RESTAURANTS, all_areas, all_cuisines, all_tags
from app.google_places import google_places_enabled, search_bengaluru_restaurants

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Restro Finder",
    description="A small restaurant finder with an in-process static catalogue.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")


@app.get("/")
def home(request: Request):
    return FileResponse(APP_DIR / "templates" / "index.html")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "restaurants": len(RESTAURANTS)}


@app.get("/api/meta")
def metadata():
    return {
        "cuisines": all_cuisines(),
        "areas": sorted(set(all_areas() + ["Bengaluru", "Indiranagar", "Koramangala", "Whitefield", "Jayanagar"])),
        "tags": all_tags(),
        "prices": ["$", "$$", "$$$"],
        "google_places_enabled": google_places_enabled(),
        "default_location": "Bengaluru, India",
    }


@app.get("/api/restaurants")
def list_restaurants(
    q: Annotated[str | None, Query(description="Search name, cuisine, area, description, or tags")] = None,
    cuisine: str | None = None,
    area: str | None = None,
    price: str | None = None,
    open_now: bool | None = None,
    tag: str | None = None,
    min_rating: float = Query(0, ge=0, le=5),
    max_distance_km: float | None = Query(None, gt=0),
    sort: str = Query("rating", pattern="^(rating|distance|name)$"),
    source: str = Query("local", pattern="^(local|google)$"),
):
    if source == "google":
        restaurants = search_bengaluru_restaurants(
            query=q,
            cuisine=cuisine,
            area=area,
            tag=tag,
            open_now=open_now,
            min_rating=min_rating,
        )
        message = None
        if not restaurants:
            message = (
                "Live OpenStreetMap data came back empty. The free Overpass API "
                "is sometimes rate-limited from cloud hosts (Render, GitHub Actions, "
                "etc.) — try again in a moment or switch to Demo data."
            )
        return {
            "count": len(restaurants),
            "restaurants": restaurants,
            "message": message,
        }

    results = list(RESTAURANTS)

    if q:
        needle = q.strip().lower()
        results = [
            restaurant
            for restaurant in results
            if needle in " ".join(
                [
                    restaurant["name"],
                    restaurant["cuisine"],
                    restaurant["area"],
                    restaurant["description"],
                    " ".join(restaurant["tags"]),
                ]
            ).lower()
        ]

    if cuisine:
        results = [restaurant for restaurant in results if restaurant["cuisine"].lower() == cuisine.lower()]
    if area:
        results = [restaurant for restaurant in results if restaurant["area"].lower() == area.lower()]
    if price:
        results = [restaurant for restaurant in results if restaurant["price"] == price]
    if open_now is not None:
        results = [restaurant for restaurant in results if restaurant["open_now"] is open_now]
    if tag:
        results = [restaurant for restaurant in results if tag.lower() in [item.lower() for item in restaurant["tags"]]]
    if min_rating:
        results = [restaurant for restaurant in results if restaurant["rating"] >= min_rating]
    if max_distance_km is not None:
        results = [restaurant for restaurant in results if restaurant["distance_km"] <= max_distance_km]

    if sort == "distance":
        results.sort(key=lambda restaurant: restaurant["distance_km"] or 999)
    elif sort == "name":
        results.sort(key=lambda restaurant: restaurant["name"])
    else:
        results.sort(key=lambda restaurant: (-restaurant["rating"], restaurant["distance_km"]))

    return {"count": len(results), "restaurants": results}


@app.get("/api/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: str):
    for restaurant in RESTAURANTS:
        if restaurant["id"] == restaurant_id:
            return restaurant
    raise HTTPException(status_code=404, detail="Restaurant not found")