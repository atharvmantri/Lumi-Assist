"""Weather lookup via wttr.in — no API key needed."""
from __future__ import annotations

import urllib.request
import json

from tools import tool


@tool(
    name="get_weather",
    description=(
        "Get current weather for a location. Uses wttr.in (free, no API key). "
        "Returns temperature, conditions, humidity, and wind. "
        "Use when the user asks about weather, temperature, or forecasts. "
        "Location is optional — defaults to the user's approximate location."
    ),
    parameters={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name, zip code, or 'current' for IP-based location (default: 'current')",
            },
        },
        "required": [],
    },
)
def get_weather(location: str = "current") -> str:
    try:
        query = location.strip() or "current"
        url = f"https://wttr.in/{urllib.request.quote(query)}?format=j1"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())

        current = data.get("current_condition", [{}])[0]
        temp_c = current.get("temp_C", "?")
        temp_f = current.get("temp_F", "?")
        feels_c = current.get("FeelsLikeC", "?")
        feels_f = current.get("FeelsLikeF", "?")
        desc = current.get("weatherDesc", [{}])[0].get("value", "unknown")
        humidity = current.get("humidity", "?")
        wind_kmh = current.get("windspeedKmph", "?")
        wind_mph = current.get("windspeedMiles", "?")
        visibility_km = current.get("visibility", "?")
        uv = current.get("uvIndex", "?")

        return (
            f"Weather in {query}:\n"
            f"  Conditions: {desc}\n"
            f"  Temperature: {temp_c}°C ({temp_f}°F), feels like {feels_c}°C ({feels_f}°F)\n"
            f"  Humidity: {humidity}%\n"
            f"  Wind: {wind_kmh} km/h ({wind_mph} mph)\n"
            f"  Visibility: {visibility_km} km\n"
            f"  UV Index: {uv}"
        )
    except urllib.error.URLError as e:
        return f"error fetching weather: {e}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="get_time",
    description="Get the current date and time in various formats.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_time() -> str:
    from datetime import datetime
    now = datetime.now()
    return (
        f"Current time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
        f"Unix timestamp: {int(now.timestamp())}"
    )
