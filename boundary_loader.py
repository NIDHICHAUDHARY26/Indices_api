"""
Boundary Loader
- Shapefile  → fast State/District/Taluka dropdowns + LGD code lookup
- GEE Assets → accurate geometry using your if/elif/else hierarchy with lgd codes
  (taluka > district > state, exactly as in your indices.py AOI logic)
"""

import geopandas as gpd
import json
import unicodedata
import re
from typing import Optional
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    SHAPEFILE_PATH, COL_TALUKA, COL_DISTRICT, COL_STATE,
    COL_LGD_T, COL_LGD_D, COL_LGD_S, EE_SHP
)

_gdf: Optional[gpd.GeoDataFrame] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    if not text: return ""
    text = unicodedata.normalize("NFD", str(text).lower().strip())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text)


def load_shapefile() -> gpd.GeoDataFrame:
    global _gdf
    if _gdf is not None:
        return _gdf
    if not os.path.exists(SHAPEFILE_PATH):
        raise FileNotFoundError(f"Shapefile not found: {SHAPEFILE_PATH}")
    _gdf = gpd.read_file(SHAPEFILE_PATH)
    if _gdf.crs is None or _gdf.crs.to_epsg() != 4326:
        _gdf = _gdf.to_crs(epsg=4326)
    _gdf["_tn"] = _gdf[COL_TALUKA].apply(_norm)
    _gdf["_dn"] = _gdf[COL_DISTRICT].apply(_norm)
    _gdf["_sn"] = _gdf[COL_STATE].apply(_norm)
    return _gdf


def _get_row(taluka=None, district=None, state=None):
    """Best-matching shapefile row."""
    gdf  = load_shapefile()
    mask = gdf.index.notna()
    if taluka:   mask = mask & gdf["_tn"].str.contains(_norm(taluka),   na=False)
    if district: mask = mask & gdf["_dn"].str.contains(_norm(district), na=False)
    if state:    mask = mask & gdf["_sn"].str.contains(_norm(state),    na=False)
    res = gdf[mask]
    return res.iloc[0] if not res.empty else None


# ─── Dropdown functions (shapefile — instant) ─────────────────────────────────

def get_states() -> list:
    return sorted(load_shapefile()[COL_STATE].dropna().unique().tolist())


def get_districts(state: str) -> list:
    gdf = load_shapefile()
    return sorted(gdf[gdf["_sn"].str.contains(_norm(state), na=False)][COL_DISTRICT].dropna().unique().tolist())


def get_talukas(district: str, state: str = None) -> list:
    gdf  = load_shapefile()
    mask = gdf["_dn"].str.contains(_norm(district), na=False)
    if state: mask = mask & gdf["_sn"].str.contains(_norm(state), na=False)
    return sorted(gdf[mask][COL_TALUKA].dropna().unique().tolist())


def search_location(query: str, limit: int = 20) -> list:
    gdf = load_shapefile()
    q   = _norm(query)
    mask = (gdf["_tn"].str.contains(q, na=False) |
            gdf["_dn"].str.contains(q, na=False) |
            gdf["_sn"].str.contains(q, na=False))
    return [
        {
            "taluka":   r[COL_TALUKA],
            "district": r[COL_DISTRICT],
            "state":    r[COL_STATE],
            "lgd_t":    str(r.get(COL_LGD_T, "")),
            "lgd_d":    str(r.get(COL_LGD_D, "")),
            "lgd_s":    str(r.get(COL_LGD_S, "")),
        }
        for _, r in gdf[mask].head(limit).iterrows()
    ]


def get_lgd_codes(taluka=None, district=None, state=None) -> dict:
    """Get LGD codes from shapefile for given names."""
    row = _get_row(taluka, district, state)
    if row is None:
        return {}
    return {
        "lgd_t":  str(row.get(COL_LGD_T, "")).strip(),
        "lgd_d":  str(row.get(COL_LGD_D, "")).strip(),
        "lgd_s":  str(row.get(COL_LGD_S, "")).strip(),
        "name_t": row[COL_TALUKA],
        "name_d": row[COL_DISTRICT],
        "name_s": row[COL_STATE],
    }


# ─── GEE AOI (your if/elif/else hierarchy) ───────────────────────────────────

def _build_gee_aoi(taluka=None, district=None, state=None):
    """
    Build ee.FeatureCollection AOI using LGD codes.
    Hierarchy: taluka > district > state
    Exactly matches your AOI logic from indices.py.
    """
    import ee
    codes = get_lgd_codes(taluka, district, state)
    if not codes:
        raise ValueError(f"Location not found in shapefile: "
                         f"taluka={taluka} district={district} state={state}")

    lgd_t = codes.get("lgd_t", "")
    lgd_d = codes.get("lgd_d", "")
    lgd_s = codes.get("lgd_s", "")

    if taluka and lgd_t:
        aoi   = ee.FeatureCollection(EE_SHP["shp_t"]).filter(ee.Filter.inList("lgd_t", [lgd_t]))
        level = "Taluka"
    elif district and lgd_d:
        aoi   = ee.FeatureCollection(EE_SHP["shp_d"]).filter(ee.Filter.inList("lgd_d", [lgd_d]))
        level = "District"
    elif state and lgd_s:
        aoi   = ee.FeatureCollection(EE_SHP["shp_s"]).filter(ee.Filter.inList("lgd_s", [lgd_s]))
        level = "State"
    else:
        raise ValueError("Provide at least one of: taluka, district, or state")

    return aoi, level, codes


def get_ee_geometry(taluka=None, district=None, state=None):
    """Return ee.Geometry (union) for the AOI. Used for index computation."""
    aoi, _, _ = _build_gee_aoi(taluka, district, state)
    return aoi.geometry()


def get_ee_feature_collection(taluka=None, district=None, state=None):
    aoi, level, codes = _build_gee_aoi(taluka, district, state)
    return aoi, level


# ─── GeoJSON for Leaflet boundary ────────────────────────────────────────────

def get_taluka_geojson(taluka=None, district=None, state=None) -> dict:
    """
    Get GeoJSON boundary + bbox from GEE asset.
    Falls back to shapefile if GEE fails.
    """
    # First try GEE
    try:
        import ee
        aoi, level, codes = _build_gee_aoi(taluka, district, state)
        fc_info    = aoi.getInfo()
        if not fc_info or not fc_info.get("features"):
            raise ValueError("Empty GEE result")

        geom_info  = aoi.geometry().getInfo()
        flat       = _flatten_coords(geom_info.get("coordinates", []))
        if not flat:
            raise ValueError("No coordinates")

        lons = [c[0] for c in flat]
        lats = [c[1] for c in flat]
        return {
            "taluka":   codes.get("name_t", taluka or ""),
            "district": codes.get("name_d", district or ""),
            "state":    codes.get("name_s", state or ""),
            "level":    level,
            "geojson":  {"type": "FeatureCollection", "features": fc_info["features"]},
            "bbox":     {"minx": min(lons), "miny": min(lats),
                         "maxx": max(lons), "maxy": max(lats)},
            "centroid": {"lat": (min(lats)+max(lats))/2,
                         "lon": (min(lons)+max(lons))/2},
        }
    except Exception as e:
        # Fallback to shapefile
        return _geojson_from_shapefile(taluka, district, state, str(e))


def _flatten_coords(coords):
    result = []
    if not coords: return result
    if isinstance(coords[0], (int, float)): return [coords]
    for item in coords:
        result.extend(_flatten_coords(item))
    return result


def _geojson_from_shapefile(taluka, district, state, reason=""):
    row = _get_row(taluka, district, state)
    if row is None:
        return {"error": f"Location not found. GEE error: {reason}"}
    geojson  = json.loads(gpd.GeoSeries([row.geometry]).to_json())
    bounds   = row.geometry.bounds
    centroid = row.geometry.centroid
    return {
        "taluka":   row[COL_TALUKA],
        "district": row[COL_DISTRICT],
        "state":    row[COL_STATE],
        "level":    "Taluka",
        "geojson":  geojson,
        "bbox":     {"minx": bounds[0], "miny": bounds[1],
                     "maxx": bounds[2], "maxy": bounds[3]},
        "centroid": {"lat": centroid.y, "lon": centroid.x},
    }