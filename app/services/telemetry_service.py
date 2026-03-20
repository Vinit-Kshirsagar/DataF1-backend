import json
import logging
import os
from typing import Optional

import fastf1
import numpy as np

from app.config import settings
from app.redis_client import get_redis
from app.schemas.telemetry import DataPoint, TelemetryResponse
from app.services import summary_service

logger = logging.getLogger(__name__)

os.makedirs(settings.FASTF1_CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(settings.FASTF1_CACHE_DIR)

TELEMETRY_TTL = 60 * 60 * 12
TARGET_POINTS = 300

METRIC_META = {
    "throttle":  {"label": "Throttle",  "unit": "%",    "channel": "Throttle"},
    "brake":     {"label": "Brake",     "unit": "%",    "channel": "Brake"},
    "speed":     {"label": "Speed",     "unit": "km/h", "channel": "Speed"},
    "lap_time":  {"label": "Lap Time",  "unit": "s",    "channel": None},
    "top_speed": {"label": "Top Speed", "unit": "km/h", "channel": None},
}


def _safe_float(value) -> Optional[float]:
    try:
        f = float(value)
        if np.isnan(f) or np.isinf(f):
            return None
        return round(f, 4)
    except (TypeError, ValueError):
        return None


def _smooth_and_resample(x_raw, y_raw, n_points, channel):
    mask = np.isfinite(x_raw) & np.isfinite(y_raw)
    x_raw, y_raw = x_raw[mask], y_raw[mask]
    if len(x_raw) < 2:
        return []
    sort_idx = np.argsort(x_raw)
    x_raw, y_raw = x_raw[sort_idx], y_raw[sort_idx]
    x_even = np.linspace(x_raw[0], x_raw[-1], n_points)
    y_interp = np.interp(x_even, x_raw, y_raw)
    window = 3 if channel == "Brake" else (7 if channel == "Throttle" else 5)
    kernel = np.ones(window) / window
    y_smooth = np.convolve(y_interp, kernel, mode='same')
    if channel in ("Throttle", "Brake"):
        y_smooth = np.clip(y_smooth, 0, 100)
    # X stays in real metres — no normalisation
    return [
        DataPoint(x=round(float(x_even[i]), 1), y=round(float(y_smooth[i]), 2))
        for i in range(n_points)
    ]


async def get_telemetry(year, round_number, session_key, driver_code, metric):
    cache_key = f"telemetry:{year}:{round_number}:{session_key}:{driver_code}:{metric}"
    redis = await get_redis()

    cached = await redis.get(cache_key)
    if cached:
        logger.info(f"Cache HIT: {cache_key}")
        return TelemetryResponse(**json.loads(cached))

    logger.info(f"Cache MISS: {cache_key}")
    if metric not in METRIC_META:
        raise ValueError(f"Unknown metric: {metric}")

    meta = METRIC_META[metric]
    session = fastf1.get_session(year, round_number, session_key)
    session.load(telemetry=True, weather=False, messages=False, laps=True)

    results = session.results
    driver_row = results[results["Abbreviation"] == driver_code]
    driver_full_name = driver_code
    team = "Unknown"
    if not driver_row.empty:
        driver_full_name = str(driver_row.iloc[0].get("FullName", driver_code))
        team = str(driver_row.iloc[0].get("TeamName", "Unknown"))

    laps = session.laps.pick_drivers(driver_code)
    partial = False
    data_points = []
    fastest_lap = None
    total_laps = len(laps)

    if metric == "lap_time":
        for _, lap in laps.iterrows():
            lap_num = _safe_float(lap.get("LapNumber"))
            lap_time = lap.get("LapTime")
            if lap_num is None:
                continue
            try:
                seconds = lap_time.total_seconds() if hasattr(lap_time, "total_seconds") else None
                if seconds and 60 < seconds < 300:
                    data_points.append(DataPoint(x=lap_num, y=round(seconds, 3)))
            except Exception:
                partial = True
        if data_points:
            fastest_lap = min(dp.y for dp in data_points)

    elif metric == "top_speed":
        for _, lap in laps.iterrows():
            lap_num = _safe_float(lap.get("LapNumber"))
            if lap_num is None:
                continue
            try:
                tel = lap.get_telemetry()
                if tel is None or len(tel) == 0:
                    partial = True
                    continue
                speeds = tel["Speed"].dropna()
                if len(speeds) == 0:
                    partial = True
                    continue
                max_speed = _safe_float(speeds.max())
                if max_speed and max_speed > 100:
                    data_points.append(DataPoint(x=lap_num, y=max_speed))
            except Exception as e:
                logger.warning(f"Top speed lap error: {e}")
                partial = True

    else:
        try:
            fastest = laps.pick_fastest()
            tel = fastest.get_telemetry()
            channel = meta["channel"]
            if tel is not None and channel in tel.columns:
                x_raw = tel["Distance"].values.astype(float)
                y_raw = tel[channel].values.astype(float)
                if channel == "Brake":
                    y_raw = (y_raw > 0).astype(float) * 100.0
                data_points = _smooth_and_resample(x_raw, y_raw, TARGET_POINTS, channel)
                lap_time = fastest.get("LapTime")
                if lap_time is not None:
                    try:
                        fastest_lap = round(lap_time.total_seconds(), 3)
                    except Exception:
                        pass
            else:
                partial = True
        except Exception as e:
            logger.warning(f"Fastest lap telemetry failed for {driver_code}: {e}")
            partial = True

    if not data_points:
        raise ValueError(f"No telemetry data available for {driver_code} {metric}")

    race_name = f"Round {round_number}"
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        event = schedule[schedule["RoundNumber"] == round_number]
        if not event.empty:
            race_name = str(event.iloc[0]["EventName"])
    except Exception:
        pass

    summary = await summary_service.generate_summary(
        driver=driver_code, team=team, metric=metric, session=session_key,
        race=race_name, year=year,
        data_points=[{"x": dp.x, "y": dp.y} for dp in data_points],
        fastest_lap=fastest_lap,
    )

    response = TelemetryResponse(
        year=year, round=round_number, session=session_key,
        driver=driver_code, driver_full_name=driver_full_name, team=team,
        metric=metric, metric_label=meta["label"], metric_unit=meta["unit"],
        data=data_points, total_laps=total_laps, fastest_lap=fastest_lap,
        summary=summary, partial=partial,
    )

    try:
        await redis.setex(cache_key, TELEMETRY_TTL, json.dumps(response.model_dump()))
    except Exception as e:
        logger.warning(f"Failed to cache: {e}")

    return response
