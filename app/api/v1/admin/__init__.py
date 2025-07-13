from fastapi import APIRouter
from .endpoints import auth

# ú¡ğï1
admin_router = APIRouter()

# ¡ğ¤Áï1
admin_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["¡ğ-¤Á"]
)

# íïåû vÖ¡!Wï1
# admin_router.include_router(users.router, prefix="/users", tags=["¡ğ-(7¡"])
# admin_router.include_router(agents.router, prefix="/agents", tags=["¡ğ-ã¡"])