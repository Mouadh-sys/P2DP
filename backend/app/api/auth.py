from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_items() -> dict[str, list]:
    return {"items": []}
