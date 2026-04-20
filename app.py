import streamlit as st
from google import genai
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl
import io

# ==========================================
# CUADRILLA 1: CONFIGURACIÓN Y UI FUTURISTA
# ==========================================
def configurar_interfaz():
    st.set_page_config(page_title="PMS V0", page_icon="🛣️", layout="wide")
    
    # 1. Inyección de CSS Futurista (Efecto Neon y textos brillantes)
    st.markdown("""
    <style>
    /* Estilo para los botones principales (Borde brillante) */
    div.stButton > button:first-child {
        background-color: transparent;
        color: #00f2fe;
        border: 2px solid #00f2fe;
        box-shadow: 0 0 10px #00f2fe;
        transition: all 0.3s ease-in-out;
    }
    /* Efecto al pasar el mouse (Hover) */
    div.stButton > button:first-child:hover {
        background-color: #00f2fe;
        color: #0f172a;
        box-shadow: 0 0 20px #00f2fe, inset 0 0 10px #ffffff;
    }
    /* Estilo futurista para las métricas (números grandes) */
    div[data-testid="stMetricValue"] {
        color: #00ffcc;
        text-shadow: 0 0 8px #00ffcc;
        font-family: 'Courier New', Courier, monospace;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🛣️ Sistema de Gestión de Pavimentos (PMS)")
    st.markdown("### 💻 Consultoría de Interventoría | Panel de Análisis Avanzado")
    
    # 2. Construyendo la nueva Barra Lateral (Centro de Mando)
    st.sidebar.markdown("## 🛰️ CENTRO DE MANDO")
    st.sidebar.write("---")
    
    # Estos espacios los conectaremos a los datos reales en el siguiente paso
    st.sidebar.markdown("### 📊 Estado Global de la Red")
    if 'listo' not in st.session_state:
        st.sidebar.info("Esperando telemetría... Sube un archivo para inicializar los sensores.")
    else:
        # Mostramos KPIs provisionales (luego les pondremos la matemática real)
        st.sidebar.metric(label="Tramos Analizados", value="100 %", delta="Operativo")
        st.sidebar.metric(label="Salud Estructural", value="Crítica", delta="-15% vs año ant.", delta_color="inverse")
        
    st.sidebar.write("---")
    st.sidebar.write("📥 **Módulo de Ingreso de Datos:**")
    
    buffer = io.BytesIO()
    df_plantilla = pd.DataFrame(columns=[
        "Tramo", "Latitud", "Longitud", "abscisa inicio", "abscisa fin", 
        "IRI", "AHUELLAMIENTO", "FISURAS", "DEFLEXION", "FRICCION", "TEXTURA"
    ])
    df_plantilla.to_excel(buffer, index=False)
    
    st.sidebar.download_button(
        label="⬇️ Descargar Plantilla Base",
        data=buffer.getvalue(),
        file_name="Plantilla_PMS_Base.xlsx",
        mime="application/vnd.ms-excel"
    )
    
# ==========================================
# CUADRILLA 2: PROCESAMIENTO ESPACIAL Y MAPEO DE COLUMNAS
# ==========================================
import tempfile
import os
import geopandas as gpd

def procesar_archivo_espacial(archivo):
    gdf = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=archivo.name) as tmp:
            tmp.write(archivo.getvalue())
            tmp_path = tmp.name

        if archivo.name.endswith('.zip'):
            gdf = gpd.read_file(f"zip://{tmp_path}")
        elif archivo.name.endswith(('.kml', '.kmz')):
            gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
            gdf = gpd.read_file(tmp_path, driver='KML')

        os.remove(tmp_path)
        
        # --- SOLUCIÓN DEFINITIVA DE GEOMETRÍA ---
        # 1. Identificamos el nombre real de la columna espacial (geometry, Shape, geom, etc.)
        geom_col = gdf.active_geometry_name
        
        # 2. Pasamos a mayúsculas todas las columnas, EXCEPTO la espacial
        gdf.columns = [c if c == geom_col else str(c).upper().strip() for c in gdf.columns]
        
        # 3. Le reconfirmamos a GeoPandas cuál es su columna de dibujo (vital para Folium)
        gdf = gdf.set_geometry(geom_col)
        # ----------------------------------------
        
        return gdf

    except Exception as e:
        st.error(f"Error procesando el archivo espacial: {e}")
        return None
    
def mapear_columnas(gdf):
    st.write("### 🔀 Emparejamiento de Columnas")
    st.write("Por favor, selecciona qué columna de tu archivo corresponde a cada parámetro:")
    
    # Lista de columnas disponibles en el shapefile/KML
    columnas_disp = ["No Aplica"] + list(gdf.columns)
    
    # Usamos 4 columnas para organizar mejor los campos adicionales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        col_tramo = st.selectbox("ID / Nombre Tramo:", columnas_disp)
        col_abs_ini = st.selectbox("Abscisa Inicial:", columnas_disp)
        col_abs_fin = st.selectbox("Abscisa Final:", columnas_disp)
    with col2:
        col_iri = st.selectbox("IRI (Regularidad):", columnas_disp)
        col_ahu = st.selectbox("Ahuellamiento:", columnas_disp)
    with col3:
        col_fis = st.selectbox("Fisuras (%):", columnas_disp)
        col_def = st.selectbox("Deflexión (Estructural):", columnas_disp)
    with col4:
        col_fric = st.selectbox("Fricción:", columnas_disp)
        col_text = st.selectbox("Textura:", columnas_disp)
        col_res = st.selectbox("Vida Residual:", columnas_disp)
        
    # Guardamos la configuración en nuestro diccionario maestro
    mapa_cols = {
        'TRAMO': col_tramo, 'ABS_INI': col_abs_ini, 'ABS_FIN': col_abs_fin,
        'IRI': col_iri, 'AHUELLAMIENTO': col_ahu, 'FISURAS': col_fis,
        'DEFLEXION': col_def, 'FRICCION': col_fric, 'TEXTURA': col_text,
        'RESIDUAL': col_res
    }
    return mapa_cols

# ==========================================
# ==========================================
# CUADRILLA 3: MAPA ANALÍTICO INTERACTIVO (VERSIÓN CAMPO Y DINÁMICA)
# ==========================================
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl

def generar_mapa(gdf, mapa_cols):
    st.subheader("🗺️ Mapa Temático de Condición")
    
    # 1. Diccionario MAESTRO de parámetros visualizables
    # Aquí agregamos TODOS los posibles parámetros de la obra
    opciones_param = {
        "IRI (Regularidad)": mapa_cols.get('IRI'),
        "Ahuellamiento": mapa_cols.get('AHUELLAMIENTO'),
        "Fisuras": mapa_cols.get('FISURAS'),
        "Deflexión": mapa_cols.get('DEFLEXION'),
        "Fricción": mapa_cols.get('FRICCION'),
        "Textura": mapa_cols.get('TEXTURA'),
        "Vida Residual": mapa_cols.get('RESIDUAL')
    }
    
    # FILTRO INTELIGENTE: Nos quedamos SOLO con los que NO digan "No Aplica"
    # Si un proyecto no tiene Textura, simplemente desaparece de esta lista.
    opciones_validas = {k: v for k, v in opciones_param.items() if v and v != "No Aplica"}
    
    if not opciones_validas:
        st.warning("⚠️ Debes asignar al menos un parámetro de condición en el paso anterior para ver el mapa.")
        return

    # 2. Controles de Visualización en la parte superior
    c_param, c_mapa = st.columns([2, 1])
    with c_param:
        param_visual = st.selectbox("🔍 ¿Qué parámetro deseas proyectar en el mapa?", list(opciones_validas.keys()))
    with c_mapa:
        tipo_mapa = st.selectbox("🌍 Tipo de Mapa Base", ["Satélite (Esri)", "Claro (CartoDB)", "Oscuro (CartoDB)", "Calles (OSM)"])
    
    col_activa = opciones_validas[param_visual]
    
    # 3. Controles del Semáforo
    st.write(f"⚙️ **Configura los límites del semáforo para {param_visual}** (Mayor valor = Peor condición):")
    st.info("💡 Tip: Ajusta estos valores según el parámetro. Ej: Para IRI usa 2.5 y 3.5, pero para Fisuras usa 10 y 20.")
    c1, c2, c3 = st.columns(3)
    with c1: lim1 = st.number_input("🟢 a 🟡 (Bueno a Regular)", value=2.5, step=0.5)
    with c2: lim2 = st.number_input("🟡 a 🟠 (Regular a Malo)", value=3.5, step=0.5)
    with c3: lim3 = st.number_input("🟠 a 🔴 (Malo a Crítico)", value=5.0, step=0.5)

    # 4. Proyección a WGS84
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf_mapa = gdf.to_crs(epsg=4326)
    else:
        gdf_mapa = gdf.copy()

    # 5. Configuración del Mapa Base según selección
    bounds = gdf_mapa.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    # Diccionario con los tiles disponibles
    tiles_dict = {
        "Claro (CartoDB)": "cartodb positron",
        "Oscuro (CartoDB)": "cartodb dark_matter",
        "Calles (OSM)": "OpenStreetMap",
        "Satélite (Esri)": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    }
    
    tile_seleccionado = tiles_dict[tipo_mapa]
    if tipo_mapa == "Satélite (Esri)":
        m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles=tile_seleccionado, attr="Esri")
    else:
        m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles=tile_seleccionado)

    # BOTÓN DE GPS PARA CAMPO
    LocateControl(
        strings={"title": "Mostrar mi ubicación actual", "popup": "Estás aquí"},
        drawCircle=True, 
        drawMarker=True, 
        keepCurrentZoomLevel=True 
    ).add_to(m)

    def asignar_color(valor):
        try:
            v = float(valor)
            if v <= lim1: return '#28a745'
            elif v <= lim2: return '#ffc107'
            elif v <= lim3: return '#fd7e14'
            else: return '#dc3545'
        except:
            return '#6c757d' # Gris si el valor es nulo o texto

    # 6. Agregamos las geometrías
    folium.GeoJson(
        gdf_mapa,
        style_function=lambda feature: {
            'color': asignar_color(feature['properties'].get(col_activa)),
            'weight': 6,
            'opacity': 0.8
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[mapa_cols.get('TRAMO', ''), col_activa],
            aliases=['ID Tramo:', f'{param_visual}:'],
            localize=True
        )
    ).add_to(m)

    st_folium(m, width="100%", height=600)
# ==========================================
# CUADRILLA 4: PROYECCIONES Y ALARMAS
# ==========================================
def proyectar_deterioro(df, mapa_cols):
    st.subheader("⏳ Proyecciones de Deterioro y Alarmas Críticas")
    
    with st.expander("🚨 Configurar Límites Críticos (Manual de Carreteras)", expanded=False):
        col_lim1, col_lim2 = st.columns(2)
        with col_lim1:
            lim_iri = st.number_input("Límite Crítico IRI", value=3.5, step=0.1)
            lim_ahu = st.number_input("Límite Crítico Ahuellamiento (mm)", value=15.0, step=1.0)
            lim_fis = st.number_input("Límite Crítico Fisuras (%)", value=20.0, step=1.0)
        with col_lim2:
            lim_def = st.number_input("Límite Crítico Deflexión (µm)", value=800.0, step=10.0)
            lim_fric = st.number_input("Mínimo Fricción", value=0.40, step=0.01)
            lim_text = st.number_input("Mínimo Textura", value=0.40, step=0.01)

    with st.expander("⚙️ Configurar Tasas de Deterioro Anual", expanded=False):
        col_rate1, col_rate2 = st.columns(2)
        with col_rate1:
            tasa_iri = st.number_input("Aumento IRI / año", value=0.12, step=0.01)
            tasa_ahu = st.number_input("Aumento Ahuellamiento / año", value=0.7, step=0.1)
            tasa_fis = st.number_input("Multiplicador Fisuras", value=0.15, step=0.01)
        with col_rate2:
            tasa_def = st.number_input("Aumento Deflexión / año", value=12.0, step=1.0)
            tasa_fric = st.number_input("Pérdida Fricción / año", value=-0.02, step=0.01)
            tasa_text = st.number_input("Pérdida Textura / año", value=-0.01, step=0.01)

    st.write("---")
    
    # Extraemos el nombre real de la columna "Tramo" usando nuestro mapa
    col_tramo = mapa_cols.get('TRAMO', 'TRAMO')
    
    if col_tramo == "No Aplica" or col_tramo not in df.columns:
        st.warning("⚠️ Debes asignar una columna de TRAMO en el emparejamiento para poder proyectar.")
        return

    lista_tramos = df[col_tramo].unique()
    tramo_sel = st.selectbox("Selecciona un tramo para evaluar su futuro:", lista_tramos)
    años = st.slider("Ventana de análisis (Años hacia el futuro)", 1, 20, 10)

    # Filtramos los datos del tramo seleccionado
    datos = df[df[col_tramo] == tramo_sel].iloc[0]

    # Extraemos los valores iniciales usando el mapeo (con validación por si dice 'No Aplica')
    def extraer_valor(clave_mapa, default):
        col = mapa_cols.get(clave_mapa)
        if col != "No Aplica" and col in datos:
            try: return float(datos[col])
            except: return default
        return default

    iri = extraer_valor('IRI', 2.0)
    ahu = extraer_valor('AHUELLAMIENTO', 5.0)
    fis = extraer_valor('FISURAS', 1.0)
    d0 = extraer_valor('DEFLEXION', 250.0)
    fric = extraer_valor('FRICCION', 0.60)
    text = extraer_valor('TEXTURA', 0.80)

    historia = []
    falla_iri, falla_ahu, falla_fis, falla_def, falla_fric, falla_text = None, None, None, None, None, None

    for año in range(años + 1):
        historia.append({
            "Año": año,
            "IRI": round(iri, 2), "Límite IRI": lim_iri,
            "Ahuellamiento": round(ahu, 1), "Límite Ahuellamiento": lim_ahu,
            "Fisuras": round(fis, 1), "Límite Fisuras": lim_fis,
            "Deflexión": round(d0, 0), "Límite Deflexión": lim_def,
            "Fricción": round(fric, 3), "Límite Fricción": lim_fric,
            "Textura": round(text, 3), "Límite Textura": lim_text
        })
        
        # Revisamos si superó el límite crítico en este año
        if iri >= lim_iri and falla_iri is None: falla_iri = año
        if ahu >= lim_ahu and falla_ahu is None: falla_ahu = año
        if fis >= lim_fis and falla_fis is None: falla_fis = año
        if d0 >= lim_def and falla_def is None: falla_def = año
        if fric <= lim_fric and falla_fric is None: falla_fric = año
        if text <= lim_text and falla_text is None: falla_text = año

        # Aplicamos el deterioro para el próximo año
        iri += tasa_iri
        ahu += tasa_ahu
        fis += (fis * tasa_fis) + 1
        d0  += tasa_def
        fric += tasa_fric
        text += tasa_text
        
        if fis > 100: fis = 100
        if fric < 0: fric = 0
        if text < 0: text = 0

    df_proj = pd.DataFrame(historia)

    st.write("### 🚨 Resumen de Intervenciones Predictivas")
    alarmas_activas = False
    col_a1, col_a2, col_a3 = st.columns(3)
    
    if falla_iri is not None: col_a1.error(f"⚠️ **IRI:** Alcanza estado crítico en el **Año {falla_iri}**"); alarmas_activas = True
    if falla_ahu is not None: col_a2.error(f"⚠️ **Ahuellamiento:** Falla en el **Año {falla_ahu}**"); alarmas_activas = True
    if falla_fis is not None: col_a3.error(f"⚠️ **Fisuras:** Falla en el **Año {falla_fis}**"); alarmas_activas = True
    if falla_def is not None: col_a1.error(f"⚠️ **Deflexión:** Falla estructural en el **Año {falla_def}**"); alarmas_activas = True
    if falla_fric is not None: col_a2.error(f"⚠️ **Fricción:** Inseguro en el **Año {falla_fric}**"); alarmas_activas = True
    if falla_text is not None: col_a3.error(f"⚠️ **Textura:** Inseguro en el **Año {falla_text}**"); alarmas_activas = True
        
    if not alarmas_activas:
        st.success("✅ El tramo seleccionado no requiere intervención durante el periodo analizado.")

    st.write("---")
    st.write("### Gráficas de Comportamiento vs. Límites Normativos")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.line_chart(df_proj, x="Año", y=["IRI", "Límite IRI"], color=["#1f77b4", "#ff0000"])
        st.line_chart(df_proj, x="Año", y=["Deflexión", "Límite Deflexión"], color=["#e377c2", "#ff0000"])
    with col2:
        st.line_chart(df_proj, x="Año", y=["Ahuellamiento", "Límite Ahuellamiento"], color=["#ff7f0e", "#ff0000"])
        st.line_chart(df_proj, x="Año", y=["Fricción", "Límite Fricción"], color=["#8c564b", "#ff0000"])
    with col3:
        st.line_chart(df_proj, x="Año", y=["Fisuras", "Límite Fisuras"], color=["#d62728", "#ff0000"])
        st.line_chart(df_proj, x="Año", y=["Textura", "Límite Textura"], color=["#7f7f7f", "#ff0000"])

# ==========================================
# INGENIERO RESIDENTE (EJECUCIÓN PRINCIPAL)
# ==========================================
# ==========================================
# CUADRILLA 5: CÁLCULO DE TRÁFICO (ESALs)
# ==========================================
def calcular_trafico():
    st.write("---")
    st.subheader("🚛 Análisis de Tráfico (AASHTO)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        tpda = st.number_input("TPDA (Vehículos/día)", value=1500, step=100)
        tasa_crecimiento = st.number_input("Tasa Crecimiento Anual (%)", value=2.5, step=0.1)
    with col2:
        porcentaje_pesados = st.number_input("% Vehículos Pesados", value=15.0, step=1.0)
        factor_camion = st.number_input("Factor de Daño (FCE) prom.", value=1.5, step=0.1)
    with col3:
        periodo_diseno = st.number_input("Periodo de Diseño (Años)", value=10, step=1)
        
    # Fórmulas de Ingeniería (AASHTO)
    r = tasa_crecimiento / 100
    if r == 0:
        factor_crecimiento = periodo_diseno
    else:
        # Factor de crecimiento acumulado = ((1 + r)^n - 1) / r
        factor_crecimiento = ((1 + r)**periodo_diseno - 1) / r
    
    # ESALs = TPDA * 365 * %Pesados * FCE * Factor Crecimiento (Asumimos carril de diseño 100%)
    esals_totales = tpda * 365 * (porcentaje_pesados / 100) * factor_camion * factor_crecimiento
    
    # Visualización del resultado
    st.info(f"🛣️ **ESALs Acumulados de Diseño:** {esals_totales:,.0f} ejes equivalentes")
    
    return esals_totales, periodo_diseno
# ==========================================
# CUADRILLA 6: ASESORÍA EXPERTA IA (GEMINI)
# ==========================================
# ==========================================
# CUADRILLA 6: ASESORÍA EXPERTA IA (GEMINI - ACTUALIZADO)
# ==========================================
def consultoria_ia(df):
    st.write("---")
    st.subheader("🧠 Asesoría Experta con Inteligencia Artificial")
    st.write("Deja que nuestro 'Ingeniero Senior IA' analice los datos y te dé un concepto técnico.")
    
    # Campo para que el usuario ponga su llave
    api_key = st.text_input("🔑 Ingresa tu API Key de Google Gemini:", type="password")
    
    if api_key:
        try:
            # NUEVO MOTOR: Usamos el nuevo cliente oficial de google.genai
            client = genai.Client(api_key=api_key)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                lista_tramos = df['TRAMO'].unique() if 'TRAMO' in df.columns else ["Tramo Único"]
                tramo_sel = st.selectbox("Selecciona el tramo a consultar:", lista_tramos)
                
                # Rescatamos los ESALs calculados en la otra pestaña
                esals = st.session_state.get('esals', 'No calculado aún')
                
                # Extraemos los datos exactos del tramo seleccionado
                datos = df[df['TRAMO'] == tramo_sel].iloc[0] if 'TRAMO' in df.columns else df.iloc[0]
                
                st.info(f"**Datos enviados a la IA:**\n\nIRI: {datos.get('IRI')} \nAhuellamiento: {datos.get('AHUELLAMIENTO')}mm \nFisuras: {datos.get('FISURAS')}% \nDeflexión: {datos.get('DEFLEXION')}µm \nTráfico: {esals}")
            
            with col2:
                if st.button("🔍 Generar Concepto Técnico", type="primary", use_container_width=True):
                    with st.spinner("El Ingeniero IA está revisando los planos y datos de campo..."):
                        
                        prompt_ingeniero = f"""
                        Actúa como un Ingeniero Civil Senior con más de 20 años de experiencia en diseño, mantenimiento y rehabilitación de pavimentos (Metodologías AASHTO y MEPDG).
                        Tu cliente te ha entregado los siguientes datos de campo de una vía:
                        
                        - IRI (Rugosidad): {datos.get('IRI', 'N/A')}
                        - Ahuellamiento: {datos.get('AHUELLAMIENTO', 'N/A')} mm
                        - Fisuras: {datos.get('FISURAS', 'N/A')} %
                        - Deflexión (Estructural): {datos.get('DEFLEXION', 'N/A')} micras
                        - Tráfico (ESALs de diseño): {esals}
                        
                        Por favor, redacta un concepto técnico profesional. Estructúralo en:
                        1. Diagnóstico del estado actual (funcional y estructural).
                        2. Posibles causas del deterioro basándote en los números.
                        3. Recomendaciones concretas de intervención (ej. sello de fisuras, fresado, sobrecarpeta, reconstrucción).
                        Sé directo, usa lenguaje de ingeniería civil y no des respuestas genéricas.
                        """
                        
                        # NUEVA FORMA DE LLAMAR AL MODELO
                        respuesta = client.models.generate_content(
                            model='gemini-2.5-flash-lite',
                            contents=prompt_ingeniero,
                        )
                        st.success("✅ Análisis Técnico Completado.")
                        st.markdown(respuesta.text)
        except Exception as e:
            st.error(f"Error al conectar con la IA. Verifica tu API Key. Detalle: {e}")
    else:
        st.warning("👈 Por favor, ingresa tu API Key para habilitar al Ingeniero IA.")
# ==========================================
# PUNTO DE ARRANQUE (MOTOR DEL SCRIPT)
# ==========================================
def main():
    configurar_interfaz()
    
    # El cargador de archivos ahora admite ZIP
    archivo = st.file_uploader("Sube tu archivo (Excel, ZIP o KMZ)", type=["xlsx", "xls", "kmz", "zip"])
    
    if archivo:
        # 1. Leemos el archivo solo una vez y lo guardamos en la memoria (session_state)
        if 'gdf_crudo' not in st.session_state or st.session_state.get('nombre_archivo') != archivo.name:
            with st.spinner("Procesando topografía y atributos..."):
                gdf = procesar_archivo_espacial(archivo)
                if gdf is not None:
                    st.session_state.gdf_crudo = gdf
                    st.session_state.nombre_archivo = archivo.name
                    # Borramos estados anteriores si se sube un archivo nuevo
                    if 'listo' in st.session_state: del st.session_state['listo']

        # 2. Si el archivo se leyó bien, mostramos los menús de emparejamiento
        if 'gdf_crudo' in st.session_state:
            gdf = st.session_state.gdf_crudo
            
            # Llamamos a nuestra nueva función de la Cuadrilla 2
            mapa_cols = mapear_columnas(gdf)
            
            st.write("---")
            if st.button("🚀 Confirmar Datos y Generar Dashboard", type="primary", use_container_width=True):
                # Guardamos el mapeo de columnas para usarlo en el mapa y gráficas
                st.session_state.mapa_cols = mapa_cols
                
                # Separamos el dataframe normal (sin geometría) para las otras pestañas
                if 'geometry' in gdf.columns:
                    st.session_state.df = pd.DataFrame(gdf.drop(columns='geometry'))
                else:
                    st.session_state.df = pd.DataFrame(gdf)
                    
                st.session_state.gdf = gdf
                st.session_state.listo = True

    # 3. Si ya confirmamos el mapeo, desplegamos las pestañas
    if st.session_state.get('listo', False):
        df = st.session_state.df
        gdf = st.session_state.gdf
        mapa_cols = st.session_state.mapa_cols # ¡Aquí están las columnas que el usuario eligió!
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🗺️ Mapa", 
            "🚛 Tráfico", 
            "📊 Inventario", 
            "⏳ Proyecciones",
            "🧠 Consultor IA"
        ])
        
        with tab1:
            generar_mapa(gdf, mapa_cols)
        with tab2:
            esals, n_diseno = calcular_trafico()
            st.session_state.esals = esals
            st.session_state.n_diseno = n_diseno
        with tab3:
            st.subheader("Datos de Inventario")
            st.dataframe(df, use_container_width=True)
        with tab4:
            proyectar_deterioro(df, mapa_cols)
        with tab5:
            consultoria_ia(df)

if __name__ == "__main__":
    main()
