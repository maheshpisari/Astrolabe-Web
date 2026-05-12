import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import swisseph as swe
import math
from datetime import date, datetime, timedelta, timezone

# Vimshottari Dasha Lord Sequence & Years
NL_SEQUENCE = ["KE", "VE", "SU", "MO", "MA", "RA", "JU", "SA", "ME"]
KP_YEARS = {"KE": 7, "VE": 20, "SU": 6, "MO": 10, "MA": 7, "RA": 18, "JU": 16, "SA": 19, "ME": 17}

RASHI_LORDS = {
    1: "MA", 2: "VE", 3: "ME", 4: "MO", 5: "SU", 6: "ME",
    7: "VE", 8: "MA", 9: "JU", 10: "SA", 11: "SA", 12: "JU"
}

LORD_TO_RASHIS = {}
for rashi, lord in RASHI_LORDS.items():
    LORD_TO_RASHIS.setdefault(lord, []).append(rashi)

def get_current_ist_rounded():
    """Gets current IST time and rounds to the nearest 15 minutes."""
    # 1. Get current UTC time and convert to IST (+5 hours 30 minutes)
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    
    # 2. Round to the nearest 15 minutes
    minute = 15 * round(ist_now.minute / 15)
    
    # 3. Handle the edge case where rounding pushes the minute to 60
    if minute >= 60:
        ist_now += timedelta(hours=1)
        minute = 0
        
    rounded_time = ist_now.replace(minute=minute, second=0, microsecond=0)
    
    return rounded_time.date(), rounded_time.time()

def get_nl_sl(longitude):
    long_min = longitude * 60.0
    nak_idx = int(long_min / 800.0)
    nl = NL_SEQUENCE[nak_idx % 9]
    
    rem_min = long_min % 800.0
    start_idx = NL_SEQUENCE.index(nl)
    cum_span = 0.0
    
    for i in range(9):
        sl = NL_SEQUENCE[(start_idx + i) % 9]
        span = KP_YEARS[sl] * (800.0 / 120.0)
        cum_span += span
        if rem_min < cum_span:
            return nl, sl
    return nl, nl

def get_lagna(year, month, day, hour, minute):
    utc_hour = hour - 5
    utc_min = minute - 30
    if utc_min < 0:
        utc_min += 60
        utc_hour -= 1
        
    jd = swe.julday(year, month, day, utc_hour + utc_min/60.0)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    cusps, ascmc = swe.houses_ex(jd, 12.9716, 77.5946, b'P', swe.FLG_SIDEREAL)
    return int(math.floor(ascmc[0] + 0.5)) % 360

def get_moon_nl_sl(year, month, day, hour, minute):
    utc_hour = hour - 5
    utc_min = minute - 30
    if utc_min < 0:
        utc_min += 60
        utc_hour -= 1
    jd = swe.julday(year, month, day, utc_hour + utc_min/60.0)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    pos, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    return get_nl_sl(pos[0])

def get_planetary_positions(year, month, day, hour, minute):
    utc_hour = hour - 5
    utc_min = minute - 30
    if utc_min < 0:
        utc_min += 60
        utc_hour -= 1
        
    jd = swe.julday(year, month, day, utc_hour + utc_min/60.0)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    planets = {
        "SU": swe.SUN, "MO": swe.MOON, "MA": swe.MARS, "ME": swe.MERCURY, 
        "JU": swe.JUPITER, "VE": swe.VENUS, "SA": swe.SATURN, "RA": swe.MEAN_NODE
    }
    
    positions = {}
    ra_exact_lon = 0
    for name, p_id in planets.items():
        pos, _ = swe.calc_ut(jd, p_id, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        lon = pos[0]
        if name == "RA": ra_exact_lon = lon
        positions[name] = {"deg": int(math.floor(lon + 0.5)) % 360, "nl": get_nl_sl(lon)[0], "sl": get_nl_sl(lon)[1]}
        
    ke_exact_lon = (ra_exact_lon + 180) % 360
    ke_nl, ke_sl = get_nl_sl(ke_exact_lon)
    positions["KE"] = {"deg": int(math.floor(ke_exact_lon + 0.5)) % 360, "nl": ke_nl, "sl": ke_sl}
    
    return positions

def ang_dist(d1, d2):
    return min(abs(d1 - d2), 360 - abs(d1 - d2))

def draw_circular_horoscope(year, month, day, hour, minute):
    current_lagna = get_lagna(year, month, day, hour, minute)
    planet_positions = get_planetary_positions(year, month, day, hour, minute)
    inner_offset = 30 - current_lagna

    time_markers = []
    start_t = datetime(year, month, day, 9, 15)
    end_t = datetime(year, month, day, 15, 30)
    curr_t = start_t
    while curr_t <= end_t:
        l_val = get_lagna(year, month, day, curr_t.hour, curr_t.minute)
        time_markers.append((curr_t.strftime("%H:%M"), l_val))
        curr_t += timedelta(minutes=15)
        
    moon_transitions = []
    curr_m = start_t
    prev_nl, prev_sl = get_moon_nl_sl(year, month, day, curr_m.hour, curr_m.minute)
    l_val_start = get_lagna(year, month, day, curr_m.hour, curr_m.minute)
    moon_transitions.append((l_val_start, f"{prev_nl}-{prev_sl}"))
    
    curr_m += timedelta(minutes=1)
    while curr_m <= end_t:
        curr_nl, curr_sl = get_moon_nl_sl(year, month, day, curr_m.hour, curr_m.minute)
        if curr_nl != prev_nl or curr_sl != prev_sl:
            l_val = get_lagna(year, month, day, curr_m.hour, curr_m.minute)
            moon_transitions.append((l_val, f"{curr_nl}-{curr_sl}"))
            prev_nl, prev_sl = curr_nl, curr_sl
        curr_m += timedelta(minutes=1)

    fig = plt.figure(figsize=(16, 16), dpi=150) 
    ax = fig.add_subplot(111, projection='polar')
    ax.set_theta_zero_location("N") 
    ax.set_theta_direction(1)       
    ax.axis('off')

    theta_circle = np.linspace(0, 2 * np.pi, 500)
    ax.plot(theta_circle, np.full_like(theta_circle, 10), color='black', lw=2, zorder=3)
    ax.plot(theta_circle, np.full_like(theta_circle, 14), color='black', lw=2, zorder=3)

    market_zones = [
        (0, "+ve stability in market", "green"), (30, "Accumulation, internal buying", "blue"),
        (60, "-ve disposal / selling", "red"), (90, "+ve less up move, no down", "green"),
        (120, "Sideways no buying or selling", "black"), (150, "-ve selling / profit booking", "red"),
        (180, "+ve uprise / partner", "green"), (210, "-ve loss / obstacle", "red"),
        (240, "+ve gain house, income house", "green"), (270, "-ve consumption of income", "red"),
        (300, "+ve big lots buying", "green"), (330, "-ve heavily -ve", "red")
    ]

    for angle in range(0, 360, 30):
        theta = np.radians(angle)
        ax.plot([theta, theta], [10, 14], color='black', lw=2, zorder=2)
        ax.text(theta, 14.5, f"{angle}°", ha='center', va='center', fontsize=14, fontweight='bold')

    for start_deg, text, color in market_zones:
        center_deg = start_deg + 15
        theta = np.radians(center_deg)
        rot = center_deg
        if 90 < rot <= 270: rot += 180
        ax.text(theta, 12.0, text, ha='center', va='center', fontsize=12, fontweight='bold', color=color, rotation=rot)

    ax.plot(theta_circle, np.full_like(theta_circle, 4), color='black', lw=1.5, zorder=3)
    ax.plot(theta_circle, np.full_like(theta_circle, 7), color='black', lw=1.5, zorder=3)

    empty_rashis = []
    for rashi_idx in range(1, 13):
        start_angle = (rashi_idx - 1) * 30
        end_angle = start_angle + 30
        has_planet = any(start_angle <= data["deg"] < end_angle for data in planet_positions.values())
        if not has_planet:
            empty_rashis.append(rashi_idx) 
            ax.fill_between(np.radians(np.linspace(start_angle + inner_offset, end_angle + inner_offset, 50)), 0, 4, color='lightgrey', alpha=0.6, zorder=1)

    for angle in range(0, 360, 5):
        theta = np.radians(angle + inner_offset)
        if angle % 30 == 0:
            ax.plot([theta, theta], [0, 10], color='black', lw=2, zorder=2)
            ax.text(np.radians(angle + 15 + inner_offset), 10.8, str((angle // 30) + 1), ha='center', va='center', fontsize=22, fontweight='bold', color='darkred')
        else:
            ax.plot([theta, theta], [0, 10], color='gray', lw=1, linestyle='--', zorder=2)
            ax.text(theta, 9.4, str(angle % 30), ha='center', va='center', fontsize=9, color='blue', fontweight='bold')

    used_positions_inner = []
    for planet, data in planet_positions.items():
        shifted_deg = (data["deg"] + inner_offset) % 360
        theta = np.radians(shifted_deg)
        radius = 3.4 
        while any(ang_dist(shifted_deg, p_deg) < 4.0 and abs(radius - p_rad) < 0.6 for p_deg, p_rad in used_positions_inner):
            radius -= 0.65 
        used_positions_inner.append((shifted_deg, radius))
        ax.text(theta, radius, planet, ha='center', va='center', fontsize=7, fontweight='bold', color='purple', bbox=dict(boxstyle="round,pad=0.03", fc="white", ec="none", alpha=0.9), zorder=6)

    ring1_plots = {p: [] for p in planet_positions.keys()}
    for planet, data in planet_positions.items():
        nl = data["nl"]
        if planet not in ring1_plots[nl]: ring1_plots[nl].append(planet)
        if nl in ["RA", "KE"]:
            proxy_lord = RASHI_LORDS[(planet_positions[nl]["deg"] // 30) + 1]
            if planet not in ring1_plots[proxy_lord]: ring1_plots[proxy_lord].append(planet)

    for target_planet, visitors in ring1_plots.items():
        if len(visitors) == 0:
            visitors.append(target_planet)

    ring1_where_is_planet = {p: {"degrees": set(), "rashis": set()} for p in planet_positions.keys()}
    ring1_rashi_filled = {r: False for r in range(1, 13)}

    used_positions_ring1 = []
    for target_planet, visitors in ring1_plots.items():
        if not visitors: continue
        target_deg = planet_positions[target_planet]["deg"]
        shifted_deg = (target_deg + inner_offset) % 360
        theta = np.radians(shifted_deg)
        ring1_rashi_filled[(target_deg // 30) + 1] = True
        
        for visitor in visitors:
            ring1_where_is_planet[visitor]["degrees"].add(target_deg) 
            radius = 4.3 
            while any(ang_dist(shifted_deg, p_deg) < 3.5 and abs(radius - p_rad) < 0.45 for p_deg, p_rad in used_positions_ring1):
                radius += 0.45 
            used_positions_ring1.append((shifted_deg, radius))
            ax.text(theta, radius, visitor, ha='center', va='center', fontsize=7, fontweight='bold', color='teal', bbox=dict(boxstyle="round,pad=0.03", fc="white", ec="black", lw=0.5, alpha=0.9), zorder=6)

    rashi_governors = {r: [] for r in empty_rashis}
    for planet, data in planet_positions.items():
        nl = data["nl"]
        effective_lord = RASHI_LORDS[(planet_positions[nl]["deg"] // 30) + 1] if nl in ["RA", "KE"] else nl
        for r_owned in LORD_TO_RASHIS.get(effective_lord, []):
            if r_owned in empty_rashis and planet not in rashi_governors[r_owned]:
                rashi_governors[r_owned].append(planet)

    for rashi_idx, governors in rashi_governors.items():
        if not governors: continue
        ring1_rashi_filled[rashi_idx] = True
        for g in governors: ring1_where_is_planet[g]["rashis"].add(rashi_idx) 
        theta = np.radians(((rashi_idx - 1) * 30 + 15 + inner_offset) % 360)
        ax.text(theta, 5.5, "-".join(governors), ha='center', va='center', fontsize=11, fontweight='bold', color='darkblue', bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="teal", lw=1.5, alpha=0.95), zorder=7)
        ax.annotate('', xy=(theta + np.radians(13.5), 5.5), xytext=(theta + np.radians(7), 5.5), arrowprops=dict(arrowstyle="-|>", color='teal', lw=2, mutation_scale=12), zorder=6)
        ax.annotate('', xy=(theta - np.radians(13.5), 5.5), xytext=(theta - np.radians(7), 5.5), arrowprops=dict(arrowstyle="-|>", color='teal', lw=2, mutation_scale=12), zorder=6)

    for r in range(1, 13):
        if not ring1_rashi_filled[r]:
            lord = RASHI_LORDS[r]
            ring1_where_is_planet.setdefault(lord, {"degrees": set(), "rashis": set()})["rashis"].add(r)
            theta = np.radians(((r - 1) * 30 + 15 + inner_offset) % 360)
            ax.text(theta, 5.5, lord, ha='center', va='center', fontsize=11, fontweight='bold', color='darkblue', bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="teal", lw=1.5, alpha=0.95), zorder=7)
            ax.annotate('', xy=(theta + np.radians(13.5), 5.5), xytext=(theta + np.radians(7), 5.5), arrowprops=dict(arrowstyle="-|>", color='teal', lw=2, mutation_scale=12), zorder=6)
            ax.annotate('', xy=(theta - np.radians(13.5), 5.5), xytext=(theta - np.radians(7), 5.5), arrowprops=dict(arrowstyle="-|>", color='teal', lw=2, mutation_scale=12), zorder=6)

    ring2_plots_radial = {}
    ring2_governors = {r: [] for r in empty_rashis}
    ring2_rashi_filled = {r: False for r in range(1, 13)}

    for planet, data in planet_positions.items():
        sl = data["sl"]
        if sl in ring1_where_is_planet:
            for deg in ring1_where_is_planet[sl]["degrees"]: ring2_plots_radial.setdefault(deg, []).append(planet)
            for r_idx in ring1_where_is_planet[sl]["rashis"]:
                if planet not in ring2_governors[r_idx]: ring2_governors[r_idx].append(planet)

    used_positions_ring2 = []
    for target_deg, visitors in ring2_plots_radial.items():
        shifted_deg = (target_deg + inner_offset) % 360
        theta = np.radians(shifted_deg)
        if visitors: ring2_rashi_filled[(target_deg // 30) + 1] = True
        for visitor in visitors:
            radius = 7.3 
            while any(ang_dist(shifted_deg, p_deg) < 3.5 and abs(radius - p_rad) < 0.45 for p_deg, p_rad in used_positions_ring2):
                radius += 0.45 
            used_positions_ring2.append((shifted_deg, radius))
            ax.text(theta, radius, visitor, ha='center', va='center', fontsize=7, fontweight='bold', color='indigo', bbox=dict(boxstyle="round,pad=0.03", fc="white", ec="black", lw=0.5, alpha=0.9), zorder=6)

    for rashi_idx, governors in ring2_governors.items():
        if not governors: continue
        ring2_rashi_filled[rashi_idx] = True
        theta = np.radians(((rashi_idx - 1) * 30 + 15 + inner_offset) % 360)
        ax.text(theta, 8.5, "-".join(governors), ha='center', va='center', fontsize=11, fontweight='bold', color='darkred', bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="indigo", lw=1.5, alpha=0.95), zorder=7)
        ax.annotate('', xy=(theta + np.radians(13.5), 8.5), xytext=(theta + np.radians(7), 8.5), arrowprops=dict(arrowstyle="-|>", color='indigo', lw=2, mutation_scale=12), zorder=6)
        ax.annotate('', xy=(theta - np.radians(13.5), 8.5), xytext=(theta - np.radians(7), 8.5), arrowprops=dict(arrowstyle="-|>", color='indigo', lw=2, mutation_scale=12), zorder=6)

    for r in range(1, 13):
        if not ring2_rashi_filled[r]:
            t_start = np.radians(((r - 1) * 30 + inner_offset) % 360)
            t_end = np.radians((r * 30 + inner_offset) % 360)
            ax.plot([t_start, t_end], [7, 10], color='red', lw=3, alpha=0.5, zorder=3)
            ax.plot([t_start, t_end], [10, 7], color='red', lw=3, alpha=0.5, zorder=3)

    for t_str, l_val in time_markers:
        theta = np.radians((l_val + inner_offset) % 360)
        ax.plot([theta, theta], [10, 14], color='black', lw=1.5, linestyle=':', zorder=4)
        rot_deg = (l_val + inner_offset) % 360
        if 90 < rot_deg <= 270: rot_deg += 180
        ax.text(theta, 13.0, f"L-{t_str}" if t_str == "09:15" else t_str, ha='center', va='center', rotation=rot_deg, fontsize=8 if t_str == "09:15" else 5.5, fontweight='bold', color='magenta' if t_str == "09:15" else 'black', bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none", alpha=1.0), zorder=5)

    for l_val, transition_text in moon_transitions:
        theta = np.radians((l_val + inner_offset) % 360)
        ax.plot([theta, theta], [10, 14], color='darkorange', lw=2, linestyle='--', zorder=4)
        rot_deg = (l_val + inner_offset) % 360
        if 90 < rot_deg <= 270: rot_deg += 180
        ax.text(theta, 13.6, transition_text, ha='center', va='center', rotation=rot_deg, fontsize=7, fontweight='bold', color='darkorange', bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="darkorange", lw=1.0, alpha=0.9), zorder=5)

    plt.tight_layout()
    return fig

# --- STREAMLIT UI ---
st.set_page_config(layout="wide", page_title="Astrolabe Explorer")
st.title("Financial Astrolabe Explorer")
st.markdown("Explore intraday astrological shifts dynamically. No database required.")

# Fetch the live, rounded IST date and time
default_date, default_time = get_current_ist_rounded()

col1, col2 = st.columns(2)
with col1:
    selected_date = st.date_input("Select Date", default_date)
with col2:
    selected_time = st.time_input("Select Time", default_time)

st.divider()

with st.spinner("Calculating Ephemeris..."):
    fig = draw_circular_horoscope(
        selected_date.year, 
        selected_date.month, 
        selected_date.day, 
        selected_time.hour, 
        selected_time.minute
    )
    st.pyplot(fig, use_container_width=False)
