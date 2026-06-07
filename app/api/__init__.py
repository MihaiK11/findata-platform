from .analytics_routes import router as analytics_router
from .assistant_routes import router as assistant_router
from .admin_routes import router as admin_router
from .routes import router as query_router

__all__ = ["analytics_router", "assistant_router", "query_router", "admin_router"]

