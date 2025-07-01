import logging
from typing import List, Dict, Any
from aiogram.types import Message, ContentType
from loader import dp, _
from database import async_session
from sqlalchemy import select, func, cast
from geoalchemy2.types import Geography, Geometry
from models import Route

logger = logging.getLogger(__name__)

DEFAULT_RADIUS_KM = 10.0
NEARBY_ROUTES_LIMIT = 10
SUPPORTED_LANGUAGES = ("en", "ru", "be")

async def get_nearby_routes(
    lat: float,
    lon: float,
    radius_km: float = DEFAULT_RADIUS_KM,
    limit: int = NEARBY_ROUTES_LIMIT
) -> List[Dict[str, Any]]:
    radius_m = radius_km * 1000
    distance_expr = func.ST_DistanceSphere(
        cast(Route.location, Geography),
        func.ST_MakePoint(lon, lat).cast(Geography)
    ).label("distance")
    stmt = (
        select(
            Route.id,
            Route.name_en,
            Route.name_ru,
            Route.name_be,
            func.ST_Y(cast(Route.location, Geometry)).label("lat"),
            func.ST_X(cast(Route.location, Geometry)).label("lon"),
            distance_expr
        )
        .where(
            func.ST_DWithin(
                cast(Route.location, Geography),
                func.ST_MakePoint(lon, lat).cast(Geography),
                radius_m
            )
        )
        .order_by(distance_expr)
        .limit(limit)
    )
    async with async_session() as session:
        result = await session.execute(stmt)
        return result.mappings().all()

@dp.message_handler(content_types=[ContentType.LOCATION])
async def handle_location(message: Message):
    lat = message.location.latitude
    lon = message.location.longitude
    lang_code_full = message.from_user.language_code or ""
    primary_lang = lang_code_full.split("-", 1)[0].lower()
    if primary_lang not in SUPPORTED_LANGUAGES:
        primary_lang = "en"
    lang = primary_lang
    try:
        routes = await get_nearby_routes(lat, lon)
    except Exception:
        logger.exception("Error fetching nearby routes")
        await message.answer(_("An error occurred while fetching routes."))
        return
    if not routes:
        await message.answer(
            _("No nearby routes found within %(radius)d km.") % {"radius": int(DEFAULT_RADIUS_KM)}
        )
        return
    lines = []
    unit = _("km")
    for idx, route in enumerate(routes, start=1):
        name = route.get(f"name_{lang}") or route.get("name_en")
        distance_km = route["distance"] / 1000
        lines.append(f"{idx}. {name} - {distance_km:.1f} {unit}")
    await message.answer("\n".join(lines))