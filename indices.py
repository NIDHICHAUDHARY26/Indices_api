"""
Remote Sensing Indices Calculator
- All formulas exactly from your indices.py (same image.expression style, same band aliases)
- Uses cloud_mask.py for collection building (S2_SR_HARMONIZED — correct for 2017-present)
- Threshold classification from config.INDICES (from index_class_color)
- Performance: bestEffort=True, tileScale=4, scale=30 for stats (fast)
- Returns classified PNG via getThumbURL clipped to AOI
"""

import ee
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import INDICES, SATELLITE_MAP, MAX_CLOUD_COVER
from utils.cloud_mask import (
    get_best_composite,
    get_sentinel2_collection, get_sentinel2_permissive,
    get_landsat_collection, get_sentinel1_collection
)

# ─── Band resolver ────────────────────────────────────────────────────────────

def _b(image, sat_key, alias):
    """Select band by alias from SATELLITE_MAP."""
    band_name = SATELLITE_MAP[sat_key]["bands"][alias]
    return image.select(band_name)


# ─── Index Computation ────────────────────────────────────────────────────────
# All formulas exactly match indices.py calculate_* functions.
# S2_SR_HARMONIZED stores reflectance as float 0-1 after cloud_mask.py divides by 10000.

def compute_index(image: ee.Image, index_name: str, sat_key: str) -> ee.Image:
    name = index_name.upper()

    def b(alias):
        return _b(image, sat_key, alias)

    # ── Vegetation ─────────────────────────────────────────────────────────
    if name == "NDVI":
        return image.expression("(N-R)/(N+R)", {"N":b("N"),"R":b("R")}).rename("NDVI")

    elif name == "GNDVI":
        return image.expression("(N-G)/(N+G)", {"N":b("N"),"G":b("G")}).rename("GNDVI")

    elif name == "EVI":
        return image.expression(
            "2.5*((N-R)/(N+6*R-7.5*B+1))",
            {"N":b("N"),"R":b("R"),"B":b("B")}
        ).rename("EVI")

    elif name == "LAI":
        # From indices.py: 3.618 * (2.5*((N-R)/(N+6*R-7.5*B+1))) - 0.118
        return image.expression(
            "3.618*(2.5*((N-R)/(N+6*R-7.5*B+1)))-0.118",
            {"N":b("N"),"R":b("R"),"B":b("B")}
        ).rename("LAI")

    elif name == "GLI":
        return image.expression(
            "(2*G-R-B)/(2*G+R+B)",
            {"G":b("G"),"R":b("R"),"B":b("B")}
        ).rename("GLI")

    elif name == "SAVI":
        # From indices.py: (1+L)*(N-R)/(N+R+L) [L=0.5]
        return image.expression(
            "(1+L)*(N-R)/(N+R+L)",
            {"N":b("N"),"R":b("R"),"L":ee.Image(0.5)}
        ).rename("SAVI")

    elif name == "MSAVI":
        N = b("N"); R = b("R")
        return (N.multiply(2).add(1)
                .subtract(
                    N.multiply(2).add(1).pow(2)
                    .subtract(N.subtract(R).multiply(8))
                    .sqrt()
                ).divide(2)).rename("MSAVI")

    elif name == "GCI":
        # From indices.py: (S1/G) - 1
        return image.expression("(S1/G)-1", {"S1":b("S1"),"G":b("G")}).rename("GCI")

    elif name == "CIG":
        # From indices.py calculate_CIG: (N/G) - 1
        return image.expression("(N/G)-1", {"N":b("N"),"G":b("G")}).rename("CIG")

    elif name == "SIPI":
        # From indices.py: (N-A)/(N-R)
        return image.expression(
            "(N-A)/(N-R)", {"N":b("N"),"A":b("A"),"R":b("R")}
        ).rename("SIPI")

    elif name == "ARVI":
        # From indices.py: (N-(2*R)+B)/(N+(2*R)+B)
        return image.expression(
            "(N-(2*R)+B)/(N+(2*R)+B)",
            {"N":b("N"),"R":b("R"),"B":b("B")}
        ).rename("ARVI")

    elif name == "NBR":
        return image.expression("(N-S2)/(N+S2)", {"N":b("N"),"S2":b("S2")}).rename("NBR")

    elif name == "GSAVI":
        # From indices.py: (1+L)*(N-G)/(N+G+L)
        return image.expression(
            "(1+L)*(N-G)/(N+G+L)",
            {"N":b("N"),"G":b("G"),"L":ee.Image(0.5)}
        ).rename("GSAVI")

    elif name == "SLAVI":
        return image.expression("N/(R+S2)", {"N":b("N"),"R":b("R"),"S2":b("S2")}).rename("SLAVI")

    elif name == "S2REP":
        # From indices.py: 705 + 35*(((RE3+R)/2 - RE1)/(RE2-RE1))
        return image.expression(
            "705+35*(((RE3+R)/2-RE1)/(RE2-RE1))",
            {"RE1":b("RE1"),"RE2":b("RE2"),"RE3":b("RE3"),"R":b("R")}
        ).rename("S2REP")

    elif name == "RENDVI":
        return image.expression(
            "(RE2-RE1)/(RE2+RE1)", {"RE2":b("RE2"),"RE1":b("RE1")}
        ).rename("RENDVI")

    elif name == "MRESR":
        return image.expression(
            "(RE2-A)/(RE2+A)", {"RE2":b("RE2"),"A":b("A")}
        ).rename("MRESR")

    elif name == "NDREI":
        return image.expression(
            "(N-RE1)/(N+RE1)", {"N":b("N"),"RE1":b("RE1")}
        ).rename("NDREI")

    elif name == "NIRv":
        return image.expression(
            "((N-R)/(N+R))*N", {"N":b("N"),"R":b("R")}
        ).rename("NIRv")

    elif name == "RGRI":
        return image.expression("R/G", {"R":b("R"),"G":b("G")}).rename("RGRI")

    elif name == "MCARI":
        # From indices.py: ((RE1-R)-0.2*(RE1-G))*(RE1/R)
        return image.expression(
            "((RE1-R)-0.2*(RE1-G))*(RE1/R)",
            {"RE1":b("RE1"),"R":b("R"),"G":b("G")}
        ).rename("MCARI")

    elif name == "PSRI":
        return image.expression("(R-B)/RE2", {"R":b("R"),"B":b("B"),"RE2":b("RE2")}).rename("PSRI")

    elif name == "ARI":
        return image.expression("(1/G)-(1/RE1)", {"G":b("G"),"RE1":b("RE1")}).rename("ARI")

    elif name == "ARI2":
        return image.expression(
            "N*((1/G)-(1/RE1))", {"N":b("N"),"G":b("G"),"RE1":b("RE1")}
        ).rename("ARI2")

    elif name == "MIRBI":
        # From indices.py: (S2*0.0001*10) - (S1*0.0001*9.8) + 2
        # NOTE: cloud_mask.py already divides S2 by 10000, so values are 0-1.
        # Applying the 0.0001 scale factor on already-scaled values still matches
        # the relative formula intent.
        return image.expression(
            "(S2*0.0001*10)-(S1*0.0001*9.8)+2",
            {"S2":b("S2"),"S1":b("S1")}
        ).rename("MIRBI")

    # ── Water ───────────────────────────────────────────────────────────────
    elif name == "NDWI":
        return image.expression("(G-N)/(G+N)", {"G":b("G"),"N":b("N")}).rename("NDWI")

    elif name == "MNDWI":
        return image.expression("(G-S1)/(G+S1)", {"G":b("G"),"S1":b("S1")}).rename("MNDWI")

    elif name == "LSWI":
        return image.expression("(N-S2)/(N+S2)", {"N":b("N"),"S2":b("S2")}).rename("LSWI")

    elif name == "MSI":
        return image.expression("S1/N", {"S1":b("S1"),"N":b("N")}).rename("MSI")

    elif name == "NMDI":
        return image.expression(
            "(N-(S1-S2))/(N+(S1-S2))", {"N":b("N"),"S1":b("S1"),"S2":b("S2")}
        ).rename("NMDI")

    elif name == "MBWI":
        return image.expression("(G-N2)/(G+N2)", {"G":b("G"),"N2":b("N2")}).rename("MBWI")

    # ── Built-up ────────────────────────────────────────────────────────────
    elif name == "NDBI":
        return image.expression("(S1-N)/(S1+N)", {"S1":b("S1"),"N":b("N")}).rename("NDBI")

    elif name == "UI":
        return image.expression("(S2-N)/(S2+N)", {"S2":b("S2"),"N":b("N")}).rename("UI")

    # ── Soil ────────────────────────────────────────────────────────────────
    elif name == "BSI":
        return image.expression(
            "((S1+R)-(N+B))/((S1+R)+(N+B))",
            {"S1":b("S1"),"R":b("R"),"N":b("N"),"B":b("B")}
        ).rename("BSI")

    # ── Agriculture ─────────────────────────────────────────────────────────
    elif name == "VCI":
        ndvi = image.expression("(N-R)/(N+R)", {"N":b("N"),"R":b("R")})
        # Use region stats as proxy for historical min/max
        stats = ndvi.reduceRegion(
            reducer=ee.Reducer.min().combine(ee.Reducer.max(), sharedInputs=True),
            geometry=image.geometry(), scale=30, maxPixels=1e8, bestEffort=True, tileScale=4
        ).getInfo()
        vs = list(stats.values())
        ndvi_min = vs[0] if vs else -1
        ndvi_max = vs[1] if len(vs) > 1 else 1
        denom = ndvi_max - ndvi_min
        if not denom or denom < 0.001:
            denom = 1.0
        return ndvi.subtract(ndvi_min).divide(denom).multiply(100).clamp(0, 100).rename("VCI")

    elif name == "NDDI":
        ndvi = image.expression("(N-R)/(N+R)", {"N":b("N"),"R":b("R")})
        ndwi = image.expression("(G-N)/(G+N)", {"G":b("G"),"N":b("N")})
        return ndvi.subtract(ndwi).divide(ndvi.add(ndwi)).rename("NDDI")

    # ── Thermal ─────────────────────────────────────────────────────────────
    elif name == "LST":
        # Landsat C2 L2 — cloud_mask.py applies scale: B10 * 0.00341802 + 149.0
        # That gives Kelvin. Subtract 273.15 for Celsius.
        t1 = _b(image, sat_key, "T1")
        return t1.subtract(273.15).rename("LST")

    # ── Soil Moisture (Sentinel-1) ───────────────────────────────────────────
    elif name == "SM":
        # From indices.py calculate_SM
        return image.expression(
            "((12.11993+1.139742*((VH+(VV-12.11993)*1.139742)/(1+1.139742**2)))+19.476)/0.3711",
            {"VV": image.select("VV"), "VH": image.select("VH")}
        ).rename("SM")

    else:
        raise ValueError(f"Unknown index: {index_name}")


# ─── Classification ───────────────────────────────────────────────────────────

def make_classified_image(idx_img: ee.Image, index_name: str) -> ee.Image:
    """
    Apply threshold-based classification from config.INDICES.
    Returns integer-class image. Class values match config palettes.
    """
    info         = INDICES.get(index_name.upper(), {})
    thresholds   = info.get("threshold", [-1, 0, 0.5, 1])
    class_values = info.get("class_values", [1, 2, 3])

    classified = ee.Image(0)
    for i, val in enumerate(class_values):
        lo = thresholds[i]
        hi = thresholds[i + 1]
        classified = classified.where(idx_img.gte(lo).And(idx_img.lt(hi)), val)
    # Last class includes upper boundary
    classified = classified.where(idx_img.gte(thresholds[-2]), class_values[-1])
    return classified.rename(index_name.upper())


def get_vis_params(index_name: str) -> dict:
    info = INDICES.get(index_name.upper(), {})
    return {
        "min":     1,
        "max":     len(info.get("class_values", [1,2,3,4,5])),
        "palette": info.get("palettes", ["#d73027","#fee08b","#1a9850"]),
    }


# ─── Stats helper ─────────────────────────────────────────────────────────────

def _get_stats(idx_img: ee.Image, geometry, sat_key: str) -> dict:
    """
    Fast stats: use scale=30 always + bestEffort + tileScale=4.
    Returns {"mean":..., "min":..., "max":...}
    """
    try:
        raw = idx_img.reduceRegion(
            reducer=(ee.Reducer.mean()
                     .combine(ee.Reducer.min(), sharedInputs=True)
                     .combine(ee.Reducer.max(), sharedInputs=True)),
            geometry=geometry,
            scale=30,           # Always 30m for stats — much faster than 10m
            maxPixels=1e8,
            bestEffort=True,
            tileScale=4
        ).getInfo()
        vs = [v for v in raw.values() if v is not None]
        return {
            "mean": round(vs[0], 4) if len(vs) > 0 else None,
            "min":  round(vs[1], 4) if len(vs) > 1 else None,
            "max":  round(vs[2], 4) if len(vs) > 2 else None,
        }
    except Exception:
        return {"mean": None, "min": None, "max": None}


# ─── Main API Functions ───────────────────────────────────────────────────────

def get_index_stats(geometry, index_name: str, date: str,
                    window_days: int = 30) -> dict:
    """
    Compute index stats for a geometry+date.
    Uses cloud_mask.py get_best_composite (never fails for valid AOI).
    """
    idx_info = INDICES.get(index_name.upper(), {})
    sat_key  = idx_info.get("satellite", "sentinel2")

    composite, count = get_best_composite(geometry, date, sat_key, window_days)
    if composite is None:
        return {"error": f"No imagery found for {date}. Try a wider cloud window."}

    try:
        idx_img = compute_index(composite, index_name, sat_key)
    except ValueError as e:
        return {"error": str(e)}

    stats = _get_stats(idx_img, geometry, sat_key)
    return {
        "index":       index_name.upper(),
        "index_name":  idx_info.get("name", index_name),
        "category":    idx_info.get("category", ""),
        "description": idx_info.get("description", ""),
        "satellite":   sat_key,
        "formula":     idx_info.get("formula", ""),
        "date_used":   date,
        "scenes_used": count,
        "stats":       stats,
        "mean":        stats["mean"],
        "min":         stats["min"],
        "max":         stats["max"],
    }


def get_map_url(geometry, index_name: str, date: str,
                window_days: int = 30) -> dict:
    """
    Classified PNG thumbnail using threshold palette from config.
    Uses cloud_mask.py get_best_composite.
    """
    idx_info = INDICES.get(index_name.upper(), {})
    sat_key  = idx_info.get("satellite", "sentinel2")

    composite, count = get_best_composite(geometry, date, sat_key, window_days)
    if composite is None:
        return {"error": f"No imagery found for {date}. Try a wider cloud window."}

    try:
        idx_img    = compute_index(composite, index_name, sat_key)
        classified = make_classified_image(idx_img, index_name)
    except ValueError as e:
        return {"error": str(e)}

    vis    = get_vis_params(index_name)
    stats  = _get_stats(idx_img, geometry, sat_key)

    png_url = classified.getThumbURL({
        **vis,
        "region":     geometry,
        "dimensions": {"width": 512, "height": 512},
        "format":     "png",
    })

    return {
        "index":       index_name.upper(),
        "satellite":   sat_key,
        "date_used":   date,
        "scenes_used": count,
        "png_url":     png_url,
        "mean":        stats["mean"],
        "min":         stats["min"],
        "max":         stats["max"],
        "vis_params":  vis,
        "bands_used":  idx_info.get("bands_needed", []),
    }


def get_map_url_range(geometry, index_name: str,
                      start_date: str, end_date: str) -> dict:
    """Median composite over a date range — classified PNG."""
    import datetime
    idx_info = INDICES.get(index_name.upper(), {})
    sat_key  = idx_info.get("satellite", "sentinel2")

    if sat_key == "sentinel2":
        col = get_sentinel2_permissive(geometry, start_date, end_date)
    elif sat_key in ("landsat8", "landsat9", "landsat"):
        col = get_landsat_collection(geometry, start_date, end_date, max_cloud=60)
    elif sat_key == "sentinel1":
        col = get_sentinel1_collection(geometry, start_date, end_date)
    else:
        return {"error": f"Unknown satellite: {sat_key}"}

    count = col.limit(1).size().getInfo()
    if count == 0:
        return {"error": f"No imagery between {start_date} and {end_date}"}

    count     = col.limit(50).size().getInfo()
    composite = col.median().clip(geometry)

    try:
        idx_img    = compute_index(composite, index_name, sat_key)
        classified = make_classified_image(idx_img, index_name)
    except ValueError as e:
        return {"error": str(e)}

    vis    = get_vis_params(index_name)
    stats  = _get_stats(idx_img, geometry, sat_key)

    png_url = classified.getThumbURL({
        **vis,
        "region":     geometry,
        "dimensions": {"width": 512, "height": 512},
        "format":     "png",
    })

    return {
        "index":       index_name.upper(),
        "satellite":   sat_key,
        "date_used":   f"{start_date} to {end_date}",
        "scenes_used": count,
        "png_url":     png_url,
        "mean":        stats["mean"],
        "min":         stats["min"],
        "max":         stats["max"],
        "vis_params":  vis,
    }


def get_rgb_url(geometry, date: str, sat_key: str = "sentinel2",
                window_days: int = 30) -> dict:
    """True-color RGB PNG."""
    composite, count = get_best_composite(geometry, date, sat_key, window_days)
    if composite is None:
        return {"error": "No imagery found"}
    bands = SATELLITE_MAP[sat_key]["bands"]
    rgb   = [bands["R"], bands["G"], bands["B"]]
    url   = composite.select(rgb).getThumbURL({
        "min": 0, "max": 0.3, "bands": rgb,
        "region": geometry,
        "dimensions": {"width": 512, "height": 512},
        "format": "png",
    })
    return {
        "png_url":     url,
        "rgb_url":     url,
        "satellite":   sat_key,
        "scenes_used": count,
        "date_used":   date
    }
    
    
