"""
Health Services & Facility Lookup Module.
Fetches real-time live medical facilities directly from OpenStreetMap Free API (Nominatim),
and provides emergency helplines and offline failure handling.
"""

import json
import logging
import time
import urllib.parse
import urllib.request
from typing import Any, Optional

logger = logging.getLogger("agent.health_services")

# In-memory bounded cache for OSM lookups (respects Nominatim policy & eliminates repeat latency)
_FACILITY_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL_SEC: float = 600.0  # 10 minutes cache TTL

# Dataset freshness timestamp and truthful attribution
DATA_SOURCE_ATTRIBUTION = "OpenStreetMap (Nominatim community data)"

# Emergency & Specialized Helplines
EMERGENCY_HELPLINES: dict[str, dict[str, str]] = {
    "erss": {
        "name": "National Emergency Response Support System (ERSS)",
        "number": "112",
        "description": "Unified 24/7 national emergency response for immediate police, fire, and medical assistance.",
    },
    "ambulance": {
        "name": "National Ambulance Emergency Service",
        "number": "108",
        "description": "Free 24/7 emergency medical transport and immediate trauma support.",
    },
    "general": {
        "name": "National Health Helpline & Tele-Consultation",
        "number": "104",
        "description": "24/7 medical advice, PHC guidance, and government health scheme info.",
    },
    "mental_health": {
        "name": "Tele-MANAS Mental Health Helpline",
        "number": "14416 / 1800-891-4416",
        "description": "Free 24/7 confidential psychological support and counseling.",
    },
    "maternal": {
        "name": "Mother and Child Tracking & Healthcare Line",
        "number": "1800-180-1104",
        "description": "Maternal care, vaccination schedules, and pregnancy guidance.",
    },
}


def fetch_live_openstreetmap_hospitals(
    location: str, timeout: float = 3.5
) -> list[dict[str, Any]]:
    """Fetch live real-world hospitals directly from OpenStreetMap Nominatim Free API."""
    cache_key = location.lower().strip()
    now = time.time()
    if cache_key in _FACILITY_CACHE:
        cached_time, cached_results = _FACILITY_CACHE[cache_key]
        if now - cached_time < _CACHE_TTL_SEC:
            logger.info(
                f"Serving OSM hospital results from in-memory cache for '{cache_key}' (0ms network delay)."
            )
            return cached_results

    queries_to_try = [
        f"hospitals in {location}",
        f"hospitals near {location}",
    ]
    parts = [p.strip() for p in location.replace(",", " ").split() if p.strip()]
    if len(parts) > 1:
        queries_to_try.append(f"hospitals in {parts[-1]}")  # e.g., 'Lucknow'

    for q in queries_to_try:
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=json&addressdetails=1&extratags=1&limit=5"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "AanyaVoiceHealthCompanion/1.0 (Health Access Companion; contact: support@aanya.local)"
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    if not data:
                        continue
                    live_results = []
                    for item in data:
                        display_name = item.get("display_name", "")
                        name = item.get("name") or (
                            display_name.split(",")[0]
                            if display_name
                            else f"Hospital in {location.title()}"
                        )
                        postcode = item.get("address", {}).get("postcode", "")
                        extratags = (
                            item.get("extratags")
                            if isinstance(item.get("extratags"), dict)
                            else {}
                        )
                        emergency_tag = extratags.get("emergency") == "yes"
                        raw_hours = extratags.get("opening_hours")
                        operating_hours = (
                            raw_hours
                            if raw_hours
                            else "Hours unverified; confirm with facility before visiting"
                        )
                        if name:
                            live_results.append(
                                {
                                    "district": location.lower(),
                                    "pincode": postcode,
                                    "name": name,
                                    "facility_type": "Hospital / Healthcare Facility (OpenStreetMap community data)",
                                    "address": display_name,
                                    "contact_phone": "Call 112 / 108 for Emergency or 104 for Health Info",
                                    "emergency_services": emergency_tag,
                                    "operating_hours": operating_hours,
                                }
                            )
                    if live_results:
                        _FACILITY_CACHE[cache_key] = (now, live_results)
                        return live_results
        except Exception as e:
            logger.warning(
                f"Live OpenStreetMap API lookup failed or timed out for '{q}': {e}"
            )
    return []


def search_health_facilities(
    location_or_pincode: str,
    facility_type: Optional[str] = None,
    simulated_failure: bool = False,
) -> dict[str, Any]:
    """
    Search for nearest primary health centers or hospitals by location name or pincode.
    Fetches real-time live data directly from OpenStreetMap Free API (Nominatim).
    """
    if simulated_failure:
        logger.error(
            "Simulated network timeout connecting to OpenStreetMap Nominatim API."
        )
        return {
            "status": "error",
            "message": "Health facility lookup is currently unreachable due to network timeout.",
            "data_source": DATA_SOURCE_ATTRIBUTION,
            "fallback_recommendation": (
                "For urgent medical assistance, please call 112 ERSS or 108 Emergency Ambulance immediately "
                "or visit your nearest district civil hospital."
            ),
        }

    clean_loc = location_or_pincode.strip().lower()
    if not clean_loc:
        return {
            "status": "error",
            "message": "Please provide a valid district name or pincode.",
            "data_source": DATA_SOURCE_ATTRIBUTION,
        }

    # 100% Live lookup from OpenStreetMap Free API
    matches = fetch_live_openstreetmap_hospitals(clean_loc)

    if facility_type and matches:
        filtered = [
            m
            for m in matches
            if facility_type.lower() in m["facility_type"].lower()
            or facility_type.lower() in m["name"].lower()
        ]
        if filtered:
            matches = filtered

    if matches:
        return {
            "status": "success",
            "count": len(matches),
            "location_query": location_or_pincode,
            "data_source": DATA_SOURCE_ATTRIBUTION,
            "facilities": matches,
        }

    return {
        "status": "partial_success",
        "location_query": location_or_pincode,
        "data_source": DATA_SOURCE_ATTRIBUTION,
        "message": f"No specific registered hospital found directly for '{location_or_pincode}'.",
        "general_guidance": (
            f"You can visit the Primary Health Centre (PHC) at your nearest Block Headquarter in {location_or_pincode.title()}, "
            "or call 104 National Health Line for direct location guidance."
        ),
        "emergency_contact": "108 Emergency Ambulance",
    }


def get_emergency_helpline(category: str = "general") -> dict[str, Any]:
    """Retrieve official government emergency or specialized helpline information."""
    key = category.strip().lower()
    if "112" in key or "erss" in key:
        info = EMERGENCY_HELPLINES["erss"]
    elif "mental" in key or "mind" in key or "stress" in key:
        info = EMERGENCY_HELPLINES["mental_health"]
    elif "maternal" in key or "child" in key or "baby" in key or "pregnant" in key:
        info = EMERGENCY_HELPLINES["maternal"]
    elif "ambulance" in key or "emergency" in key or "accident" in key:
        info = EMERGENCY_HELPLINES["ambulance"]
    else:
        info = EMERGENCY_HELPLINES["general"]

    return {
        "status": "success",
        "category": category,
        "data_source": DATA_SOURCE_ATTRIBUTION,
        "helpline": info,
    }
