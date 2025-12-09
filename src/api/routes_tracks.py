# src/api/routes_tracks.py
from fastapi import APIRouter

router = APIRouter(tags=["tracks"])

@router.get("/tracks")
def get_tracks():
    return {"plannedTracks": []}
