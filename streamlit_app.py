import streamlit as st
import math
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import csv
import os
import webbrowser

# Datos de departamentos de El Salvador (HSP promedio y distribuidora principal)
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
        "note": "Requiere solicitud en Portal Digital AES, inversores UL 1741 / IEEE 1547 y reprogramación/cambio a medidor bidireccional."
    },
    "DELSUR": {
        "full_name": "DELSUR",
        "paperwork_fee": 230.0,
        "note": "Requiere formulario Generación Distribuida DELSUR, diagrama unifilar firmado por ingeniero SIGET e inspección de medidor bidireccional."
    },
    "CLESA": {
        "full_name": "CLESA (AES El Salvador)",
        "paperwork_fee": 250.0,
        "note": "Cumple normativa AES El Salvador: protección anti-isla UL 1741, desconectador AC exterior visible y medidor bidireccional."
    },
    "EEO": {
        "full_name": "EEO (AES El Salvador)",
        "paperwork_fee": 250.0,
        "note": "Normativa AES Zona Oriental: verificación de capacidad de transformador, plano unifilar y medición bidireccional."
    },
    "DEUSEM": {
        "full_name": "DEUSEM (AES El Salvador)",
        "paperwork_fee": 240.0,
        "note": "Normativa AES El Salvador: firma de ingeniero registrado en SIGET y calibración de medidor bidireccional."
    },
    "BD": {
        "full_name": "B&D Servicios Técnicos",
        "paperwork_fee": 220.0,
        "note": "Requiere solicitud formal de interconexión, diagrama unifilar, fichas técnicas e instalación de medidor bidireccional."
    },
    "EDECSA": {
        "full_name": "EDECSA",
        "paperwork_fee": 220.0,
        "note": "Requiere solicitud formal de interconexión, diagrama unifilar, fichas técnicas e instalación de medidor bidireccional."
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


class SolarCalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Calculadora Solar FV, Cotización, ROI y SIGET (El Salvador)")
        self.root.geometry("1260x780")
        self.root.configure(bg="#f1f5f9")

        self.bom_items = []
        self.actual_array_kw = 0.0
        self.panel_count = 0
        self.inverter_kw = 0
        self.wiring_title = ""
        self.wiring_advice = ""
        self.siget_items = []

        self._setup_styles()
        self._build_ui()
        self.calculate_system()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f1f5f9")
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("Header.TLabel", font=("Segoe UI", 15, "bold"), background="#f1f5f9", foreground="#0f172a")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 9), background="#f1f5f9", foreground="#475569")
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), background="#ffffff", foreground="#2563eb")
        style.configure("Field.TLabel", font=("Segoe UI", 9, "bold"), background="#ffffff", foreground="#1e293b")
        style.configure("TButton", font=("Segoe UI", 9, "bold"), padding=6)
        style.configure("Primary.TButton", background="#2563eb", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#1d4ed8")])
        style.configure("Excel.TButton", background="#15803d", foreground="#ffffff")
        style.map("Excel.TButton", background=[("active", "#166534")])
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=26)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e2e8f0", foreground="#0f172a")

    def _build_ui(self):
        # Encabezado
        header_frame = ttk.Frame(self.root, padding=(15, 10))
        header_frame.pack(fill="x")
        ttk.Label(header_frame, text="☀️ Calculadora Solar FV, Cotización y Retorno de Inversión (El Salvador)", style="Header.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="Dimensionamiento técnico, lista de materiales (BOM), precios en USD (+13% IVA), ahorro mensual y normativa SIGET.", style="SubHeader.TLabel").pack(anchor="w")

        # Contenedor principal de 2 columnas
        main_frame = ttk.Frame(self.root, padding=(15, 5, 15, 15))
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1, minsize=380)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=1)

        # ================= PANEL IZQUIERDO (ENTRADAS) =================
        left_card = ttk.Frame(main_frame, style="Card.TFrame", padding=15)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # Canvas con scroll para el formulario izquierdo
        canvas = tk.Canvas(left_card, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_card, orient="vertical", command=canvas.yview)
        form_frame = ttk.Frame(canvas, style="Card.TFrame")

        form_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=form_frame, anchor="nw", width=350)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 1. Datos del Cliente
        ttk.Label(form_frame, text="1. Datos del Cliente y Distribuidora", style="Section.TLabel").pack(anchor="w", pady=(0, 8))

        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_city = tk.StringVar()
        self.var_dept = tk.StringVar(value="San Salvador")
        self.var_dist = tk.StringVar(value="CAESS")

        self._add_entry(form_frame, "Nombre del Cliente:", self.var_name)
        self._add_entry(form_frame, "Correo Electrónico:", self.var_email)
        self._add_entry(form_frame, "Teléfono:", self.var_phone)
        self._add_entry(form_frame, "Ciudad / Municipio:", self.var_city)

        ttk.Label(form_frame, text="Departamento (El Salvador):", style="Field.TLabel").pack(anchor="w", pady=(4, 2))
        cb_dept = ttk.Combobox(form_frame, textvariable=self.var_dept, values=list(DEPT_DATA.keys()), state="readonly")
        cb_dept.pack(fill="x", pady=(0, 6))
        cb_dept.bind("<<ComboboxSelected>>", self.on_dept_change)

        ttk.Label(form_frame, text="Distribuidora Eléctrica Local:", style="Field.TLabel").pack(anchor="w", pady=(4, 2))
        cb_dist = ttk.Combobox(form_frame, textvariable=self.var_dist, values=list(DISTRIBUTOR_PRESETS.keys()), state="readonly")
        cb_dist.pack(fill="x", pady=(0, 12))
        cb_dist.bind("<<ComboboxSelected>>", lambda e: self.calculate_system())

        # 2. Parámetros Técnicos y Tarifa
        ttk.Label(form_frame, text="2. Parámetros del Sistema y Tarifa", style="Section.TLabel").pack(anchor="w", pady=(6, 8))

        self.var_daily_kwh = tk.StringVar(value="30")
        self._add_entry(form_frame, "Consumo Diario Estimado (kWh/día) [Manual]:", self.var_daily_kwh)

        # Horas Pico Solar con entrada manual + botones -1/+1
        ttk.Label(form_frame, text="Horas Pico Solar (HSP) [Hasta 2 decimales]:", style="Field.TLabel").pack(anchor="w", pady=(4, 2))
        hsp_row = ttk.Frame(form_frame, style="Card.TFrame")
        hsp_row.pack(fill="x", pady=(0, 8))
        self.var_sun_hours = tk.StringVar(value="5.15")
        ttk.Button(hsp_row, text="-1", width=4, command=lambda: self.adjust_sun_hours(-1)).pack(side="left")
        ttk.Entry(hsp_row, textvariable=self.var_sun_hours, justify="center").pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(hsp_row, text="+1", width=4, command=lambda: self.adjust_sun_hours(1)).pack(side="left")

        ttk.Label(form_frame, text="Tipo de Panel Solar:", style="Field.TLabel").pack(anchor="w", pady=(4, 2))
        self.var_panel_watts = tk.StringVar(value="615W")
        cb_panel = ttk.Combobox(form_frame, textvariable=self.var_panel_watts, values=["100W", "500W", "615W", "650W"], state="readonly")
        cb_panel.pack(fill="x", pady=(0, 6))

        ttk.Label(form_frame, text="Tipo de Sistema:", style="Field.TLabel").pack(anchor="w", pady=(4, 2))
        self.var_sys_type = tk.StringVar(value="Híbrido (Red + Baterías)")
        cb_sys = ttk.Combobox(form_frame, textvariable=self.var_sys_type, values=["Híbrido (Red + Baterías)", "On-Grid (Inyección a Red)", "Off-Grid (Aislado con Baterías)"], state="readonly")
        cb_sys.pack(fill="x", pady=(0, 6))
        cb_sys.bind("<<ComboboxSelected>>", lambda e: self.calculate_system())

        ttk.Label(form_frame, text="Categoría Tarifaria (El Salvador):", style="Field.TLabel").pack(anchor="w", pady=(4, 2))