import streamlit as st
import math
import pandas as pd
import io
from fpdf import FPDF

# --- PAGE SETUP ---
st.set_page_config(page_title="Solar Sizer El Salvador", page_icon="☀️", layout="centered")

st.title("☀️ Sistema Solar Inteligente (El Salvador)")
st.write("Herramienta avanzada de cotización para contratistas e ingenieros solares en El Salvador.")

# --- COMPANY PROFILE / LOGO CONFIGURATION ---
st.sidebar.header("🏢 Configuración del Contratista")
company_name = st.sidebar.text_input("Nombre de tu Empresa", value="Solar El Salvador S.A. de C.V.")
warranty_years_panels = st.sidebar.number_input("Garantía de Paneles (Años)", value=25)
warranty_years_inv = st.sidebar.number_input("Garantía de Inversor (Años)", value=5)

st.sidebar.subheader("💳 Condiciones de Pago")
payment_terms_type = st.sidebar.selectbox(
    "Estructura de Hitos",
    ["60% Anticipo / 40% Contra Entrega", "50% Anticipo / 30% Instalación / 20% Pruebas", "100% Contado"]
)

# --- CUSTOMER IDENTIFICATION SECTION ---
st.header("👤 Información del Cliente")
col_c1, col_c2 = st.columns(2)

with col_c1:
    customer_name = st.text_input("Nombre Completo del Cliente", placeholder="Ej. Juan Pérez")
    customer_email = st.text_input("Correo Electrónico", placeholder="ejemplo@correo.com")

with col_c2:
    customer_phone = st.text_input("Número de Teléfono / WhatsApp", placeholder="+503 0000-0000")
    customer_city = st.selectbox(
        "Municipio / Ciudad (El Salvador)", 
        ["San Salvador", "Santa Tecla", "Antiguo Cuscatlán", "San Miguel", "Santa Ana", "Lourdes Colón", "Soyapango", "Ilopango", "Merliot", "Ahuachapán", "Sonsonate", "Usulután", "La Libertad", "Otro"]
    )

# --- TECHNICAL INPUT SECTION ---
st.header("⚡ Parámetros Técnicos")

col1, col2, col3 = st.columns(3)

with col1:
    kw_per_day = st.number_input(
        "Energía Consumida (kWh / Día)", 
        min_value=0.1, 
        max_value=500.0, 
        value=15.0, 
        step=0.5
    )

with col2:
    panel_wattage = st.selectbox(
        "Capacidad del Panel (Watts)",
        options=[100, 600, 610, 615, 650],
        index=1
    )

with col3:
    sun_hours = st.number_input(
        "Horas de Sol Pico / Día", 
        min_value=0.50, 
        max_value=14.00, 
        value=4.55, 
        step=0.01,
        format="%.2f"
    )

# --- SYSTEM CONFIGURATIONS ---
with st.expander("⚙️ Configuración Avanzada del Sistema"):
    distributor = st.selectbox("Distribuidora Eléctrica Local", ["AES (CAESS, CLESA, EEO, DEUSEM)", "DELSUR", "EDESAL", "B&D / Otros"])
    system_type = st.radio("Tipo de Sistema", ["Inyección a Red / On-Grid (Sin Baterías)", "Off-Grid / Híbrido (Con Baterías)"])
    battery_type = st.radio("Tipo de Batería (Si aplica)", ["Litio-Ion (80% Profundidad de Descarga)", "Plomo-Ácido / AGM (50% Profundidad de Descarga)"])
    dod = 0.80 if "Litio" in battery_type else 0.50
    sys_efficiency = st.slider("Eficiencia General del Sistema (%)", min_value=50, max_value=95, value=75) / 100.0

# --- CORE LOGIC CALCULATIONS ---
wh_per_day = kw_per_day * 1000
required_generation_wh = wh_per_day / sys_efficiency
required_array_watts = required_generation_wh / sun_hours

num_panels = math.ceil(required_array_watts / panel_wattage)
actual_array_watts = num_panels * panel_wattage

if actual_array_watts < 1000:
    system_voltage = 12
elif actual_array_watts < 3000:
    system_voltage = 24
else:
    system_voltage = 48

inverter_size_w = math.ceil((actual_array_watts * 1.25) / 500) * 500

# --- EL SALVADOR REGIONAL PRICING RULES ($ USD) ---
panel_unit_cost = 55 if panel_wattage == 100 else 170  
inverter_cost = 0
inverter_qty = 1

if system_type == "Inyección a Red / On-Grid (Sin Baterías)":
    if panel_wattage == 100 or num_panels < 4:
        inverter_type = "Microinversores (AC individual)"
        inverter_qty = num_panels
        recommended_model = "Enphase IQ8 Series"
        inverter_cost = 175 * inverter_qty  
    else:
        inverter_type = "Inversor Central de Cadena (String)"
        recommended_model = "Fronius Primo / SMA"
        inverter_cost = 1950 if actual_array_watts < 6000 else 2850
else:
    if actual_array_watts <= 1200:
        inverter_type = f"Inversor Off-Grid Pura ({system_voltage}V)"
        recommended_model = "Victron Energy MultiPlus"
        inverter_cost = 690
    elif actual_array_watts <= 3000:
        inverter_type = f"Inversor Híbrido Todo-en-Uno ({system_voltage}V)"
        recommended_model = "Growatt SPF"
        inverter_cost = 850
    else:
        inverter_type = "Inversor Híbrido Split-Phase (48V)"
        recommended_model = "EG4 6000XP / Deye"
        inverter_cost = 1650 if actual_array_watts < 8000 else 4200

controller_amps = math.ceil((actual_array_watts / system_voltage) * 1.25)
battery_wh = wh_per_day / dod
battery_ah = math.ceil(battery_wh / system_voltage)

if system_type == "Off-Grid / Híbrido (Con Baterías)":
    if "Litio" in battery_type:
        total_battery_blocks = math.ceil(battery_wh / 5120)
        battery_cost = total_battery_blocks * 1450
    else:
        total_battery_blocks = math.ceil(battery_wh / 1200)
        battery_cost = total_battery_blocks * 240
else:
    battery_cost = 0
    total_battery_blocks = 0

rails_needed = math.ceil(num_panels * 1.2) 
mid_clamps = (num_panels - 1) * 2 if num_panels > 1 else 0
end_clamps = 4
l_feet = math.ceil(rails_needed * 2.5)

racking_total_cost = (rails_needed * 50) + (mid_clamps * 6) + (end_clamps * 7) + (l_feet * 9)
wire_connectors_cost = 210 + (num_panels * 5)  
safety_grounding_cost = 300 if system_type == "Inyección a Red / On-Grid (Sin Baterías)" else 500 

total_panels_cost = num_panels * panel_unit_cost
total_equipment_cost = total_panels_cost + inverter_cost + battery_cost
total_bos_cost = racking_total_cost + wire_connectors_cost + safety_grounding_cost
grand_total = total_equipment_cost + total_bos_cost

# --- STAGING EXCEL AND PRINTING DATAFRAME ---
pricing_data = [
    {"Descripción del Material": f"Paneles Solares ({num_panels} x {panel_wattage}W)", "Cantidad": str(num_panels), "Costo Total Estimado ($ USD)": total_panels_cost},
    {"Descripción del Material": f"Inversor Recomendado ({recommended_model})", "Cantidad": str(inverter_qty), "Costo Total Estimado ($ USD)": inverter_cost},
]

if system_type == "Off-Grid / Híbrido (Con Baterías)":
    pricing_data.append({"Descripción del Material": f"Banco de Baterías ({battery_type})", "Cantidad": str(total_battery_blocks), "Costo Total Estimado ($ USD)": battery_cost})

pricing_data.extend([
    {"Descripción del Material": "Estructuras de Aluminio y Montaje (Rieles, Clamps, L-Feet)", "Cantidad": "Kit", "Costo Total Estimado ($ USD)": math.ceil(racking_total_cost)},
    {"Descripción del Material": "Cableado Eléctrico Solar y Conectores (Cable PV, MC4)", "Cantidad": "Kit", "Costo Total Estimado ($ USD)": math.ceil(wire_connectors_cost)},
    {"Descripción del Material": "Protecciones Eléctricas y Tierras (Caja Combinadora, DPS, Breakers)", "Cantidad": "Kit", "Costo Total Estimado ($ USD)": safety_grounding_cost}
])

df_materials = pd.DataFrame(pricing_data)

# --- OUTPUT DISPLAY SECTION ---
st.header("📋 Resumen del Presupuesto")
if customer_name:
    st.subheader(f"Propuesta Comercial: {customer_name}")
    st.write(f"📍 **Ubicación:** {customer_city} | 📱 **Empresa Emisora:** {company_name}")

st.table(df_materials)

# --- FILE EXPORT ENGINES ---
st.header("💾 Exportar Documentos de Venta")
col_b1, col_b2 = st.columns(2)

# 1. EXCEL EXPORT ENGINE (Requires 'openpyxl' to be installed)
with col_b1:
    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
        df_materials.to_excel(writer, index=False, sheet_name='Lista de Materiales')
        
        # Staging metadata tabs for sales tracking
        df_meta = pd.DataFrame({
            "Campo Remitente": ["Cliente", "Ciudad", "Teléfono", "Proyecto Total", "Términos de Pago"],
            "Detalle Regulado": [customer_name, customer_city, customer_phone, f"${grand_total} USD", payment_terms_type]
        })
        df_meta.to_excel(writer, index=False, sheet_name='Detalles de Cotización')
        
    st.download_button(
        label="📊 Descargar Lista en Excel (.xlsx)",
        data=buffer_excel.getvalue(),
        file_name=f"Materiales_Solar_{customer_name.replace(' ', '_') if customer_name else 'Cliente'}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# 2. PDF EXPORT ENGINE (With custom warranties and payment clauses)
with col_b2:
    def generate_pdf():
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 8, company_name.upper(), ln=True, align="L")
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 4, "Soluciones de Energía Renovable en El Salvador", ln=True, align="L")
        pdf.line(10, 23, 200, 23)
        pdf.ln(8)
        
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "COTIZACION FORMAL DE MATERIALES", ln=True, align="C")
        pdf.ln(4)
        
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, "1. Datos del Cliente & Ubicación", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 5, f"Nombre: {customer_name if customer_name else 'N/A'}", ln=True)
        pdf.cell(0, 5, f"Destino / Ciudad: {customer_city}, El Salvador", ln=True)
        pdf.cell(0, 5, f"Contacto: {customer_phone if customer_phone else 'N/A'} | {customer_email if customer_email else 'N/A'}", ln=True)
        pdf.ln(4)
        
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, "2. Especificaciones Técnicas Básicas", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 5, f"Arreglo Diseñado: {actual_array_watts}W usando Paneles de {panel_wattage}W", ln=True)