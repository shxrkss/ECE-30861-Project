# src/api/routes_tracks.py

#Santa's Changes to the file
# from fastapi import APIRouter

# router = APIRouter(tags=["tracks"])

# @router.get("/tracks")
# def get_tracks():
#     return {"plannedTracks": ["Access Control"]}

#---------------------OLD CODE BELOW---------------

from fastapi import APIRouter

router = APIRouter(tags=["tracks"])

@router.get("/tracks")
def get_tracks():
    return {"plannedTracks": []}
