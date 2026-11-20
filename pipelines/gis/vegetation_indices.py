"""
GIS Vegetation Indices
======================
Module: pipelines.gis.vegetation_indices

Implements standard remote-sensing vegetation and water indices:
- NDVI  (Normalized Difference Vegetation Index)
- NDWI  (Normalized Difference Water Index)
- EVI   (Enhanced Vegetation Index)
- SAVI  (Soil-Adjusted Vegetation Index)

All functions handle division-by-zero safely (returns NaN, never Inf).
Input arrays should be reflectance values in [0.0, 1.0] or [0, 10000] DN.
"""

from __future__ import annotations

import numpy as np


def _safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Element-wise division; returns NaN where denominator == 0."""
    with np.errstate(invalid="ignore", divide="ignore"):
        result = np.where(denominator == 0, np.nan, numerator / denominator)
    return result.astype(np.float64)


def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """
    Normalized Difference Vegetation Index.

    NDVI = (NIR - RED) / (NIR + RED)

    Returns values in [-1.0, 1.0]; NaN where NIR+RED == 0.

    Parameters
    ----------
    nir : np.ndarray  Near-infrared band reflectance.
    red : np.ndarray  Red band reflectance.

    Returns
    -------
    np.ndarray  NDVI values clipped to [-1, 1], NaN for invalid pixels.
    """
    nir = np.asarray(nir, dtype=np.float64)
    red = np.asarray(red, dtype=np.float64)
    denom = nir + red
    ndvi = _safe_divide(nir - red, denom)
    return np.clip(ndvi, -1.0, 1.0)


def compute_ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """
    Normalized Difference Water Index (McFeeters 1996).

    NDWI = (GREEN - NIR) / (GREEN + NIR)

    Returns values in [-1.0, 1.0]; NaN where denominator == 0.

    Parameters
    ----------
    green : np.ndarray  Green band reflectance.
    nir   : np.ndarray  Near-infrared band reflectance.

    Returns
    -------
    np.ndarray  NDWI values clipped to [-1, 1], NaN for invalid pixels.
    """
    green = np.asarray(green, dtype=np.float64)
    nir = np.asarray(nir, dtype=np.float64)
    denom = green + nir
    ndwi = _safe_divide(green - nir, denom)
    return np.clip(ndwi, -1.0, 1.0)


def compute_evi(
    nir: np.ndarray,
    red: np.ndarray,
    blue: np.ndarray,
    G: float = 2.5,
    C1: float = 6.0,
    C2: float = 7.5,
    L: float = 1.0,
) -> np.ndarray:
    """
    Enhanced Vegetation Index (Liu & Huete 1995).

    EVI = G * (NIR - RED) / (NIR + C1*RED - C2*BLUE + L)

    Parameters
    ----------
    nir  : np.ndarray  Near-infrared band.
    red  : np.ndarray  Red band.
    blue : np.ndarray  Blue band.
    G    : float       Gain factor (default 2.5).
    C1   : float       Aerosol resistance coefficient for red (default 6.0).
    C2   : float       Aerosol resistance coefficient for blue (default 7.5).
    L    : float       Canopy background adjustment (default 1.0).

    Returns
    -------
    np.ndarray  EVI values; NaN where denominator == 0.
    """
    nir = np.asarray(nir, dtype=np.float64)
    red = np.asarray(red, dtype=np.float64)
    blue = np.asarray(blue, dtype=np.float64)
    denom = nir + C1 * red - C2 * blue + L
    evi = _safe_divide(G * (nir - red), denom)
    return evi


def compute_savi(
    nir: np.ndarray,
    red: np.ndarray,
    L: float = 0.5,
) -> np.ndarray:
    """
    Soil-Adjusted Vegetation Index (Huete 1988).

    SAVI = ((NIR - RED) / (NIR + RED + L)) * (1 + L)

    Parameters
    ----------
    nir : np.ndarray  Near-infrared band.
    red : np.ndarray  Red band.
    L   : float       Soil brightness correction factor (default 0.5).

    Returns
    -------
    np.ndarray  SAVI values; NaN where denominator == 0.
    """
    nir = np.asarray(nir, dtype=np.float64)
    red = np.asarray(red, dtype=np.float64)
    denom = nir + red + L
    savi = _safe_divide(nir - red, denom) * (1.0 + L)
    return savi


def summarize_index_array(arr: np.ndarray) -> dict:
    """
    Return descriptive statistics for a vegetation index array.

    Parameters
    ----------
    arr : np.ndarray  Array of index values (may contain NaN for invalid pixels).

    Returns
    -------
    dict with keys:
        min              : float  Minimum valid value.
        max              : float  Maximum valid value.
        mean             : float  Mean of valid pixels.
        valid_pixel_count: int    Count of non-NaN pixels.
        nan_count        : int    Count of NaN (invalid) pixels.
    """
    arr = np.asarray(arr, dtype=np.float64)
    nan_mask = np.isnan(arr)
    nan_count = int(np.sum(nan_mask))
    valid_count = int(arr.size - nan_count)

    if valid_count == 0:
        return {
            "min": float("nan"),
            "max": float("nan"),
            "mean": float("nan"),
            "valid_pixel_count": 0,
            "nan_count": nan_count,
        }

    return {
        "min": float(np.nanmin(arr)),
        "max": float(np.nanmax(arr)),
        "mean": float(np.nanmean(arr)),
        "valid_pixel_count": valid_count,
        "nan_count": nan_count,
    }
