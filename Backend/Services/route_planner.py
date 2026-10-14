# Backend/Services/route_planner.py
"""
Hazard-aware route planner (A* over a forecast-scored sea grid).

How it works
------------
1. Build a lat/lon grid over the start-end bounding box (padded) with at most
   ~24 x 24 cells.
2. Fetch, in batched requests, the CURRENT and MAXIMUM-OVER-THE-TRIP wave
   height and wind for every cell (look-ahead = estimated trip time, 12-48 h;
   the worst value is used - a boat may still be out when conditions peak).
3. Cells with no marine coverage are land. Cells exceeding the vessel's
   limits are blocked. Other cells cost distance x (1 + 4 * load^2), where
   load = max(wave/limit, wind/limit), so the route prefers calmer water.
4. A* finds the cheapest path; the path is smoothed with line-of-sight checks
   so it is not a staircase of grid cells.
5. The straight-line route is evaluated too, so the advisory can say what the
   detour buys ("direct route crosses 3.1 m waves").

Limitations (returned in every response): forecast grid resolution is
5-25 km; it does not know about rocks, shoals, nets, traffic separation
schemes or maritime borders. It is a planning aid, not a navigation system.
"""
import asyncio
import heapq
import logging
import math
from typing import Optional

from Tools.marine_tools import get_marine_grid
from Tools.official_alerts import haversine_km
from Tools.openmeteo_weather import get_weather_grid

logger = logging.getLogger(__name__)

VESSEL_LIMITS = {
    # Typical small-craft guidance; conservative on purpose.
    "small": {"label": "Small boat / canoe (< 10 m)", "wave_m": 1.5, "wind_kt": 20.0, "speed_kt": 6.0},
    "medium": {"label": "Mechanised fishing vessel (10-20 m)", "wave_m": 2.5, "wind_kt": 28.0, "speed_kt": 8.0},
    "large": {"label": "Large vessel (> 20 m)", "wave_m": 3.5, "wind_kt": 35.0, "speed_kt": 10.0},
}
MAX_CELLS_PER_SIDE = 24
MIN_RES_DEG = 0.05
MAX_ROUTE_KM = 1500.0
MAX_WINDOW_HOURS = 48
KM_PER_NM = 1.852

LIMITATIONS = (
    "Planning aid only. Forecast grid resolution is about 5-25 km and does not include rocks, shoals, "
    "fishing nets, traffic lanes, restricted areas or maritime borders. Always cross-check official "
    "forecasts and local knowledge."
)


class RouteError(Exception):
    pass


def _grid(start, end):
    lat_min, lat_max = sorted((start[0], end[0]))
    lon_min, lon_max = sorted((start[1], end[1]))
    span = max(lat_max - lat_min, lon_max - lon_min)
    pad = max(0.25, span * 0.3)
    lat_min, lat_max = max(-89.0, lat_min - pad), min(89.0, lat_max + pad)
    lon_min, lon_max = lon_min - pad, lon_max + pad
    res = max(MIN_RES_DEG, max(lat_max - lat_min, lon_max - lon_min) / MAX_CELLS_PER_SIDE)
    rows = int(math.ceil((lat_max - lat_min) / res)) + 1
    cols = int(math.ceil((lon_max - lon_min) / res)) + 1
    return lat_min, lon_min, res, rows, cols


def _cell_of(lat, lon, lat0, lon0, res, rows, cols):
    r = min(rows - 1, max(0, int(round((lat - lat0) / res))))
    c = min(cols - 1, max(0, int(round((lon - lon0) / res))))
    return r, c


def _center(r, c, lat0, lon0, res):
    return lat0 + r * res, lon0 + c * res


def _load(cell: Optional[dict], limits: dict) -> Optional[float]:
    if cell is None:
        return None
    wave = cell.get("wave")
    wind = cell.get("wind")
    parts = []
    if wave is not None:
        parts.append(wave / limits["wave_m"])
    if wind is not None:
        parts.append(wind / limits["wind_kt"])
    return max(parts) if parts else None


def _line_cells(a, b):
    """Grid cells crossed by the segment a->b (Bresenham)."""
    (r0, c0), (r1, c1) = a, b
    dr, dc = abs(r1 - r0), abs(c1 - c0)
    sr, sc = (1 if r1 > r0 else -1), (1 if c1 > c0 else -1)
    err = dr - dc
    cells = []
    r, c = r0, c0
    while True:
        cells.append((r, c))
        if (r, c) == (r1, c1):
            return cells
        e2 = 2 * err
        if e2 > -dc:
            err -= dc
            r += sr
        if e2 < dr:
            err += dr
            c += sc


def _nearest_sea(start_rc, passable, rows, cols, max_ring=4):
    if passable(start_rc):
        return start_rc
    r0, c0 = start_rc
    for ring in range(1, max_ring + 1):
        best = None
        for r in range(r0 - ring, r0 + ring + 1):
            for c in range(c0 - ring, c0 + ring + 1):
                if 0 <= r < rows and 0 <= c < cols and max(abs(r - r0), abs(c - c0)) == ring and passable((r, c)):
                    d = (r - r0) ** 2 + (c - c0) ** 2
                    if best is None or d < best[0]:
                        best = (d, (r, c))
        if best:
            return best[1]
    return None


async def plan_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float,
                     vessel: str = "small") -> dict:
    limits = VESSEL_LIMITS.get(vessel) or VESSEL_LIMITS["small"]
    direct_km = haversine_km(start_lat, start_lon, end_lat, end_lon)
    if direct_km > MAX_ROUTE_KM:
        raise RouteError(f"Route too long ({direct_km:.0f} km). Maximum supported is {MAX_ROUTE_KM:.0f} km.")
    if direct_km < 0.5:
        raise RouteError("Start and destination are the same point.")

    lat0, lon0, res, rows, cols = _grid((start_lat, start_lon), (end_lat, end_lon))
    centers = [(_center(r, c, lat0, lon0, res)) for r in range(rows) for c in range(cols)]
    pts = [(lat, ((lon + 180.0) % 360.0) - 180.0) for lat, lon in centers]

    # Look ahead for the whole trip (estimated from the direct distance with a
    # detour margin), capped at 48 h; beyond that, forecasts are too uncertain.
    est_hours = direct_km / KM_PER_NM / limits["speed_kt"] * 1.3
    window = int(min(MAX_WINDOW_HOURS, max(12, math.ceil(est_hours) + 2)))
    marine, weather = await asyncio.gather(get_marine_grid(pts, hours=window), get_weather_grid(pts, hours=window))
    cells: dict[tuple, Optional[dict]] = {}
    for idx, (m, w) in enumerate(zip(marine, weather)):
        r, c = divmod(idx, cols)
        if m is None:
            cells[(r, c)] = None  # land / no marine coverage
            continue
        wave = max(v for v in (m.get("wave_height"), m.get("wave_height_max_12h")) if v is not None)
        wind_vals = [v for v in ((w or {}).get("wind_speed"), (w or {}).get("wind_speed_max_12h")) if v is not None]
        cells[(r, c)] = {"wave": wave, "wind": max(wind_vals) if wind_vals else None,
                         "wind_missing": not wind_vals}

    def passable(rc, allow_hazard=False):
        cell = cells.get(rc)
        if cell is None:
            return False
        load = _load(cell, limits)
        return allow_hazard or (load is not None and load < 1.0)

    start_rc = _cell_of(start_lat, start_lon, lat0, lon0, res, rows, cols)
    end_rc = _cell_of(end_lat, end_lon, lat0, lon0, res, rows, cols)

    def astar(allow_hazard: bool):
        ok = lambda rc: passable(rc, allow_hazard)
        s = _nearest_sea(start_rc, ok, rows, cols)
        g = _nearest_sea(end_rc, ok, rows, cols)
        if s is None or g is None:
            return None, s, g
        def h(rc):
            a, b = _center(*rc, lat0, lon0, res), _center(*g, lat0, lon0, res)
            return haversine_km(a[0], a[1], b[0], b[1])
        open_heap = [(h(s), 0.0, s)]
        came, best = {}, {s: 0.0}
        while open_heap:
            _, cost, cur = heapq.heappop(open_heap)
            if cur == g:
                path = [cur]
                while cur in came:
                    cur = came[cur]
                    path.append(cur)
                return path[::-1], s, g
            if cost > best.get(cur, math.inf):
                continue
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == dc == 0:
                        continue
                    nxt = (cur[0] + dr, cur[1] + dc)
                    if not (0 <= nxt[0] < rows and 0 <= nxt[1] < cols) or not ok(nxt):
                        continue
                    a, b = _center(*cur, lat0, lon0, res), _center(*nxt, lat0, lon0, res)
                    load = _load(cells[nxt], limits) or 0.0
                    step = haversine_km(a[0], a[1], b[0], b[1]) * (1 + 4 * min(load, 3.0) ** 2)
                    new_cost = cost + step
                    if new_cost < best.get(nxt, math.inf):
                        best[nxt] = new_cost
                        came[nxt] = cur
                        heapq.heappush(open_heap, (new_cost + h(nxt), new_cost, nxt))
        return None, s, g

    path, s_rc, g_rc = astar(allow_hazard=False)
    safe_route_found = path is not None
    if path is None:
        path, s_rc, g_rc = astar(allow_hazard=True)
    if path is None:
        raise RouteError("No sea route found between these points on the forecast grid (land-locked or outside marine coverage).")

    # Line-of-sight smoothing.
    def clear(a, b):
        return all(passable(rc, allow_hazard=not safe_route_found) for rc in _line_cells(a, b))
    smooth = [path[0]]
    i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1 and not clear(path[i], path[j]):
            j -= 1
        smooth.append(path[j])
        i = j

    waypoints = [{"latitude": start_lat, "longitude": start_lon, "label": "Start"}]
    for rc in smooth[1:-1] if len(smooth) > 2 else []:
        lat, lon = _center(*rc, lat0, lon0, res)
        waypoints.append({"latitude": round(lat, 4), "longitude": round(((lon + 180) % 360) - 180, 4)})
    waypoints.append({"latitude": end_lat, "longitude": end_lon, "label": "Destination"})

    def stats(cell_list):
        waves = [cells[rc]["wave"] for rc in cell_list if cells.get(rc) and cells[rc]["wave"] is not None]
        winds = [cells[rc]["wind"] for rc in cell_list if cells.get(rc) and cells[rc]["wind"] is not None]
        land = sum(1 for rc in cell_list if cells.get(rc) is None)
        blocked = sum(1 for rc in cell_list if cells.get(rc) is not None and not passable(rc))
        return {
            "max_wave_m": round(max(waves), 2) if waves else None,
            "max_wind_kt": round(max(winds), 1) if winds else None,
            "land_cells_crossed": land,
            "hazard_cells_crossed": blocked,
        }

    route_cells = []
    for a, b in zip(smooth, smooth[1:]):
        route_cells.extend(_line_cells(a, b))
    distance_km = sum(haversine_km(a["latitude"], a["longitude"], b["latitude"], b["longitude"])
                      for a, b in zip(waypoints, waypoints[1:]))
    direct_cells = _line_cells(start_rc, end_rc)
    route_stats = stats(route_cells)
    direct_stats = stats(direct_cells)

    if not safe_route_found:
        verdict = "NO_SAFE_ROUTE"
        summary = (f"No route stays within limits for a {limits['label'].lower()} "
                   f"(waves < {limits['wave_m']} m, wind < {limits['wind_kt']:.0f} kt) over the next {window} h. "
                   "Do not make this trip now.")
    elif direct_stats["hazard_cells_crossed"] or direct_stats["land_cells_crossed"]:
        verdict = "DETOUR"
        why = []
        if direct_stats["hazard_cells_crossed"]:
            why.append(f"rough water (up to {direct_stats['max_wave_m']} m waves / {direct_stats['max_wind_kt']} kt wind)")
        if direct_stats["land_cells_crossed"]:
            why.append("land")
        summary = (f"Safer route found ({distance_km / KM_PER_NM:.0f} NM vs {direct_km / KM_PER_NM:.0f} NM direct). "
                   f"The direct line crosses {' and '.join(why)}.")
    else:
        verdict = "DIRECT_OK"
        summary = (f"Route is within limits for a {limits['label'].lower()}: max waves "
                   f"{route_stats['max_wave_m']} m, max wind {route_stats['max_wind_kt']} kt over the next {window} h.")

    eta_hours = distance_km / KM_PER_NM / limits["speed_kt"]
    if eta_hours > window:
        summary += (f" WARNING: the trip (~{eta_hours:.0f} h) is longer than the {window} h forecast checked - "
                    "re-plan at sea and stop at intermediate harbours.")

    return {
        "verdict": verdict,
        "summary": summary,
        "safe_route_found": safe_route_found,
        "vessel": {"class": vessel if vessel in VESSEL_LIMITS else "small", **limits},
        "waypoints": waypoints,
        "distance_nm": round(distance_km / KM_PER_NM, 1),
        "direct_distance_nm": round(direct_km / KM_PER_NM, 1),
        "eta_hours": round(distance_km / KM_PER_NM / limits["speed_kt"], 1),
        "route_conditions": route_stats,
        "direct_conditions": direct_stats,
        "grid": {"resolution_deg": round(res, 3), "rows": rows, "cols": cols,
                 "sea_cells": sum(1 for v in cells.values() if v is not None)},
        "forecast_window_hours": window,
        "limitations": LIMITATIONS,
    }
