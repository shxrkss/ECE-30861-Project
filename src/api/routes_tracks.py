# src/api/routes_tracks.py

from fastapi import APIRouter

router = APIRouter(tags=["tracks"])

@router.get("/tracks")
def get_tracks():
    return {"plannedTracks": ["Access Control"]}

#---------------------OLD CODE BELOW---------------

# from fastapi import APIRouter

# router = APIRouter(tags=["tracks"])

# @router.get("/tracks")
# def get_tracks():
#     return {"plannedTracks": []}
