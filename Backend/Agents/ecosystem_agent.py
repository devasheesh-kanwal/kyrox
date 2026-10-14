# Backend/Agents/ecosystem_agent.py
"""
Ecosystem Agent - threatened marine species RECORDED near the position.

Source: OBIS (Ocean Biodiversity Information System, UNESCO-IOC), red-list
checklist for a ~0.5 deg box around the vessel. These are historical
occurrence records, not live sightings or tracking; the output says so.

Used for bycatch-awareness advice: if critically endangered / endangered
species have been recorded here, the recommendation reminds fishers how to
avoid and release them.
"""
import logging
from typing import Optional

from Services.http_cache import UpstreamError, cached_get_json

logger = logging.getLogger(__name__)

OBIS_REDLIST_URL = "https://api.obis.org/v3/checklist/redlist"
BOX_HALF_DEG = 0.25
CATEGORY_LABELS = {
    "CR": "Critically Endangered",
    "EN": "Endangered",
    "VU": "Vulnerable",
    "NT": "Near Threatened",
}
CATEGORY_RANK = {"CR": 0, "EN": 1, "VU": 2, "NT": 3}

GROUPS = [
    ("Mammalia", "marine mammal", "🐬"),
    ("Elasmobranchii", "shark / ray", "🦈"),
    ("Reptilia", "sea turtle / reptile", "🐢"),
    ("Aves", "seabird", "🕊️"),
    ("Anthozoa", "coral", "🪸"),
    ("Actinopteri", "fish", "🐟"),
    ("Holocephali", "chimaera", "🐟"),
]

BYCATCH_TIPS = {
    "marine mammal": "Avoid setting gillnets near dolphins or porpoises; if entangled, cut the net and release.",
    "shark / ray": "Release sharks, rays and guitarfish alive; many are protected - do not land them.",
    "sea turtle / reptile": "Use turtle excluder devices on trawls; bring entangled turtles aboard gently and release.",
    "coral": "Do not anchor or drag gear on coral reefs.",
    "seabird": "Use bird-scaring lines on longlines.",
}


def _group(record: dict) -> tuple[str, str]:
    # WoRMS files sea turtles under order Testudines, not class Reptilia.
    if record.get("order") == "Testudines" or record.get("class") == "Reptilia":
        return "sea turtle / reptile", "🐢"
    for cls, label, icon in GROUPS:
        if record.get("class") == cls:
            return label, icon
    return "marine species", "🌊"


def _polygon(lat: float, lon: float) -> str:
    s, n = max(-89.9, lat - BOX_HALF_DEG), min(89.9, lat + BOX_HALF_DEG)
    w, e = lon - BOX_HALF_DEG, lon + BOX_HALF_DEG
    return f"POLYGON(({w:.3f} {s:.3f},{e:.3f} {s:.3f},{e:.3f} {n:.3f},{w:.3f} {n:.3f},{w:.3f} {s:.3f}))"


async def ecosystem_agent(latitude: float, longitude: float, limit: int = 25) -> dict:
    # Snap to a 0.1 deg grid so nearby requests share the cache.
    lat, lon = round(latitude, 1), round(longitude, 1)
    try:
        resp = await cached_get_json(OBIS_REDLIST_URL, {"geometry": _polygon(lat, lon), "size": 100},
                                     ttl=7 * 24 * 3600, stale_ttl=30 * 24 * 3600)
    except UpstreamError as exc:
        return {"available": False, "error": str(exc), "species": [], "total": 0}

    results = (resp.data or {}).get("results") or []
    species = []
    for r in results:
        cat = r.get("category")
        if cat not in CATEGORY_LABELS or not r.get("is_marine", True):
            continue
        group, icon = _group(r)
        species.append({
            "scientific_name": r.get("scientificName"),
            "category": cat,
            "category_label": CATEGORY_LABELS[cat],
            "group": group,
            "icon": icon,
            "class": r.get("class"),
            "family": r.get("family"),
            "records": r.get("records"),
            "obis_url": f"https://obis.org/taxon/{r.get('taxonID')}" if r.get("taxonID") else None,
        })
    species.sort(key=lambda s: (CATEGORY_RANK[s["category"]], -(s["records"] or 0)))

    top_groups = []
    for s in species:
        if s["category"] in ("CR", "EN") and s["group"] not in top_groups:
            top_groups.append(s["group"])
    tips = [BYCATCH_TIPS[g] for g in top_groups if g in BYCATCH_TIPS]
    counts = {c: sum(1 for s in species if s["category"] == c) for c in CATEGORY_LABELS}

    return {
        "available": True,
        "source": "OBIS (Ocean Biodiversity Information System) - historical occurrence records, not live tracking",
        "area": {"latitude": lat, "longitude": lon, "half_size_deg": BOX_HALF_DEG},
        "total": len(species),
        "counts": counts,
        "species": species[:limit],
        "bycatch_tips": tips,
        "stale": resp.stale,
    }


def ecosystem_summary(eco: Optional[dict]) -> Optional[str]:
    if not eco or not eco.get("available") or not eco.get("total"):
        return None
    c = eco["counts"]
    serious = c.get("CR", 0) + c.get("EN", 0)
    if not serious:
        return None
    names = [s["scientific_name"] for s in eco["species"] if s["category"] in ("CR", "EN")][:3]
    return (f"{serious} critically endangered / endangered species have been recorded in this area "
            f"(e.g. {', '.join(names)}). {eco['bycatch_tips'][0] if eco.get('bycatch_tips') else ''}").strip()
