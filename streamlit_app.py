import streamlit as st
import pandas as pd
import math
from datetime import datetime
from io import BytesIO

# Page Configuration
st.set_page_config(
    page_title="Solar PV Quote, ROI & SIGET Calculator (El Salvador)",
    page_icon="☀️",
    layout="wide"
)

# El Salvador Departments (Average Peak Sun Hours & Primary Distributor)
DEPT_DATA = {
    "San Salvador": {"sun": 5.15, "dist": "CAESS"},
    "La Libertad": {"sun": 5.20, "dist": "DELSUR"},
    "Santa Ana": {"sun": 5.10, "dist": "CLESA"},
    "San Miguel": {"sun": 5.45, "dist": "EEO"},
    "Sonsonate": {"sun": 5.25, "dist": "CLESA"},
    "Usulután": {"sun": 5.40, "dist": "DEUSEM"},
    "Ahuachapán": {"sun": 5.15, "dist": "CLESA"},
    "La Paz": {"sun": 5.30, "dist": "DELSUR"},
    "La Unión": {"sun": 5.50, "dist": "EEO"},
    "Chalatenango": {"sun": 5.05, "dist": "CAESS"},
    "Cuscatlán": {"sun": 5.15, "dist": "DELSUR"},
    "Morazán": {"sun": 5.30, "dist": "EEO"},
    "San Vicente": {"sun": 5.25, "dist": "DELSUR"},
    "Cabañas": {"sun": 5.20, "dist": "CAESS"},
}

DISTRIBUTOR_PRESETS = {
    "CAESS": {
        "full_name": "CAESS (AES El Salvador)",
        "paperwork_fee": 250.0,
        "note": "Requires AES Digital Portal application, UL 1741 / IEEE 1547 inverter certification, and bidirectional meter reprogramming/installation."
    },
    "DELSUR": {
        "full_name": "DELSUR",
        "paperwork_fee": 230.0,
        "note": "Requires DELSUR Generación Distribuida form, single-line diagram stamped by a SIGET-registered electrical engineer, and bidirectional meter inspection."
    },
    "CLESA": {
        "full_name": "CLESA (AES El Salvador)",
        "paperwork_fee": 250.0,
        "note": "Follows AES El Salvador interconnection standards: UL 1741 anti-islanding compliance, accessible AC disconnect switch, and bidirectional meter setup."
    },
    "EEO": {
        "full_name": "EEO (AES El Salvador)",
        "paperwork_fee": 250.0,
        "note": "Follows AES El Salvador Eastern Zone standards: transformer capacity verification, single-line electrical plan, and bidirectional metering."
    },
    "DEUSEM": {
        "full_name": "DEUSEM (AES El Salvador)",
        "paperwork_fee": 240.0,
        "note": "Follows AES El Salvador standards: SIGET-licensed engineer sign-off and bidirectional meter calibration."
    },
    "BD": {
        "full_name": "B&D Servicios Técnicos",
        "paperwork_fee": 220.0,
        "note": "Requires formal interconnection request with single-line diagram, equipment datasheets, and bidirectional meter installation."
    },
    "EDECSA": {
        "full_name": "EDECSA",
        "paperwork_fee": 220.0,
        "note": "Requires formal interconnection request with single-line diagram, equipment datasheets, and bidirectional meter installation."
    },
}

DEFAULT_PRICES = {
    "panel_100": 65.0,
    "panel_500": 145.0,
    "panel_615": 175.0,
    "panel_650": 190.0,
    "inv_hybrid": 260.0,
    "inv_ongrid": 165.0,
    "inv_offgrid": 220.0,
    "battery_5kwh": 1350.0,
    "rail_bar": 32.0,
    "roof_hook": 4.5,
    "mid_clamp": 2.25,
    "end_clamp": 2.25,
    "grounding_kit": 45.0,
    "pv_cable_m": 1.65,
    "mc4_pair": 3.5,
    "dc_combiner": 140.0,
    "ac_disconnect": 95.0,
}

# Initialize Session State for syncing department -> sun hours & distributor
if "selected_dept" not in st.session_state:
    st.session_state.selected_dept = "San Salvador"
if "sun_hours" not in st.session_state:
    st.session_state.sun_hours = 5.15
if "distributor" not in st.session_state:
    st.session_state.distributor = "CAESS"


def on_dept_change():
    dept = st.session_state.selected_dept
    st.session_state.sun_hours = DEPT_DATA[dept]["sun"]
    st.session_state.distributor = DEPT_DATA[dept]["dist"]


# ================= SIDEBAR: INPUTS =================
with st.sidebar:
    st.header("1. Customer & Utility Info")
    cust_name = st.text_input("Customer Name", placeholder="e.g., Carlos Martínez")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        cust_email = st.text_input("Email Address", placeholder="carlos@ejemplo.sv")
    with col_c2:
        cust_phone = st.text_input("Phone Number", placeholder="+503 7000-0000")

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        cust_city = st.text_input("City / Municipality", placeholder="e.g., Santa Tecla")
    with col_l2:
        cust_dept = st.selectbox(
            "Department",
            options=list(DEPT_DATA.keys()),
            key="selected_dept",
            on_change=on_dept_change
        )

    dist_key = st.selectbox(
        "Local Electric Distributor",
        options=list(DISTRIBUTOR_PRESETS.keys()),
        format_func=lambda k: DISTRIBUTOR_PRESETS[k]["full_name"],
        key="distributor"
    )
    dist_info = DISTRIBUTOR_PRESETS[dist_key]

    st.divider()
    st.header("2. System & Pricing Parameters")

    daily_kwh = st.number_input(
        "Daily Energy Consumption (kWh/day)",
        min_value=0.1,
        max_value=100000.0,
        value=30.0,
        step=1.0,
        format="%.2f"
    )

    sun_hours = st.number_input(
        "Peak Sun Hours Available (HSP)",
        min_value=0.50,
        max_value=24.00,
        step=1.00,
        format="%.2f",
        key="sun_hours",
        help="Use the +/- buttons to step by 1.00, or type any value up to 2 decimal places."
    )

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        panel_watts = st.selectbox("Solar Panel Type", options=[100, 500, 615, 650], index=2, format_func=lambda w: f"{w}W Panel")
    with col_p2:
        system_type = st.selectbox("System Type", options=["Hybrid", "On-Grid", "Off-Grid"])

    st.subheader("Tariff & Labor Settings")
    tariff_category = st.selectbox(
        "El Salvador Tariff Category",
        options=["Residential (~$0.272/kWh)", "Commercial (~$0.240/kWh)", "Custom Rate ($/kWh)"]
    )

    default_rate = 0.272 if "Residential" in tariff_category else (0.240 if "Commercial" in tariff_category else 0.272)
    kwh_rate = st.number_input(
        "Electricity Rate ($ USD/kWh)",
        min_value=0.01,
        max_value=5.00,
        value=default_rate,
        step=0.005,
        format="%.3f"
    )

    labor_mode = st.selectbox(
        "Installation Labor (% of Equipment & Materials)",
        options=["70%", "80%", "90%", "100%", "Custom %"]
    )
    if labor_mode == "Custom %":
        labor_pct = st.number_input("Enter Custom Labor %", min_value=0.0, max_value=300.0, value=75.0, step=5.0)
    else:
        labor_pct = float(labor_mode.replace("%", ""))

    default_paperwork = 0.0 if system_type == "Off-Grid" else dist_info["paperwork_fee"]
    paperwork_cost = st.number_input(
        "Distributor / SIGET Permitting ($ USD)",
        min_value=0.0,
        value=default_paperwork,
        step=10.0,
        format="%.2f"
    )

    include_iva = st.checkbox("Include 13% IVA (El Salvador Tax)", value=True)


# ================= ENGINEERING CALCULATIONS =================
efficiency_factor = 1.25 # Accounts for ~20% real-world system losses
required_kw = (daily_kwh / sun_hours) * efficiency_factor
panel_count = max(1, math.ceil((required_kw * 1000) / panel_watts))
actual_array_kw = (panel_count * panel_watts) / 1000.0
inverter_kw = max(1, math.ceil(actual_array_kw))

# Battery Sizing
battery_units = 0
if system_type in ["Hybrid", "Off-Grid"]:
    autonomy_days = 1.5 if system_type == "Off-Grid" else 1.0
    battery_kwh = (daily_kwh * autonomy_days) / 0.80
    battery_units = max(1, math.ceil(battery_kwh / 5.0))

# Mounting & BOS Hardware
panel_width_m = 0.67 if panel_watts <= 100 else 1.13
total_rail_m = math.ceil((panel_count * panel_width_m * 2) * 1.1)
rail_bars = max(1, math.ceil(total_rail_m / 4.2))
mid_clamps = max(0, (panel_count - 2) * 2)
end_clamps = 4 if panel_count == 1 else 8
roof_hooks = max(2, math.ceil(total_rail_m / 1.2))

max_per_string = 12 if panel_watts == 100 else 9
strings_count = max(1, math.ceil(panel_count / max_per_string))
pv_cable_m = strings_count * 30
mc4_pairs = strings_count * 2

# Default Unit Prices
panel_unit_price = DEFAULT_PRICES.get(f"panel_{panel_watts}", 175.0)
inv_rate = DEFAULT_PRICES["inv_hybrid"] if system_type == "Hybrid" else (DEFAULT_PRICES["inv_ongrid"] if system_type == "On-Grid" else DEFAULT_PRICES["inv_offgrid"])
inv_unit_price = max(450.0, inverter_kw * inv_rate)

bom_rows = [
    {"Component / Material": "Solar PV Modules", "Specification": f"{panel_watts}W Monocrystalline Panels (IEC 61215 / 61730)", "Qty": panel_count, "Unit": "pcs", "Unit Price ($)": panel_unit_price},
    {"Component / Material": "Solar Inverter", "Specification": f"{inverter_kw}kW {system_type.upper()} Inverter (UL 1741 / IEEE 1547, 120/240V)", "Qty": 1, "Unit": "unit", "Unit Price ($)": inv_unit_price},
]

if battery_units > 0:
    bom_rows.append({
        "Component / Material": "Lithium Battery Bank (LiFePO4)",
        "Specification": f"5kWh (48V 100Ah) Modular Battery ({battery_units * 5}kWh Total)",
        "Qty": battery_units,
        "Unit": "units",
        "Unit Price ($)": DEFAULT_PRICES["battery_5kwh"]
    })

bom_rows.extend([
    {"Component / Material": "Aluminum Mounting Rails", "Specification": f"4.2m Anodized Solar Rail (~{total_rail_m}m total)", "Qty": rail_bars, "Unit": "bars", "Unit Price ($)": DEFAULT_PRICES["rail_bar"]},
    {"Component / Material": "Roof L-Feet / Tile Hooks", "Specification": "Stainless Steel Mounting Brackets + Lag Bolts", "Qty": roof_hooks, "Unit": "pcs", "Unit Price ($)": DEFAULT_PRICES["roof_hook"]},
    {"Component / Material": "Mid Clamps", "Specification": "Aluminum Inter-panel Clamps (30-35mm)", "Qty": mid_clamps, "Unit": "pcs", "Unit Price ($)": DEFAULT_PRICES["mid_clamp"]},
    {"Component / Material": "End Clamps", "Specification": "Aluminum Edge Clamps", "Qty": end_clamps, "Unit": "pcs", "Unit Price ($)": DEFAULT_PRICES["end_clamp"]},
