import streamlit as st
import requests
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, date

# ─────────────────────────────────────────────────────────────────
# CREDENCIALES — nunca visibles en el frontend
# Se leen de st.secrets (Streamlit Cloud) o variables de entorno
# ─────────────────────────────────────────────────────────────────
def get_secret(key):
    """Lee credencial desde st.secrets o variable de entorno."""
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

DATAROBOT_API_KEY       = get_secret("DATAROBOT_API_KEY")
DATAROBOT_DEPLOYMENT_ID = get_secret("DATAROBOT_DEPLOYMENT_ID")
DATAROBOT_DATAROBOT_KEY = get_secret("DATAROBOT_DATAROBOT_KEY")  # requerido en SaaS
DATAROBOT_HOST          = get_secret("DATAROBOT_HOST") or "https://app.datarobot.com"

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
# CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #0d1b2a 50%, #0a1628 100%);
        color: #e0e6f0;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1b2a 0%, #0a1628 100%);
        border-right: 1px solid #1e3a5f;
    }
    h1, h2, h3 { color: #00d4ff !important; }
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
    .stSlider > div > div > div > div { background: #00d4ff !important; }
    .stButton > button {
        background: linear-gradient(135deg, #0066cc 0%, #0099ff 100%);
        color: white; border: none; border-radius: 10px;
        padding: 14px 32px; font-size: 18px; font-weight: 700;
        width: 100%; box-shadow: 0 0 25px rgba(0,153,255,0.5);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #0099ff 0%, #00ccff 100%);
        box-shadow: 0 0 40px rgba(0,204,255,0.7);
        transform: translateY(-2px);
    }
    .resultado-box {
        background: linear-gradient(135deg, #003366 0%, #004080 100%);
        border: 2px solid #00d4ff; border-radius: 16px;
        padding: 30px; text-align: center;
        box-shadow: 0 0 40px rgba(0,212,255,0.3); margin: 20px 0;
    }
    .resultado-precio {
        font-size: 4rem; font-weight: 900; color: #00ff88;
        text-shadow: 0 0 20px rgba(0,255,136,0.5);
    }
    .resultado-label { font-size: 1.2rem; color: #7ab8d9; margin-bottom: 10px; }
    .info-card {
        background: rgba(0,60,100,0.3); border: 1px solid #1e4a7a;
        border-radius: 10px; padding: 15px; margin: 8px 0;
    }
    hr { border-color: #1e3a5f !important; }
    .stTabs [data-baseweb="tab"] {
        background: transparent; color: #7ab8d9;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #00d4ff !important;
        border-bottom: 2px solid #00d4ff !important;
    }
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

def construir_fila(fecha, oni, aportes, embalses, precio_actual,
                   oni_lag1, oni_lag3, oni_lag6,
                   aportes_lag1, aportes_lag3,
                   embalses_lag1, embalses_lag3):
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
    mes       = fecha.month
    año       = fecha.year
    trimestre = (mes - 1) // 3 + 1
    return {
        "Fecha": fecha.strftime("%Y-%m-%d"),
        "Mes": mes, "Año": año, "Trimestre": trimestre,
        "ONI": oni, "ONI_lag_1": oni_lag1, "ONI_lag_3": oni_lag3, "ONI_lag_6": oni_lag6,
        "ONI_delta_3m": round(oni - oni_lag3, 2),
        "Fase_ENSO": fase(oni), "Es_Nino": int(oni >= 0.5), "Es_Nina": int(oni <= -0.5),
        "Aportes_Porcentaje": aportes, "Aportes_lag_1": aportes_lag1, "Aportes_lag_3": aportes_lag3,
        "Aportes_MA_3": round((aportes + aportes_lag1 + aportes_lag3) / 3, 1),
        "Aportes_MA_6": round((aportes + aportes_lag1 + aportes_lag3) / 3, 1),
        "Deficit_Aportes": round(max(0, 80 - aportes), 1),
        "Embalses_Porcentaje": embalses, "Embalses_lag_1": embalses_lag1, "Embalses_lag_3": embalses_lag3,
        "Embalses_MA_3": round((embalses + embalses_lag1 + embalses_lag3) / 3, 1),
        "Embalses_delta": round(embalses - embalses_lag3, 1),
        "Precio_Bolsa": precio_actual, "Precio_lag_1": precio_actual,
        "Precio_lag_3": precio_actual, "Precio_MA_3": precio_actual,
        "Stress_Hidrico": round(oni * 10 + max(0, 65 - embalses), 2),
    }


def llamar_api_datarobot(df_datos):
    """
    Llama a la API de predicciones de DataRobot.
    Headers requeridos según documentación oficial:
      - Authorization: Bearer <API_KEY>
      - datarobot-key: <DATAROBOT_KEY>  ← obligatorio en SaaS
      - Content-Type: text/plain; charset=UTF-8
    """
    url = (
        f"{DATAROBOT_HOST}/predApi/v1.0/deployments"
        f"/{DATAROBOT_DEPLOYMENT_ID}/predictions"
    )
    headers = {
        "Authorization": f"Bearer {DATAROBOT_API_KEY}",
        "Content-Type": "text/plain; charset=UTF-8",
    }
    # datarobot-key es obligatorio en SaaS — si está disponible lo incluye
    if DATAROBOT_DATAROBOT_KEY:
        headers["datarobot-key"] = DATAROBOT_DATAROBOT_KEY

    csv_bytes = df_datos.to_csv(index=False).encode("utf-8")
    response  = requests.post(url, data=csv_bytes, headers=headers, timeout=60)

    if response.status_code == 403:
        raise ValueError(
            "403 Forbidden — Verifica que:\n"
            "1. DATAROBOT_API_KEY es correcta\n"
            "2. DATAROBOT_DATAROBOT_KEY está configurada (obligatoria en SaaS)\n"
            "3. DATAROBOT_DEPLOYMENT_ID es el correcto\n"
            "Encuéntralas en DataRobot → Consola → Despliegues → Predicciones → API"
        )
    response.raise_for_status()
    return response.json()


def credenciales_ok():
    return bool(DATAROBOT_API_KEY and DATAROBOT_DEPLOYMENT_ID)


# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding:20px 0 10px 0;">
    <div style="font-size:4rem;">⚡</div>
    <h1 style="font-size:2.5rem; margin:0; color:#00d4ff;">
        Predictor de Precio de Energía
    </h1>
    <p style="font-size:1.1rem; color:#7ab8d9; margin-top:8px;">
        Mercado Eléctrico Colombiano · Modelo IA · XM + NOAA
    </p>
    <p style="color:#4a7a9b; font-size:0.9rem;">
        Predice el precio de bolsa 3 meses adelante usando El Niño, embalses y aportes hídricos
    </p>
</div>
<hr/>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# SIDEBAR — solo información, sin credenciales
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📋 Panel de Control")
    st.markdown("---")

    # Indicador de estado de conexión (sin mostrar credenciales)
    if credenciales_ok():
        st.markdown("""
        <div style="background:#0a2e1a; border:1px solid #00cc44;
                    border-radius:8px; padding:12px; text-align:center;">
            <span style="color:#00cc44; font-size:1.1rem;">🟢 Modelo conectado</span><br>
            <small style="color:#4a9a6a;">API DataRobot activa</small>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:#2e0a0a; border:1px solid #cc3300;
                    border-radius:8px; padding:12px; text-align:center;">
            <span style="color:#ff4444; font-size:1.1rem;">🔴 Sin credenciales</span><br>
            <small style="color:#aa4444;">Configura el archivo .streamlit/secrets.toml</small>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("📖 Cómo configurar"):
            st.markdown("""
            Crea el archivo `.streamlit/secrets.toml`:
            ```toml
            DATAROBOT_API_KEY       = "tu_api_key"
            DATAROBOT_DEPLOYMENT_ID = "tu_deployment_id"
            DATAROBOT_DATAROBOT_KEY = "tu_datarobot_key"
            DATAROBOT_HOST          = "https://app.datarobot.com"
            ```
            Encuéntralos en:
            **DataRobot → Consola → Despliegues → tu despliegue → Predicciones → Código de ejemplo**
            """)

    st.markdown("---")
    st.markdown("### 📅 Fecha de predicción")
    fecha_pred = st.date_input(
        "Mes base",
        value=date.today().replace(day=1),
        help="El modelo predecirá el precio 3 meses después de esta fecha"
    )

    st.markdown("---")
    st.markdown("""
    <div class="info-card">
        <b>🧠 Cadena causal aprendida</b><br><br>
        🌊 <b>ONI</b> (El Niño)<br>
        &nbsp;&nbsp;&nbsp;↓<br>
        🌧️ <b>Menos lluvia</b><br>
        &nbsp;&nbsp;&nbsp;↓<br>
        💧 <b>Menos aportes</b><br>
        &nbsp;&nbsp;&nbsp;↓<br>
        🏞️ <b>Embalses bajos</b><br>
        &nbsp;&nbsp;&nbsp;↓<br>
        🔥 <b>Más generación térmica</b><br>
        &nbsp;&nbsp;&nbsp;↓<br>
        💰 <b>Precio sube</b>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; color:#4a7a9b; font-size:0.8rem;">
        Modelo entrenado con datos XM 2010–2025<br>
        + NOAA Oceanic Niño Index<br>
        Plataforma: DataRobot Workbench
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# TABS
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
    st.markdown("Ingresa los valores actuales del mes para predecir el precio en 3 meses")
    st.markdown("")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 🌊 Índice ONI")
        oni = st.slider("ONI actual", -3.0, 3.0, 0.1, 0.1,
                        help="≥+0.5 = El Niño | ≤-0.5 = La Niña | Entre = Neutro")
        fase_oni, _ = clasificar_oni(oni)
        st.markdown(f"**Fase ENSO:** {fase_oni}")
        oni_lag1 = st.number_input("ONI hace 1 mes",  value=0.1,  step=0.1, format="%.1f")
        oni_lag3 = st.number_input("ONI hace 3 meses", value=0.0, step=0.1, format="%.1f")
        oni_lag6 = st.number_input("ONI hace 6 meses", value=-0.1, step=0.1, format="%.1f")

    with col2:
        st.markdown("#### 💧 Aportes Hídricos")
        aportes = st.slider("Aportes % media histórica", 20.0, 200.0, 95.0, 1.0,
                            help="<70% = déficit | >100% = superávit")
        if aportes < 70:
            st.markdown("⚠️ **Déficit hídrico** — por debajo del umbral crítico")
        elif aportes > 120:
            st.markdown("✅ **Superávit** — condición favorable")
        else:
            st.markdown("✅ **Condición normal**")
        aportes_lag1 = st.number_input("Aportes % hace 1 mes",  value=92.0, step=1.0, format="%.1f")
        aportes_lag3 = st.number_input("Aportes % hace 3 meses", value=88.0, step=1.0, format="%.1f")

    with col3:
        st.markdown("#### 🏞️ Embalses")
        embalses = st.slider("Embalses % capacidad", 10.0, 100.0, 65.0, 1.0,
                             help="<40% = emergencia energética | >70% = adecuado")
        if embalses < 40:
            st.markdown("🚨 **Emergencia energética** — nivel crítico")
        elif embalses < 60:
            st.markdown("⚠️ **Nivel bajo** — monitoreo requerido")
        else:
            st.markdown("✅ **Nivel adecuado**")
        embalses_lag1 = st.number_input("Embalses % hace 1 mes",  value=67.0, step=1.0, format="%.1f")
        embalses_lag3 = st.number_input("Embalses % hace 3 meses", value=70.0, step=1.0, format="%.1f")

    st.markdown("---")
    col_p, _ = st.columns([1, 2])
    with col_p:
        precio_actual = st.number_input(
            "💰 Precio Bolsa actual (COP/kWh)",
            min_value=0.0, max_value=2000.0, value=175.0, step=10.0
        )

    st.markdown("")

    # Botón
    col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
    with col_b2:
        predecir = st.button("⚡ PREDECIR PRECIO EN 3 MESES", key="btn_pred")

    if predecir:
        if not credenciales_ok():
            st.error("⚠️ Configura las credenciales en `.streamlit/secrets.toml` — ver instrucciones en el panel lateral.")
        else:
            with st.spinner("🔄 Consultando el modelo de IA en DataRobot..."):
                try:
                    datos = construir_fila(
                        fecha_pred, oni, aportes, embalses, precio_actual,
                        oni_lag1, oni_lag3, oni_lag6,
                        aportes_lag1, aportes_lag3,
                        embalses_lag1, embalses_lag3
                    )
                    result       = llamar_api_datarobot(pd.DataFrame([datos]))
                    precio_pred  = round(result["data"][0]["prediction"], 2)
                    nivel_txt, _, nivel_color = nivel_riesgo_precio(precio_pred)

                    # Fecha resultado
                    mes_r = ((fecha_pred.month - 1 + 3) % 12) + 1
                    año_r = fecha_pred.year + (1 if mes_r < fecha_pred.month else 0)
                    fecha_r = date(año_r, mes_r, 1).strftime("%B %Y")

                    # Resultado principal
                    st.markdown(f"""
                    <div class="resultado-box">
                        <div class="resultado-label">⚡ Precio de Bolsa Predicho para {fecha_r}</div>
                        <div class="resultado-precio">{precio_pred:,.0f}</div>
                        <div style="color:#7ab8d9; font-size:1.3rem; margin-top:5px;">COP / kWh</div>
                        <div style="margin-top:15px; font-size:1.2rem;">
                            Nivel de Riesgo: <span style="color:{nivel_color}; font-weight:700;">{nivel_txt}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Métricas
                    cambio     = precio_pred - precio_actual
                    cambio_pct = (cambio / precio_actual * 100) if precio_actual > 0 else 0
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Precio Actual",  f"{precio_actual:,.0f} COP/kWh")
                    m2.metric("Precio Predicho", f"{precio_pred:,.0f} COP/kWh",
                              delta=f"{cambio:+,.0f} COP/kWh")
                    m3.metric("Variación %",    f"{cambio_pct:+.1f}%")
                    m4.metric("Nivel Riesgo",   nivel_txt.split(" ", 1)[-1])

                    # Interpretación
                    st.markdown("#### 💡 Interpretación")
                    ci1, ci2 = st.columns(2)
                    with ci1:
                        st.markdown(f"""
                        <div class="info-card">
                            <b>🌊 Condición climática</b><br>
                            {fase_oni}<br>
                            <small>ONI: {oni:+.1f} | Tendencia 3m: {oni-oni_lag3:+.1f}</small>
                        </div>
                        <div class="info-card" style="margin-top:10px;">
                            <b>💧 Situación hídrica</b><br>
                            Aportes: {aportes:.0f}% de la media<br>
                            Embalses: {embalses:.0f}% de capacidad
                        </div>
                        """, unsafe_allow_html=True)
                    with ci2:
                        if   cambio_pct >  30: msg = "⚠️ Incremento significativo esperado. Considera contratos de cobertura o ajuste de tarifas."
                        elif cambio_pct >  10: msg = "📈 Incremento moderado. Se recomienda monitoreo."
                        elif cambio_pct < -10: msg = "📉 Reducción esperada. Condición favorable para el mercado."
                        else:                  msg = "➡️ Precio relativamente estable en los próximos 3 meses."
                        st.markdown(f"""
                        <div class="info-card">
                            <b>📋 Recomendación</b><br><br>{msg}
                        </div>
                        <div class="info-card" style="margin-top:10px;">
                            <b>🤖 Variables clave del modelo</b><br>
                            1. 🏞️ Embalses lag 3m: {embalses_lag3:.0f}%<br>
                            2. 🌊 ONI actual: {oni:+.1f}<br>
                            3. 💧 Aportes: {aportes:.0f}%
                        </div>
                        """, unsafe_allow_html=True)

                    st.success(f"✅ Predicción completada para {fecha_r}")

                except ValueError as e:
                    st.error(f"❌ {e}")
                except requests.exceptions.HTTPError as e:
                    st.error(f"❌ Error HTTP {e.response.status_code}: {e.response.text[:300]}")
                except Exception as e:
                    st.error(f"❌ Error inesperado: {str(e)}")


# ══════════════════════════════════════════════════════════════════
# TAB 2 — ESCENARIOS
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📊 Simulador de Escenarios")
    st.markdown("Visualiza el impacto de distintas condiciones climáticas sobre el precio")
    st.markdown("")

    escenarios = {
        "🟢 Año Normal":            {"oni": -0.8, "aportes": 105.0, "embalses": 72.0},
        "🟡 El Niño Débil":         {"oni":  0.6, "aportes":  85.0, "embalses": 60.0},
        "🟠 El Niño Moderado":      {"oni":  1.2, "aportes":  70.0, "embalses": 48.0},
        "🔴 El Niño Fuerte 2015-16":{"oni":  2.5, "aportes":  52.0, "embalses": 32.0},
    }

    cols_e = st.columns(4)
    for i, (nombre, esc) in enumerate(escenarios.items()):
        with cols_e[i]:
            imp     = esc["oni"] * 80 + max(0, 60 - esc["embalses"]) * 5
            p_est   = max(50, 175 + imp)
            niv, _, color = nivel_riesgo_precio(p_est)
            st.markdown(f"""
            <div class="info-card" style="text-align:center; min-height:180px;">
                <b>{nombre}</b><br><br>
                🌊 ONI: <b>{esc['oni']:+.1f}</b><br>
                💧 Aportes: <b>{esc['aportes']:.0f}%</b><br>
                🏞️ Embalses: <b>{esc['embalses']:.0f}%</b><br><br>
                <span style="color:{color}; font-weight:700;">
                    Est. ~{p_est:,.0f} COP/kWh
                </span><br>
                <small>{niv}</small>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📈 Sensibilidad precio vs ONI")
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        emb_s  = st.slider("Embalses base %", 20.0, 90.0, 60.0, 5.0)
        apo_s  = st.slider("Aportes base %",  40.0, 150.0, 90.0, 5.0)
        pre_s  = st.number_input("Precio base COP/kWh", value=175.0, step=10.0)
    with col_s2:
        oni_r  = np.arange(-2.0, 2.6, 0.1)
        pre_r  = np.clip(pre_s + oni_r * 80 + max(0, 60 - emb_s) * 5, 50, 1600)
        df_s   = pd.DataFrame({"ONI": oni_r, "Precio Estimado (COP/kWh)": pre_r})
        st.line_chart(df_s.set_index("ONI"), height=260, use_container_width=True)
        st.caption("Estimación basada en la física del modelo — para predicciones exactas usa la pestaña Predicción Manual.")

    st.markdown("---")
    st.markdown("#### 📋 Tabla comparativa de escenarios")
    tabla = []
    for nombre, esc in escenarios.items():
        imp   = esc["oni"] * 80 + max(0, 60 - esc["embalses"]) * 5
        p_est = max(50, 175 + imp)
        niv, _, _ = nivel_riesgo_precio(p_est)
        tabla.append({
            "Escenario": nombre,
            "ONI": f"{esc['oni']:+.1f}",
            "Aportes %": f"{esc['aportes']:.0f}%",
            "Embalses %": f"{esc['embalses']:.0f}%",
            "Precio Est. (COP/kWh)": f"{p_est:,.0f}",
            "Riesgo": niv
        })
    st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════
# TAB 3 — LOTE
# ══════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📁 Predicción por Lote")
    st.markdown("Sube un CSV con múltiples meses para obtener todas las predicciones a la vez")
    st.markdown("")

    st.markdown("#### 1️⃣ Descarga la plantilla")
    plantilla = pd.DataFrame([{
        "Fecha":"2025-06-01","Mes":6,"Año":2025,"Trimestre":2,
        "ONI":0.1,"ONI_lag_1":0.0,"ONI_lag_3":-0.1,"ONI_lag_6":-0.3,
        "ONI_delta_3m":0.2,"Fase_ENSO":"Neutro","Es_Nino":0,"Es_Nina":0,
        "Aportes_Porcentaje":95.0,"Aportes_lag_1":92.0,"Aportes_lag_3":88.0,
        "Aportes_MA_3":91.7,"Aportes_MA_6":90.0,"Deficit_Aportes":0.0,
        "Embalses_Porcentaje":65.0,"Embalses_lag_1":67.0,"Embalses_lag_3":70.0,
        "Embalses_MA_3":67.3,"Embalses_delta":-5.0,
        "Precio_Bolsa":175.0,"Precio_lag_1":170.0,"Precio_lag_3":160.0,
        "Precio_MA_3":168.3,"Stress_Hidrico":1.0,
    }])
    st.download_button("⬇️ Descargar plantilla CSV",
                       data=plantilla.to_csv(index=False).encode("utf-8"),
                       file_name="plantilla_prediccion.csv", mime="text/csv")

    st.markdown("---")
    st.markdown("#### 2️⃣ Sube tu archivo")
    archivo = st.file_uploader("Selecciona el CSV", type=["csv"])

    if archivo:
        df_up = pd.read_csv(archivo)
        st.success(f"✅ {len(df_up)} filas cargadas")
        st.dataframe(df_up.head(5), use_container_width=True, hide_index=True)

        st.markdown("#### 3️⃣ Obtener predicciones")
        if st.button("⚡ PREDECIR LOTE COMPLETO", key="btn_lote"):
            if not credenciales_ok():
                st.error("⚠️ Configura las credenciales en `.streamlit/secrets.toml`.")
            else:
                with st.spinner(f"🔄 Procesando {len(df_up)} predicciones..."):
                    try:
                        result        = llamar_api_datarobot(df_up)
                        predicciones  = [r["prediction"] for r in result["data"]]
                        df_r          = df_up.copy()
                        df_r["Precio_3m_Predicho"] = [round(p, 2) for p in predicciones]
                        df_r["Nivel_Riesgo"] = df_r["Precio_3m_Predicho"].apply(
                            lambda p: nivel_riesgo_precio(p)[0])

                        st.success(f"✅ {len(predicciones)} predicciones completadas")
                        st.dataframe(
                            df_r[["Fecha","Precio_3m_Predicho","Nivel_Riesgo"]],
                            use_container_width=True, hide_index=True
                        )
                        if "Fecha" in df_r.columns:
                            st.line_chart(
                                df_r.set_index("Fecha")["Precio_3m_Predicho"],
                                height=250, use_container_width=True
                            )
                        st.download_button(
                            "⬇️ Descargar resultados CSV",
                            data=df_r.to_csv(index=False).encode("utf-8"),
                            file_name="predicciones_resultado.csv", mime="text/csv"
                        )
                    except ValueError as e:
                        st.error(f"❌ {e}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#4a7a9b; padding:15px 0; font-size:0.85rem;">
    ⚡ Predictor Precio Energía Colombia &nbsp;|&nbsp;
    Datos XM 2010–2025 + NOAA &nbsp;|&nbsp; DataRobot Workbench
</div>
""", unsafe_allow_html=True)
