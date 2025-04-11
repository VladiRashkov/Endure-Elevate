from .user import user_routes
from .token import token_routes
from .activity import activity_routes

ROUTES = [
    user_routes,
    token_routes,
    activity_routes,
]