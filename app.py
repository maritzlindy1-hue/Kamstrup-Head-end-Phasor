import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Kamstrup Estimated Phasor", layout="wide")

st.title("Kamstrup Estimated Phasor Viewer")
st.caption("Builds an estimated phasor from voltage, current, PF and leading/lagging direction.")

st.markdown("""
Upload a CSV with columns:

`meter`, `phase`, `voltage`, `current`, `pf`, `power_direction`, `var_direction`

Accepted phase values: `L1`, `L2`, `L3`  
Accepted power_direction: `import`, `export`  
Accepted var_direction: `lagging`, `leading`

Voltage reference angles:
- L1 = 0°
- L2 = -120°
- L3 = +120°
""")

sample = pd.DataFrame([
    {"meter": "28500183", "phase": "L1", "voltage": 230.5, "current": 45.2, "pf": 0.98, "power_direction": "import", "var_direction": "lagging"},
    {"meter": "28500183", "phase": "L2", "voltage": 231.0, "current": 42.8, "pf": 0.96, "power_direction": "import", "var_direction": "lagging"},
    {"meter": "28500183", "phase": "L3", "voltage": 229.8, "current": 47.5, "pf": 0.97, "power_direction": "import", "var_direction": "lagging"},
])

uploaded = st.file_uploader("Upload CSV", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)
else:
    st.info("No file uploaded yet. Using sample data below.")
    df = sample.copy()

required_cols = ["meter", "phase", "voltage", "current", "pf", "power_direction", "var_direction"]
missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

df["phase"] = df["phase"].astype(str).str.upper().str.strip()
df["power_direction"] = df["power_direction"].astype(str).str.lower().str.strip()
df["var_direction"] = df["var_direction"].astype(str).str.lower().str.strip()
df["pf"] = pd.to_numeric(df["pf"], errors="coerce").abs().clip(0, 1)
df["voltage"] = pd.to_numeric(df["voltage"], errors="coerce")
df["current"] = pd.to_numeric(df["current"], errors="coerce")

phase_voltage_angles = {
    "L1": 0,
    "L2": -120,
    "L3": 120,
}

def estimate_current_angle(row):
    phase = row["phase"]
    v_angle = phase_voltage_angles.get(phase)

    if v_angle is None or pd.isna(row["pf"]):
        return None

    theta = math.degrees(math.acos(row["pf"]))

    # Lagging current is behind voltage. Leading current is ahead of voltage.
    if row["var_direction"] == "leading":
        i_angle = v_angle + theta
    else:
        i_angle = v_angle - theta

    # If site is expected to import but meter shows export, CT may be reversed.
    # Flip current vector by 180 degrees for export indication.
    if row["power_direction"] == "export":
        i_angle += 180

    # Normalize to -180 to +180
    while i_angle > 180:
        i_angle -= 360
    while i_angle <= -180:
        i_angle += 360

    return i_angle

def polar_to_xy(magnitude, angle_deg, scale=1):
    rad = math.radians(angle_deg)
    return magnitude * math.cos(rad) * scale, magnitude * math.sin(rad) * scale

df["voltage_angle_deg"] = df["phase"].map(phase_voltage_angles)
df["current_angle_deg"] = df.apply(estimate_current_angle, axis=1)
df["estimated_angle_from_pf_deg"] = df["pf"].apply(lambda x: math.degrees(math.acos(x)) if pd.notna(x) else None)
df["apparent_power_va"] = df["voltage"] * df["current"]
df["active_power_w_est"] = df["apparent_power_va"] * df["pf"]

st.subheader("Input and calculated values")
st.dataframe(df, use_container_width=True)

meter_options = sorted(df["meter"].astype(str).unique())
selected_meter = st.selectbox("Select meter", meter_options)

plot_df = df[df["meter"].astype(str) == selected_meter].copy()

if plot_df.empty:
    st.warning("No data for selected meter.")
    st.stop()

# Scale current so it fits visually on same chart as voltage.
max_v = plot_df["voltage"].max()
max_i = plot_df["current"].max()
current_scale = max_v / max_i if max_i and max_i > 0 else 1

fig = go.Figure()

for _, row in plot_df.iterrows():
    phase = row["phase"]

    if pd.notna(row["voltage_angle_deg"]) and pd.notna(row["voltage"]):
        vx, vy = polar_to_xy(row["voltage"], row["voltage_angle_deg"])
        fig.add_trace(go.Scatter(
            x=[0, vx], y=[0, vy],
            mode="lines+markers+text",
            text=["", f"V{phase}<br>{row['voltage_angle_deg']:.1f}°"],
            textposition="top center",
            name=f"V{phase}",
            hovertemplate=f"V{phase}<br>Voltage: {row['voltage']} V<br>Angle: {row['voltage_angle_deg']:.1f}°<extra></extra>"
        ))

    if pd.notna(row["current_angle_deg"]) and pd.notna(row["current"]):
        ix, iy = polar_to_xy(row["current"], row["current_angle_deg"], current_scale)
        fig.add_trace(go.Scatter(
            x=[0, ix], y=[0, iy],
            mode="lines+markers+text",
            text=["", f"I{phase}<br>{row['current_angle_deg']:.1f}°"],
            textposition="bottom center",
            name=f"I{phase}",
            hovertemplate=(
                f"I{phase}<br>"
                f"Current: {row['current']} A<br>"
                f"Scaled for display<br>"
                f"Estimated angle: {row['current_angle_deg']:.1f}°<br>"
                f"PF angle: {row['estimated_angle_from_pf_deg']:.1f}°<extra></extra>"
            )
        ))

fig.update_layout(
    title=f"Estimated Phasor Diagram - Meter {selected_meter}",
    xaxis_title="X",
    yaxis_title="Y",
    yaxis_scaleanchor="x",
    height=700,
    showlegend=True,
)

fig.add_shape(type="circle", xref="x", yref="y", x0=-max_v, y0=-max_v, x1=max_v, y1=max_v, line_dash="dot")

st.plotly_chart(fig, use_container_width=True)

st.subheader("Important note")
st.warning("""
This is an estimated phasor, not a true meter phasor. 
It uses PF to estimate the current angle. 
For a true phasor you need actual voltage/current angle OBIS registers from the meter or a direct engineering read.
""")

st.subheader("Quick interpretation")
st.markdown("""
- Current close to voltage = good PF / normal load.
- Current almost opposite voltage = possible CT reversal or export condition.
- Current angle sitting closer to another phase = possible crossed CT or voltage/current phase mismatch.
- This app assumes normal phase sequence: L1 = 0°, L2 = -120°, L3 = +120°.
""")