from fastapi import APIRouter, Header, Request

from app.content import repository


router = APIRouter(prefix="/api/admin/v1", tags=["admin-taxonomy"])


@router.get("/categories")
def categories(request: Request, target: str | None = None, x_l_one_admin_token: str | None = Header(default=None)) -> dict:
    request.app.state.authorize(request, x_l_one_admin_token, None, False)
    return {"data": repository.list_categories(target)}


@router.get("/tags")
def tags(request: Request, target: str | None = None, x_l_one_admin_token: str | None = Header(default=None)) -> dict:
    request.app.state.authorize(request, x_l_one_admin_token, None, False)
    return {"data": repository.list_tags(target)}
