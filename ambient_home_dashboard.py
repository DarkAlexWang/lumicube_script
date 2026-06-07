# Ambient Home Dashboard for LumiCube
# v1: minimal visual dashboard with OpenWeather, auto-location with manual override,
# night mode, indoor comfort, Pi/network status, and critical visual/sound alerts.

from foundry_api.standard_library import *

import json
import math
import os
import socket
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CONFIG = {
    "openweather_api_key": "",
    "location": {
        "mode": "auto_with_manual_override",
        "latitude": None,
        "longitude": None,
        "label": None,
        "auto_detect_if_missing": True,
    },
    "night_mode": {
        "start_hour": 23,
        "end_hour": 8,
        "brightness": 12,
        "day_brightness": 42,
    },
    "refresh": {
        "weather_seconds": 15 * 60,
        "location_seconds": 6 * 60 * 60,
        "status_seconds": 15,
        "indoor_seconds": 10,
        "page_seconds": 6,
        "clock_seconds": 1,
        "alert_repeat_seconds": 10 * 60,
    },
    "alerts": {
        "enabled": True,
        "sound": True,
        "max_pi_cpu_temp_c": 78.0,
        "internet_failure_grace_checks": 3,
    },
}

WHITE = white
BLACK = black
RED = red
ORANGE = orange
YELLOW = yellow
GREEN = green
CYAN = cyan
BLUE = blue
MAGENTA = magenta
GREY = grey

PALETTE_DAY = [0x0A1B2A, 0x103550, 0x145C73]
PALETTE_NIGHT = [0x02060B, 0x07111A, 0x0B1A25]
PALETTE_SUNNY = [0xFFD34D, 0xFFB000, 0xFF7A00]
PALETTE_RAIN = [0x224A7A, 0x2E6BB2, 0x6CB6FF]
PALETTE_CLOUD = [0x4B5563, 0x6B7280, 0x9CA3AF]
PALETTE_ALERT = [0x550000, 0xAA0000, 0xFF2200]

WEATHER_ICONS = {
    "clear": [[0,ORANGE,0,ORANGE,ORANGE,0,ORANGE,0], [ORANGE,0,YELLOW,YELLOW,YELLOW,YELLOW,0,ORANGE], [0,YELLOW,YELLOW,YELLOW,YELLOW,YELLOW,YELLOW,0], [ORANGE,YELLOW,YELLOW,YELLOW,YELLOW,YELLOW,YELLOW,ORANGE], [ORANGE,YELLOW,YELLOW,YELLOW,YELLOW,YELLOW,YELLOW,ORANGE], [0,YELLOW,YELLOW,YELLOW,YELLOW,YELLOW,YELLOW,0], [ORANGE,0,YELLOW,YELLOW,YELLOW,YELLOW,0,ORANGE], [0,ORANGE,0,ORANGE,ORANGE,0,ORANGE,0]],
    "clouds": [[0,0,0,0,GREY,GREY,0,0], [0,0,GREY,GREY,GREY,GREY,GREY,0], [0,GREY,GREY,GREY,GREY,GREY,GREY,0], [GREY,GREY,GREY,GREY,GREY,GREY,GREY,GREY], [GREY,GREY,GREY,GREY,GREY,GREY,GREY,GREY], [0,GREY,GREY,GREY,GREY,GREY,GREY,0], [0,0,GREY,GREY,GREY,GREY,0,0], [0,0,0,0,0,0,0,0]],
    "rain": [[0,0,0,GREY,GREY,0,0,0], [0,0,GREY,GREY,GREY,GREY,0,0], [0,GREY,GREY,GREY,GREY,GREY,GREY,0], [GREY,GREY,GREY,GREY,GREY,GREY,GREY,GREY], [0,0,0,0,0,0,0,0], [BLUE,0,0,BLUE,0,0,BLUE,0], [0,0,0,0,0,0,0,0], [0,BLUE,0,0,BLUE,0,0,BLUE]],
    "storm": [[0,0,ORANGE,YELLOW,YELLOW,ORANGE,0,0], [0,0,YELLOW,YELLOW,ORANGE,0,0,0], [0,ORANGE,YELLOW,ORANGE,0,0,0,0], [0,YELLOW,YELLOW,0,0,0,0,0], [ORANGE,YELLOW,YELLOW,YELLOW,YELLOW,YELLOW,ORANGE,0], [0,0,0,0,YELLOW,ORANGE,0,0], [0,0,0,YELLOW,ORANGE,0,0,0], [0,0,0,ORANGE,0,0,0,0]],
    "mist": [[0,0,0,0,0,0,0,0], [0,GREY,GREY,GREY,GREY,GREY,GREY,0], [0,0,0,0,0,0,0,0], [0,GREY,GREY,GREY,GREY,GREY,GREY,0], [0,0,0,0,0,0,0,0], [0,GREY,GREY,GREY,GREY,GREY,GREY,0], [0,0,0,0,0,0,0,0], [0,0,0,0,0,0,0,0]],
}

STATE = {
    "location": {"lat": None, "lon": None, "label": "Locating...", "source": "unknown", "last_update": 0},
    "weather": {"ok": False, "description": "--", "temp_c": None, "feels_like_c": None, "humidity": None, "icon": "clouds", "main": None, "last_update": 0, "error": None},
    "indoor": {"temp_c": None, "humidity": None, "light": None, "last_update": 0},
    "status": {"ip": "--", "cpu_temp_c": None, "cpu_percent": None, "ram_percent": None, "disk_percent": None, "internet_ok": None, "internet_fail_count": 0, "last_update": 0},
    "ui": {"page_index": 0, "last_page_switch": 0, "last_clock_draw": 0, "last_alert": 0, "last_led_push": 0},
}

PAGES = ["clock", "indoor", "weather", "status"]


def http_json(url, timeout=5, headers=None):
    req = Request(url, headers=headers or {"User-Agent": "lumicube-ambient-dashboard/1.0"})
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def clamp(value, low, high):
    return max(low, min(high, value))


def fmt_temp(v):
    return "--.-C" if v is None else f"{v:.1f}C"


def fmt_pct(v):
    return "--%" if v is None else f"{v:.0f}%"


def now_local():
    return time.localtime()


def is_night_mode():
    hour = now_local().tm_hour
    start_hour = CONFIG["night_mode"]["start_hour"]
    end_hour = CONFIG["night_mode"]["end_hour"]
    if start_hour < end_hour:
        return start_hour <= hour < end_hour
    return hour >= start_hour or hour < end_hour


def set_display_brightness():
    target = CONFIG["night_mode"]["brightness"] if is_night_mode() else CONFIG["night_mode"]["day_brightness"]
    try:
        display.brightness = target
    except Exception:
        pass


def draw_centered_text(title, lines, accent=WHITE):
    screen.draw_rectangle(0, 0, 320, 240, BLACK)
    screen.write_text(12, 12, title, 2, accent, BLACK)
    y = 58
    for line in lines:
        screen.write_text(18, y, str(line), 1, WHITE, BLACK)
        y += 28


def draw_icon(icon_name, origin_x=228, origin_y=20, scale=8):
    icon = WEATHER_ICONS.get(icon_name, WEATHER_ICONS["clouds"])
    for y, row in enumerate(icon):
        for x, colour in enumerate(row):
            if colour:
                screen.draw_rectangle(origin_x + x * (scale // 2), origin_y + y * (scale // 2), scale // 2, scale // 2, colour)


def blend_colour(a, b, t):
    ar, ag, ab = (a >> 16) & 255, (a >> 8) & 255, a & 255
    br, bg, bb = (b >> 16) & 255, (b >> 8) & 255, b & 255
    r = int(ar + (br - ar) * t)
    g = int(ag + (bg - ag) * t)
    b = int(ab + (bb - ab) * t)
    return (r << 16) | (g << 8) | b


def weather_palette():
    main = (STATE["weather"].get("main") or "").lower()
    if "thunder" in main:
        return PALETTE_ALERT
    if "rain" in main or "drizzle" in main:
        return PALETTE_RAIN
    if "clear" in main:
        return PALETTE_SUNNY
    if "cloud" in main:
        return PALETTE_CLOUD
    return PALETTE_NIGHT if is_night_mode() else PALETTE_DAY


def render_ambient_leds(alert=False):
    palette = PALETTE_ALERT if alert else weather_palette()
    colours = {}
    t = time.time()
    pulse = 0.5 + 0.5 * math.sin(t * (2.2 if alert else 0.35))
    for x in range(9):
        for y in range(9):
            for z in range(9):
                if x == 8 or y == 8 or z == 8:
                    phase = ((x + y + z) % 8) / 7.0
                    base = blend_colour(palette[0], palette[1], phase)
                    top = blend_colour(palette[1], palette[2], pulse * 0.65)
                    colours[(x, y, z)] = blend_colour(base, top, 0.35 + 0.35 * pulse)
    try:
        display.set_3d(colours)
    except Exception:
        pass


def internet_ok():
    try:
        socket.create_connection(("1.1.1.1", 53), 2).close()
        return True
    except OSError:
        return False


def detect_location():
    manual_lat = CONFIG["location"].get("latitude")
    manual_lon = CONFIG["location"].get("longitude")
    manual_label = CONFIG["location"].get("label")
    if manual_lat is not None and manual_lon is not None:
        STATE["location"].update({
            "lat": manual_lat,
            "lon": manual_lon,
            "label": manual_label or f"{manual_lat:.3f}, {manual_lon:.3f}",
            "source": "manual",
            "last_update": time.time(),
        })
        return

    if not CONFIG["location"].get("auto_detect_if_missing", True):
        return

    try:
        data = http_json("http://ip-api.com/json/?fields=status,message,lat,lon,city,regionName,country")
        if data.get("status") == "success":
            label_parts = [data.get("city"), data.get("regionName"), data.get("country")]
            label = ", ".join([p for p in label_parts if p]) or f"{data['lat']:.3f}, {data['lon']:.3f}"
            STATE["location"].update({
                "lat": float(data["lat"]),
                "lon": float(data["lon"]),
                "label": label,
                "source": "auto-ip",
                "last_update": time.time(),
            })
    except Exception:
        pass


def reverse_geocode_label():
    api_key = CONFIG.get("openweather_api_key", "").strip()
    lat = STATE["location"].get("lat")
    lon = STATE["location"].get("lon")
    if not api_key or lat is None or lon is None:
        return
    try:
        params = urlencode({"lat": lat, "lon": lon, "limit": 1, "appid": api_key})
        data = http_json(f"https://api.openweathermap.org/geo/1.0/reverse?{params}")
        if isinstance(data, list) and data:
            item = data[0]
            label = item.get("name")
            state = item.get("state")
            country = item.get("country")
            parts = [p for p in [label, state, country] if p]
            if parts:
                STATE["location"]["label"] = ", ".join(parts)
    except Exception:
        pass


def update_weather():
    api_key = CONFIG.get("openweather_api_key", "").strip()
    lat = STATE["location"].get("lat")
    lon = STATE["location"].get("lon")
    if not api_key or lat is None or lon is None:
        STATE["weather"].update({"ok": False, "error": "Missing API key or location"})
        return
    try:
        params = urlencode({"lat": lat, "lon": lon, "appid": api_key, "units": "metric"})
        data = http_json(f"https://api.openweathermap.org/data/2.5/weather?{params}")
        weather = (data.get("weather") or [{}])[0]
        main = (weather.get("main") or "").lower()
        icon = "clouds"
        if "clear" in main:
            icon = "clear"
        elif "rain" in main or "drizzle" in main:
            icon = "rain"
        elif "thunder" in main:
            icon = "storm"
        elif any(v in main for v in ["mist", "fog", "haze", "smoke"]):
            icon = "mist"
        STATE["weather"].update({
            "ok": True,
            "description": weather.get("description", "--").title(),
            "temp_c": data.get("main", {}).get("temp"),
            "feels_like_c": data.get("main", {}).get("feels_like"),
            "humidity": data.get("main", {}).get("humidity"),
            "icon": icon,
            "main": weather.get("main", ""),
            "last_update": time.time(),
            "error": None,
        })
    except (URLError, HTTPError, TimeoutError, ValueError) as exc:
        STATE["weather"].update({"ok": False, "error": str(exc), "last_update": time.time()})


def read_attr(module_name, attr_name):
    try:
        if module_name == "pi":
            if attr_name == "cpu_temp":
                return pi.cpu_temp()
            if attr_name == "cpu_percent":
                return pi.cpu_percent()
            if attr_name == "ram_percent_used":
                return pi.ram_percent_used()
            if attr_name == "disk_percent":
                return pi.disk_percent()
            if attr_name == "ip_address":
                return pi.ip_address()
    except Exception:
        return None
    return None


def update_indoor():
    # Environment sensor not installed — skip all sensor reads
    STATE["indoor"].update({
        "temp_c": None,
        "humidity": None,
        "light": None,
        "available": False,
        "last_update": time.time(),
    })


def update_status():
    ok = internet_ok()
    fail_count = STATE["status"]["internet_fail_count"]
    fail_count = 0 if ok else fail_count + 1
    STATE["status"].update({
        "ip": read_attr("pi", "ip_address") or "--",
        "cpu_temp_c": read_attr("pi", "cpu_temp"),
        "cpu_percent": read_attr("pi", "cpu_percent"),
        "ram_percent": read_attr("pi", "ram_percent_used"),
        "disk_percent": read_attr("pi", "disk_percent"),
        "internet_ok": ok,
        "internet_fail_count": fail_count,
        "last_update": time.time(),
    })


def comfort_label(temp_c, humidity):
    if temp_c is None and humidity is None:
        return "No indoor data"
    if temp_c is not None and (temp_c < CONFIG["alerts"]["min_indoor_temp_c"] or temp_c > CONFIG["alerts"]["max_indoor_temp_c"]):
        return "Temp alert"
    if humidity is not None and (humidity < CONFIG["alerts"]["min_humidity"] or humidity > CONFIG["alerts"]["max_humidity"]):
        return "Humidity alert"
    return "Comfortable"


def active_critical_alerts():
    alerts = []
    a = CONFIG["alerts"]
    indoor = STATE["indoor"]
    status = STATE["status"]
    # Indoor temp/humidity alerts skipped — environment sensor not installed
    if status["cpu_temp_c"] is not None and status["cpu_temp_c"] >= a["max_pi_cpu_temp_c"]:
        alerts.append(f"Pi hot {status['cpu_temp_c']:.1f}C")
    if status["internet_ok"] is False and status["internet_fail_count"] >= a["internet_failure_grace_checks"]:
        alerts.append("Internet offline")
    return alerts


def play_critical_alert():
    if not CONFIG["alerts"].get("sound", True):
        return
    try:
        speaker.tone(880, 0.10)
        time.sleep(0.05)
        speaker.tone(660, 0.12)
    except Exception:
        try:
            speaker.say("Critical alert")
        except Exception:
            pass


def render_clock_page():
    t = now_local()
    screen.draw_rectangle(0, 0, 320, 240, BLACK)
    screen.write_text(18, 18, time.strftime("%H:%M", t), 4, WHITE, BLACK)
    screen.write_text(20, 110, time.strftime("%a %d %b", t), 2, GREY, BLACK)
    label = STATE["location"].get("label", "--")
    if len(label) > 24:
        label = label[:24]
    screen.write_text(20, 176, label, 1, CYAN, BLACK)


def render_indoor_page():
    draw_centered_text("INDOOR", [
        "Sensor not installed.",
        "",
        "Install the environment",
        "add-on to enable this.",
    ], accent=GREY)


def render_weather_page():
    weather = STATE["weather"]
    screen.draw_rectangle(0, 0, 320, 240, BLACK)
    screen.write_text(14, 14, "WEATHER", 2, CYAN, BLACK)
    draw_icon(weather.get("icon") or "clouds")
    screen.write_text(18, 70, fmt_temp(weather.get("temp_c")), 3, WHITE, BLACK)
    screen.write_text(18, 126, (weather.get("description") or "--")[:20], 1, GREY, BLACK)
    screen.write_text(18, 156, f"Feels {fmt_temp(weather.get('feels_like_c'))}", 1, WHITE, BLACK)
    screen.write_text(18, 184, f"Hum   {fmt_pct(weather.get('humidity'))}", 1, WHITE, BLACK)


def render_status_page():
    status = STATE["status"]
    accent = GREEN if status["internet_ok"] else RED
    draw_centered_text("STATUS", [
        f"IP    {status['ip']}",
        f"CPU   {fmt_temp(status['cpu_temp_c'])}  {fmt_pct(status['cpu_percent'])}",
        f"RAM   {fmt_pct(status['ram_percent'])}",
        f"Disk  {fmt_pct(status['disk_percent'])}",
        f"Net   {'OK' if status['internet_ok'] else 'DOWN'}",
    ], accent=accent)


def render_alert_overlay(alerts):
    screen.draw_rectangle(0, 0, 320, 240, BLACK)
    screen.write_text(14, 16, "CRITICAL", 2, RED, BLACK)
    y = 64
    for item in alerts[:4]:
        screen.write_text(16, y, item[:28], 1, WHITE, BLACK)
        y += 32


def maybe_rotate_page():
    if time.time() - STATE["ui"]["last_page_switch"] >= CONFIG["refresh"]["page_seconds"]:
        STATE["ui"]["page_index"] = (STATE["ui"]["page_index"] + 1) % len(PAGES)
        STATE["ui"]["last_page_switch"] = time.time()


def render_page_or_alert():
    alerts = active_critical_alerts()
    if alerts:
        render_alert_overlay(alerts)
        render_ambient_leds(alert=True)
        if CONFIG["alerts"].get("enabled", True) and time.time() - STATE["ui"]["last_alert"] >= CONFIG["refresh"]["alert_repeat_seconds"]:
            play_critical_alert()
            STATE["ui"]["last_alert"] = time.time()
        return

    page = PAGES[STATE["ui"]["page_index"]]
    if page == "clock":
        render_clock_page()
    elif page == "indoor":
        render_indoor_page()
    elif page == "weather":
        render_weather_page()
    else:
        render_status_page()
    render_ambient_leds(alert=False)


def should_refresh(last_key, interval_key):
    interval = CONFIG["refresh"][interval_key]
    source = last_key.split(".")
    current = STATE[source[0]][source[1]]
    return time.time() - current >= interval


def setup():
    set_display_brightness()
    detect_location()
    reverse_geocode_label()
    update_indoor()
    update_status()
    if STATE["location"].get("lat") is not None:
        update_weather()
    try:
        speaker.volume = 35
    except Exception:
        pass


def loop():
    while True:
        set_display_brightness()

        if should_refresh("location.last_update", "location_seconds"):
            detect_location()
            reverse_geocode_label()

        if should_refresh("indoor.last_update", "indoor_seconds"):
            update_indoor()

        if should_refresh("status.last_update", "status_seconds"):
            update_status()

        if should_refresh("weather.last_update", "weather_seconds"):
            update_weather()

        maybe_rotate_page()
        render_page_or_alert()
        time.sleep(CONFIG["refresh"]["clock_seconds"])


setup()
loop()
