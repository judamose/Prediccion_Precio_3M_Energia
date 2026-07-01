import streamlit as st
import requests
import pandas as pd
import numpy as np
import json
from datetime import datetime, date
import io

# ─────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DATAROBOT
# ─────────────────────────────────────────────────────────────────
DATAROBOT_API_KEY      = "NmEzNGE0ZDE5YWE2YzcyMjBhZWQ4MGE5OklEQlNDa0F1M0JPK3IvdFVQM05pdkZjaTAvV2xWTUpCdVpQMXgyUXpWWXM9"   # ← pega tu API key aquí
DATAROBOT_DEPLOYMENT_ID = "6a4454a9c96a31caeb714f9b"  # ← pega tu deployment ID aquí
DATAROBOT_HOST         = "https://app.datarobot.com"

PREDICT_URL = f"{DATAROBOT_HOST}/predApi/v1.0/deployments/{DATAROBOT_DEPLOYMENT_ID}/predictions"

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚡ Predictor Precio Energía Colombia",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────
# CSS PERSONALIZADO — TEMA ENERGÍA ELÉCTRICA
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Fondo principal */
    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #0d1b2a 50%, #0a1628 100%);
        color: #e0e6f0;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1b2a 0%, #0a1628 100%);
        border-right: 1px solid #1e3a5f;
    }

    /* Títulos */
    h1, h2, h3 { color: #00d4ff !important; }

    /* Cards métricas */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #0d2137 0%, #0a1e32 100%);
        border: 1px solid #1e4a7a;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 0 20px rgba(0,212,255,0.1);
    }
    [data-testid="metric-container"] label { color: #7ab8d9 !important; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #00d4ff !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }

    /* Sliders */
    .stSlider > div > div > div > div { background: #00d4ff !important; }

    /* Botón principal */
    .stButton > button {
        background: linear-gradient(135deg, #0066cc 0%, #0099ff 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 14px 32px;
        font-size: 18px;
        font-weight: 700;
        width: 100%;
        box-shadow: 0 0 25px rgba(0,153,255,0.5);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #0099ff 0%, #00ccff 100%);
        box-shadow: 0 0 40px rgba(0,204,255,0.7);
        transform: translateY(-2px);
    }

    /* Resultado destacado */
    .resultado-box {
        background: linear-gradient(135deg, #003366 0%, #004080 100%);
        border: 2px solid #00d4ff;
        border-radius: 16px;
        padding: 30px;
        text-align: center;
        box-shadow: 0 0 40px rgba(0,212,255,0.3);
        margin: 20px 0;
    }
    .resultado-precio {
        font-size: 4rem;
        font-weight: 900;
        color: #00ff88;
        text-shadow: 0 0 20px rgba(0,255,136,0.5);
    }
    .resultado-label {
        font-size: 1.2rem;
        color: #7ab8d9;
        margin-bottom: 10px;
    }

    /* Alerta de riesgo */
    .riesgo-bajo    { background: #0a2e1a; border: 1px solid #00cc44; border-radius: 10px; padding: 15px; }
    .riesgo-medio   { background: #2e2a0a; border: 1px solid #ffaa00; border-radius: 10px; padding: 15px; }
    .riesgo-alto    { background: #2e1a0a; border: 1px solid #ff6600; border-radius: 10px; padding: 15px; }
    .riesgo-critico { background: #2e0a0a; border: 1px solid #ff0000; border-radius: 10px; padding: 15px; }

    /* Info boxes */
    .info-card {
        background: rgba(0,60,100,0.3);
        border: 1px solid #1e4a7a;
        border-radius: 10px;
        padding: 15px;
        margin: 8px 0;
    }

    /* Separadores */
    hr { border-color: #1e3a5f !important; }

    /* Número inputs */
    .stNumberInput > div > div > input {
        background: #0d1b2a;
        border: 1px solid #1e4a7a;
        color: #e0e6f0;
        border-radius: 8px;
    }

    /* Select box */
    .stSelectbox > div > div {
        background: #0d1b2a;
        border: 1px solid #1e4a7a;
        color: #e0e6f0;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #7ab8d9;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #00d4ff !important;
        border-bottom: 2px solid #00d4ff !important;
    }

    /* Success/Error */
    .stSuccess { background: rgba(0,200,100,0.1) !important; border-color: #00cc44 !important; }
    .stError   { background: rgba(200,0,0,0.1)   !important; border-color: #ff3333 !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def clasificar_oni(oni):
    if   oni >=  2.0: return "🔴 El Niño Muy Fuerte", "critico"
    elif oni >=  1.5: return "🟠 El Niño Fuerte",     "alto"
    elif oni >=  1.0: return "🟡 El Niño Moderado",   "medio"
    elif oni >=  0.5: return "🟡 El Niño Débil",      "medio"
    elif oni <= -2.0: return "🔵 La Niña Muy Fuerte", "bajo"
    elif oni <= -1.5: return "🔵 La Niña Fuerte",     "bajo"
    elif oni <= -1.0: return "🔵 La Niña Moderada",   "bajo"
    elif oni <= -0.5: return "🔵 La Niña Débil",      "bajo"
    else:             return "⚪ Fase Neutra",          "bajo"

def nivel_riesgo_precio(precio):
    if   precio < 200:  return "🟢 Bajo",    "bajo",    "#00cc44"
    elif precio < 400:  return "🟡 Medio",   "medio",   "#ffaa00"
    elif precio < 700:  return "🟠 Alto",    "alto",    "#ff6600"
    else:               return "🔴 Crítico", "critico", "#ff0000"

def construir_features_fila(fecha, oni, aportes, embalses, precio_actual,
                             oni_lag1, oni_lag3, oni_lag6,
                             aportes_lag1, aportes_lag3,
                             embalses_lag1, embalses_lag3):
    """Construye el diccionario de features que necesita el modelo."""
    mes = fecha.month
    año = fecha.year
    trimestre = (mes - 1) // 3 + 1

    def fase(v):
        if v >= 2.0: return "Nino_Muy_Fuerte"
        if v >= 1.5: return "Nino_Fuerte"
        if v >= 1.0: return "Nino_Moderado"
        if v >= 0.5: return "Nino_Debil"
        if v <=-2.0: return "Nina_Muy_Fuerte"
        if v <=-1.5: return "Nina_Fuerte"
        if v <=-1.0: return "Nina_Moderada"
        if v <=-0.5: return "Nina_Debil"
        return "Neutro"

    oni_delta = round(oni - oni_lag3, 2)
    stress    = round(oni * 10 + max(0, 65 - embalses), 2)
    deficit   = round(max(0, 80 - aportes), 1)

    return {
        "Fecha":                fecha.strftime("%Y-%m-%d"),
        "Mes":                  mes,
        "Año":                  año,
        "Trimestre":            trimestre,
        "ONI":                  oni,
        "ONI_lag_1":            oni_lag1,
        "ONI_lag_3":            oni_lag3,
        "ONI_lag_6":            oni_lag6,
        "ONI_delta_3m":         oni_delta,
        "Fase_ENSO":            fase(oni),
        "Es_Nino":              int(oni >= 0.5),
        "Es_Nina":              int(oni <= -0.5),
        "Aportes_Porcentaje":   aportes,
        "Aportes_lag_1":        aportes_lag1,
        "Aportes_lag_3":        aportes_lag3,
        "Aportes_MA_3":         round((aportes + aportes_lag1 + aportes_lag3) / 3, 1),
        "Aportes_MA_6":         round((aportes + aportes_lag1 + aportes_lag3) / 3, 1),
        "Deficit_Aportes":      deficit,
        "Embalses_Porcentaje":  embalses,
        "Embalses_lag_1":       embalses_lag1,
        "Embalses_lag_3":       embalses_lag3,
        "Embalses_MA_3":        round((embalses + embalses_lag1 + embalses_lag3) / 3, 1),
        "Embalses_delta":       round(embalses - embalses_lag3, 1),
        "Precio_Bolsa":         precio_actual,
        "Precio_lag_1":         precio_actual,
        "Precio_lag_3":         precio_actual,
        "Precio_MA_3":          precio_actual,
        "Stress_Hidrico":       stress,
    }

def hacer_prediccion(datos_fila):
    """Llama a la API de DataRobot y retorna la predicción."""
    df = pd.DataFrame([datos_fila])
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    headers = {
        "Authorization": f"Token {DATAROBOT_API_KEY}",
        "Content-Type": "text/plain; charset=UTF-8",
        "datarobot-key": "",
    }
    response = requests.post(
        PREDICT_URL,
        data=csv_bytes,
        headers=headers,
        timeout=60
    )
    response.raise_for_status()
    result = response.json()
    pred = result["data"][0]["prediction"]
    return round(pred, 2)


# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding: 20px 0 10px 0;">
    <div style="font-size:4rem;">⚡</div>
    <h1 style="font-size:2.5rem; margin:0; color:#00d4ff;">
        Predictor de Precio de Energía
    </h1>
    <p style="font-size:1.1rem; color:#7ab8d9; margin-top:8px;">
        Mercado Eléctrico Colombiano · Modelo IA con datos XM + NOAA
    </p>
    <p style="color:#4a7a9b; font-size:0.9rem;">
        Predice el precio de bolsa 3 meses hacia adelante usando El Niño, embalses y aportes hídricos
    </p>
</div>
<hr/>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# SIDEBAR — CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    st.markdown("---")

    st.markdown("### 🔑 DataRobot API")
    api_key_input = st.text_input(
        "API Key", value=DATAROBOT_API_KEY,
        type="password", placeholder="Token DataRobot..."
    )
    deployment_id_input = st.text_input(
        "Deployment ID", value=DATAROBOT_DEPLOYMENT_ID,
        placeholder="ID del despliegue..."
    )
    if api_key_input:   DATAROBOT_API_KEY       = api_key_input
    if deployment_id_input: DATAROBOT_DEPLOYMENT_ID = deployment_id_input

    st.markdown("---")
    st.markdown("### 📅 Fecha de predicción")
    fecha_pred = st.date_input(
        "Mes a predecir",
        value=date.today().replace(day=1),
        help="Selecciona el mes para el que quieres predecir el precio 3 meses después"
    )

    st.markdown("---")
    st.markdown("""
    <div class="info-card">
        <b>🧠 Cómo funciona</b><br><br>
        El modelo aprendió la cadena causal:<br><br>
        🌊 <b>ONI</b> (El Niño)<br>
        &nbsp;&nbsp;&nbsp;&nbsp;↓<br>
        🌧️ <b>Menos lluvia</b><br>
        &nbsp;&nbsp;&nbsp;&nbsp;↓<br>
        💧 <b>Menos aportes</b><br>
        &nbsp;&nbsp;&nbsp;&nbsp;↓<br>
        🏞️ <b>Embalses bajos</b><br>
        &nbsp;&nbsp;&nbsp;&nbsp;↓<br>
        🔥 <b>Más térmica</b><br>
        &nbsp;&nbsp;&nbsp;&nbsp;↓<br>
        💰 <b>Precio sube</b>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# TABS PRINCIPALES
# ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "🎯 Predicción Manual",
    "📊 Análisis de Escenarios",
    "📁 Predicción por Lote"
])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — PREDICCIÓN MANUAL
# ══════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 🌊 Variables Climáticas e Hidrológicas")
    st.markdown("Ingresa los valores actuales para predecir el precio de bolsa en 3 meses")
    st.markdown("")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 🌊 Índice ONI (El Niño)")
        oni = st.slider(
            "ONI actual",
            min_value=-3.0, max_value=3.0, value=0.1, step=0.1,
            help="Oceanic Niño Index. ≥+0.5 = El Niño | ≤-0.5 = La Niña"
        )
        fase_oni, _ = clasificar_oni(oni)
        st.markdown(f"**Fase ENSO:** {fase_oni}")

        oni_lag1 = st.number_input("ONI hace 1 mes", value=0.1, step=0.1, format="%.1f")
        oni_lag3 = st.number_input("ONI hace 3 meses", value=0.0, step=0.1, format="%.1f")
        oni_lag6 = st.number_input("ONI hace 6 meses", value=-0.1, step=0.1, format="%.1f")

    with col2:
        st.markdown("#### 💧 Aportes Hídricos")
        aportes = st.slider(
            "Aportes % (media histórica)",
            min_value=20.0, max_value=200.0, value=95.0, step=1.0,
            help="Aportes hídricos al SIN como % de la media histórica. <70% = déficit"
        )
        if aportes < 70:
            st.markdown("⚠️ **Déficit hídrico** — por debajo del umbral")
        elif aportes > 120:
            st.markdown("✅ **Superávit hídrico** — condición favorable")
        else:
            st.markdown("✅ **Condición normal**")

        aportes_lag1 = st.number_input("Aportes % hace 1 mes", value=92.0, step=1.0, format="%.1f")
        aportes_lag3 = st.number_input("Aportes % hace 3 meses", value=88.0, step=1.0, format="%.1f")

    with col3:
        st.markdown("#### 🏞️ Embalses")
        embalses = st.slider(
            "Embalses % capacidad",
            min_value=10.0, max_value=100.0, value=65.0, step=1.0,
            help="Volumen útil total embalses SIN como % capacidad máxima. <40% = emergencia"
        )
        if embalses < 40:
            st.markdown("🚨 **Emergencia energética** — embalses críticos")
        elif embalses < 60:
            st.markdown("⚠️ **Nivel bajo** — monitoreo requerido")
        else:
            st.markdown("✅ **Nivel adecuado**")

        embalses_lag1 = st.number_input("Embalses % hace 1 mes", value=67.0, step=1.0, format="%.1f")
        embalses_lag3 = st.number_input("Embalses % hace 3 meses", value=70.0, step=1.0, format="%.1f")

    st.markdown("---")

    col_precio, col_vacio = st.columns([1, 2])
    with col_precio:
        st.markdown("#### 💰 Precio Actual")
        precio_actual = st.number_input(
            "Precio Bolsa actual (COP/kWh)",
            min_value=0.0, max_value=2000.0, value=175.0, step=10.0,
            help="Precio de bolsa nacional del mes actual"
        )

    st.markdown("")

    # ── BOTÓN PREDICCIÓN ─────────────────────────────────────────
    col_btn1, col_btn2, col_btn3 = st.columns([1,2,1])
    with col_btn2:
        predecir = st.button("⚡ PREDECIR PRECIO EN 3 MESES", key="btn_predecir")

    if predecir:
        if not DATAROBOT_API_KEY or not DATAROBOT_DEPLOYMENT_ID:
            st.error("⚠️ Ingresa tu API Key y Deployment ID en el panel lateral izquierdo.")
        else:
            with st.spinner("🔄 Consultando el modelo de IA..."):
                try:
                    datos = construir_features_fila(
                        fecha_pred, oni, aportes, embalses, precio_actual,
                        oni_lag1, oni_lag3, oni_lag6,
                        aportes_lag1, aportes_lag3,
                        embalses_lag1, embalses_lag3
                    )
                    # Actualizar URL con deployment ID actual
                    url = f"{DATAROBOT_HOST}/predApi/v1.0/deployments/{DATAROBOT_DEPLOYMENT_ID}/predictions"
                    df_pred = pd.DataFrame([datos])
                    csv_bytes = df_pred.to_csv(index=False).encode("utf-8")
                    headers = {
                        "Authorization": f"Token {DATAROBOT_API_KEY}",
                        "Content-Type": "text/plain; charset=UTF-8",
                    }
                    response = requests.post(url, data=csv_bytes, headers=headers, timeout=60)
                    response.raise_for_status()
                    result = response.json()
                    precio_pred = round(result["data"][0]["prediction"], 2)

                    nivel_txt, nivel_clase, nivel_color = nivel_riesgo_precio(precio_pred)
                    fecha_resultado = fecha_pred.replace(month=((fecha_pred.month - 1 + 3) % 12) + 1)

                    # ── RESULTADO PRINCIPAL ───────────────────────
                    st.markdown(f"""
                    <div class="resultado-box">
                        <div class="resultado-label">⚡ Precio de Bolsa Predicho para {fecha_resultado.strftime("%B %Y")}</div>
                        <div class="resultado-precio">{precio_pred:,.0f}</div>
                        <div style="color:#7ab8d9; font-size:1.3rem; margin-top:5px;">COP / kWh</div>
                        <div style="margin-top:15px; font-size:1.2rem;">
                            Nivel de Riesgo: <span style="color:{nivel_color}; font-weight:700;">{nivel_txt}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ── MÉTRICAS COMPARATIVAS ─────────────────────
                    st.markdown("#### 📊 Análisis del Resultado")
                    m1, m2, m3, m4 = st.columns(4)
                    cambio = precio_pred - precio_actual
                    cambio_pct = (cambio / precio_actual * 100) if precio_actual > 0 else 0

                    m1.metric("Precio Actual", f"{precio_actual:,.0f} COP/kWh")
                    m2.metric("Precio Predicho", f"{precio_pred:,.0f} COP/kWh",
                              delta=f"{cambio:+,.0f} COP/kWh")
                    m3.metric("Variación %", f"{cambio_pct:+.1f}%")
                    m4.metric("Nivel de Riesgo", nivel_txt.split(" ", 1)[1] if " " in nivel_txt else nivel_txt)

                    # ── INTERPRETACIÓN ────────────────────────────
                    st.markdown("#### 💡 Interpretación")
                    fase_oni_txt, _ = clasificar_oni(oni)

                    col_i1, col_i2 = st.columns(2)
                    with col_i1:
                        st.markdown(f"""
                        <div class="info-card">
                            <b>🌊 Condición climática</b><br>
                            {fase_oni_txt}<br>
                            <small>ONI actual: {oni:+.1f} | Tendencia 3m: {oni-oni_lag3:+.1f}</small>
                        </div>
                        <div class="info-card" style="margin-top:10px;">
                            <b>💧 Situación hídrica</b><br>
                            Aportes: {aportes:.0f}% de la media histórica<br>
                            Embalses: {embalses:.0f}% de capacidad<br>
                            <small>Déficit aportes: {max(0, 80-aportes):.1f}%</small>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_i2:
                        if precio_pred > precio_actual * 1.3:
                            msg = "⚠️ Se espera un incremento significativo en el precio de bolsa. Considera contratos de cobertura o ajuste de tarifas."
                        elif precio_pred > precio_actual * 1.1:
                            msg = "📈 Se espera un incremento moderado. Monitoreo recomendado."
                        elif precio_pred < precio_actual * 0.9:
                            msg = "📉 Se espera una reducción en el precio. Condición favorable para el mercado."
                        else:
                            msg = "➡️ El precio se mantiene relativamente estable en los próximos 3 meses."

                        st.markdown(f"""
                        <div class="info-card">
                            <b>📋 Recomendación</b><br><br>
                            {msg}
                        </div>
                        <div class="info-card" style="margin-top:10px;">
                            <b>🤖 Variables más influyentes</b><br>
                            1. 🏞️ Embalses (lag 3m): {embalses_lag3:.0f}%<br>
                            2. 🌊 ONI: {oni:+.1f}<br>
                            3. 💧 Aportes: {aportes:.0f}%
                        </div>
                        """, unsafe_allow_html=True)

                    st.success(f"✅ Predicción completada para {fecha_resultado.strftime('%B %Y')}")

                except requests.exceptions.HTTPError as e:
                    st.error(f"❌ Error API DataRobot: {e.response.status_code} — {e.response.text[:200]}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")


# ══════════════════════════════════════════════════════════════════
# TAB 2 — ANÁLISIS DE ESCENARIOS
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📊 Simulador de Escenarios")
    st.markdown("Compara el impacto de diferentes condiciones climáticas sobre el precio")
    st.markdown("")

    # Escenarios predefinidos
    escenarios = {
        "🟢 Año Normal (La Niña moderada)": {
            "oni": -0.8, "aportes": 105.0, "embalses": 72.0,
            "desc": "Condiciones favorables: aportes sobre la media, embalses altos"
        },
        "🟡 El Niño Débil": {
            "oni": 0.6, "aportes": 85.0, "embalses": 60.0,
            "desc": "Ligera reducción en lluvias, embalses en descenso"
        },
        "🟠 El Niño Moderado": {
            "oni": 1.2, "aportes": 70.0, "embalses": 48.0,
            "desc": "Déficit hídrico, embalses bajo el umbral crítico"
        },
        "🔴 El Niño Fuerte (2015-16)": {
            "oni": 2.5, "aportes": 52.0, "embalses": 32.0,
            "desc": "Crisis hidrológica severa como la vivida en 2015-2016"
        },
    }

    st.markdown("#### Escenarios predefinidos")
    cols_esc = st.columns(4)
    for i, (nombre, esc) in enumerate(escenarios.items()):
        with cols_esc[i]:
            st.markdown(f"""
            <div class="info-card" style="text-align:center; min-height:160px;">
                <b>{nombre}</b><br><br>
                🌊 ONI: <b>{esc['oni']:+.1f}</b><br>
                💧 Aportes: <b>{esc['aportes']:.0f}%</b><br>
                🏞️ Embalses: <b>{esc['embalses']:.0f}%</b><br><br>
                <small>{esc['desc']}</small>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🎛️ Analiza el impacto del ONI en el precio")

    col_s1, col_s2 = st.columns([1, 1])
    with col_s1:
        aportes_base = st.slider("Aportes base %", 40.0, 150.0, 90.0, 5.0)
        embalses_base = st.slider("Embalses base %", 20.0, 90.0, 60.0, 5.0)
        precio_base_s = st.number_input("Precio base COP/kWh", value=175.0, step=10.0)

    with col_s2:
        # Gráfico de sensibilidad estimada (sin llamar a la API)
        oni_range = np.arange(-2.0, 2.6, 0.2)

        # Estimación simple basada en la física del modelo
        impacto_oni     = oni_range * 80
        impacto_embalse = max(0, 60 - embalses_base) * 5
        precios_est     = precio_base_s + impacto_oni + impacto_embalse

        df_sens = pd.DataFrame({
            "ONI": oni_range,
            "Precio Estimado (COP/kWh)": np.clip(precios_est, 50, 1600)
        })

        st.markdown("**Sensibilidad del precio al ONI (estimación)**")
        st.line_chart(df_sens.set_index("ONI"), height=250, use_container_width=True)
        st.caption("⚠️ Estimación basada en la física del modelo. Para predicciones exactas usa la pestaña de Predicción Manual.")

    # Tabla resumen de escenarios
    st.markdown("---")
    st.markdown("#### 📋 Tabla de Escenarios")
    data_tabla = []
    for nombre, esc in escenarios.items():
        imp_oni     = esc["oni"] * 80
        imp_embalse = max(0, 60 - esc["embalses"]) * 5
        precio_est  = max(50, 175 + imp_oni + imp_embalse)
        nivel_txt, _, nivel_color = nivel_riesgo_precio(precio_est)
        data_tabla.append({
            "Escenario": nombre,
            "ONI": f"{esc['oni']:+.1f}",
            "Aportes %": f"{esc['aportes']:.0f}%",
            "Embalses %": f"{esc['embalses']:.0f}%",
            "Precio Est. (COP/kWh)": f"{precio_est:,.0f}",
            "Riesgo": nivel_txt
        })
    st.dataframe(pd.DataFrame(data_tabla), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════
# TAB 3 — PREDICCIÓN POR LOTE
# ══════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📁 Predicción por Lote")
    st.markdown("Sube un archivo CSV con múltiples filas para obtener predicciones masivas")
    st.markdown("")

    # Plantilla descargable
    st.markdown("#### 1️⃣ Descarga la plantilla")
    plantilla = pd.DataFrame([{
        "Fecha": "2025-06-01",
        "ONI": 0.1, "ONI_lag_1": 0.0, "ONI_lag_3": -0.1, "ONI_lag_6": -0.3,
        "ONI_delta_3m": 0.2, "Fase_ENSO": "Neutro", "Es_Nino": 0, "Es_Nina": 0,
        "Aportes_Porcentaje": 95.0, "Aportes_lag_1": 92.0, "Aportes_lag_3": 88.0,
        "Aportes_MA_3": 91.7, "Aportes_MA_6": 90.0, "Deficit_Aportes": 0.0,
        "Embalses_Porcentaje": 65.0, "Embalses_lag_1": 67.0, "Embalses_lag_3": 70.0,
        "Embalses_MA_3": 67.3, "Embalses_delta": -5.0,
        "Precio_Bolsa": 175.0, "Precio_lag_1": 170.0, "Precio_lag_3": 160.0,
        "Precio_MA_3": 168.3, "Stress_Hidrico": 1.0,
        "Mes": 6, "Año": 2025, "Trimestre": 2
    }])
    csv_plantilla = plantilla.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar plantilla CSV",
        data=csv_plantilla,
        file_name="plantilla_prediccion.csv",
        mime="text/csv"
    )

    st.markdown("---")
    st.markdown("#### 2️⃣ Sube tu archivo con datos")
    archivo = st.file_uploader("Selecciona el CSV", type=["csv"])

    if archivo:
        df_upload = pd.read_csv(archivo)
        st.markdown(f"✅ **{len(df_upload)} filas** cargadas")
        st.dataframe(df_upload.head(5), use_container_width=True, hide_index=True)

        st.markdown("#### 3️⃣ Obtener predicciones")
        if st.button("⚡ PREDECIR LOTE COMPLETO", key="btn_lote"):
            if not DATAROBOT_API_KEY or not DATAROBOT_DEPLOYMENT_ID:
                st.error("⚠️ Configura API Key y Deployment ID en el panel lateral.")
            else:
                with st.spinner(f"🔄 Procesando {len(df_upload)} predicciones..."):
                    try:
                        url = f"{DATAROBOT_HOST}/predApi/v1.0/deployments/{DATAROBOT_DEPLOYMENT_ID}/predictions"
                        csv_bytes = df_upload.to_csv(index=False).encode("utf-8")
                        headers = {
                            "Authorization": f"Token {DATAROBOT_API_KEY}",
                            "Content-Type": "text/plain; charset=UTF-8",
                        }
                        response = requests.post(url, data=csv_bytes, headers=headers, timeout=120)
                        response.raise_for_status()
                        result = response.json()

                        predicciones = [r["prediction"] for r in result["data"]]
                        df_resultado = df_upload.copy()
                        df_resultado["Precio_3m_Predicho"] = [round(p, 2) for p in predicciones]
                        df_resultado["Nivel_Riesgo"] = df_resultado["Precio_3m_Predicho"].apply(
                            lambda p: nivel_riesgo_precio(p)[0]
                        )

                        st.success(f"✅ {len(predicciones)} predicciones completadas")
                        st.dataframe(df_resultado[["Fecha","Precio_3m_Predicho","Nivel_Riesgo"]].head(20),
                                     use_container_width=True, hide_index=True)

                        # Gráfico
                        if "Fecha" in df_resultado.columns:
                            st.line_chart(
                                df_resultado.set_index("Fecha")["Precio_3m_Predicho"],
                                height=250, use_container_width=True
                            )

                        # Descarga
                        csv_out = df_resultado.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "⬇️ Descargar resultados CSV",
                            data=csv_out,
                            file_name="predicciones_resultado.csv",
                            mime="text/csv"
                        )
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

# ─────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#4a7a9b; padding:15px 0;">
    ⚡ Predictor Precio Energía Colombia &nbsp;|&nbsp;
    Modelo IA entrenado con datos XM 2010-2025 + NOAA &nbsp;|&nbsp;
    Desarrollado con DataRobot Workbench
</div>
""", unsafe_allow_html=True)
