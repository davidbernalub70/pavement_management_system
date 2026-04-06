import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Gestión de Pavimentos", layout="wide")

# ==========================================
# 1. PANEL LATERAL: CONFIGURACIÓN DINÁMICA
# ==========================================
st.sidebar.title("⚙️ Panel de Configuración")

st.sidebar.header("1. Catálogo de Precios Unitarios")
tabla_base_precios = pd.DataFrame({
    "Tratamiento Base": ["Sello de Fisuras", "Parcheo", "Slurry", "Microfresado", "Fresado", "Reposición", "Inyecciones"],
    "Precio ($/m2)": [8500, 25000, 20000, 50000, 40000, 150000, 80000]
})
precios_editables = st.sidebar.data_editor(tabla_base_precios, num_rows="dynamic", hide_index=True)
dict_precios = dict(zip(precios_editables["Tratamiento Base"], precios_editables["Precio ($/m2)"]))

st.sidebar.header("2. Constructor del Árbol")
st.sidebar.markdown("**A. Buen Estado:**")
esc_bueno_leve = st.sidebar.text_input("Ahu < 20 y Fisuras Leves", value="Sello de Fisuras")
esc_bueno_medio = st.sidebar.text_input("Ahu < 20 y Fisuras Medias", value="Slurry + Parcheo + Sello de Fisuras")
st.sidebar.markdown("**B. Regular:**")
esc_reg_leve = st.sidebar.text_input("Regular - Fisuras Leves", value="Microfresado + Sello de Fisuras")
esc_reg_medio = st.sidebar.text_input("Regular - Fisuras Medias", value="Microfresado + Sello de Fisuras + Parcheo + Slurry")
st.sidebar.markdown("**C. Crítico:**")
esc_critico = st.sidebar.text_input("Falla Estructural", value="Fresado + Reposición")

ancho_por_defecto = st.sidebar.number_input("Ancho de Vía por defecto (m)", value=7.3)

def definir_tratamiento_dinamico(fila):
    iri, ahu, fis = fila['IRI'], fila['AHUELLAMIENTO'], fila['FISURAS']
    if iri < 3.0:
        if ahu < 20: return esc_bueno_leve if fis < 5 else esc_bueno_medio
        else: return esc_critico
    elif iri <= 5.5:
        if ahu < 20: return esc_reg_leve if fis < 5 else esc_reg_medio
        else: return esc_critico
    else: return esc_critico

# ==========================================
# INTERFAZ PRINCIPAL
# ==========================================
st.title("🛣️ Simulador de Gestión de Pavimentos")

archivo_subido = st.file_uploader("Sube tu inventario (Excel/CSV):", type=["xlsx", "csv"])

if archivo_subido is not None:
    if archivo_subido.name.endswith('.csv'): df = pd.read_csv(archivo_subido)
    else: df = pd.read_excel(archivo_subido)
        
    df['Intervención Sugerida'] = df.apply(definir_tratamiento_dinamico, axis=1)
    df['Longitud (m)'] = df['abscisa fin'] - df['abscisa inicio']
    df['Ancho (m)'] = df['ANCHO'] if 'ANCHO' in df.columns else ancho_por_defecto
    df['Área (m2)'] = df['Longitud (m)'] * df['Ancho (m)']
    
    desglose_individual = []
    def calcular_costo_compuesto(fila):
        area = fila['Área (m2)']
        componentes = [t.strip() for t in str(fila['Intervención Sugerida']).split('+')]
        costo_total = 0
        for comp in componentes:
            precio = dict_precios.get(comp, 0)
            costo_parcial = area * precio
            costo_total += costo_parcial
            desglose_individual.append({'TRAMO': fila['TRAMO'], 'Componente': comp, 'Costo ($)': costo_parcial})
        return costo_total

    df['Costo Tramo ($)'] = df.apply(calcular_costo_compuesto, axis=1)
    
    tab1, tab2 = st.tabs(["📊 Diagnóstico y Mapa (Hoy)", "⏳ Máquina del Tiempo (Simulación)"])
    
    # ==========================================
    # PESTAÑA 1: DIAGNÓSTICO Y MAPA
    # ==========================================
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Presupuesto", f"${df['Costo Tramo ($)'].sum():,.0f}")
        col2.metric("📏 Longitud", f"{df['Longitud (m)'].sum():,.0f} m")
        col3.metric("⬛ Área Total", f"{df['Área (m2)'].sum():,.0f} m²")
        col4.metric("⚠️ Tramos Críticos", len(df[df['Intervención Sugerida'] == esc_critico]))
        
        st.write("---")
        st.write("### 🗺️ Mapa Analítico de Tramos")
        
        capa_seleccionada = st.radio(
            "Selecciona la capa que deseas visualizar en las líneas del mapa:",
            ["Intervención Sugerida", "IRI", "Ahuellamiento", "Fisuras"],
            horizontal=True
        )

        if 'Latitud' in df.columns and 'Longitud' in df.columns:
            mapa = folium.Map(location=[df['Latitud'].mean(), df['Longitud'].mean()], zoom_start=14)
            
            for i in range(len(df) - 1):
                fila_actual = df.iloc[i]
                fila_siguiente = df.iloc[i+1]
                
                if fila_actual['TRAMO'] == fila_siguiente['TRAMO']:
                    color_linea = "gray"
                    if capa_seleccionada == "IRI":
                        val = fila_actual['IRI']
                        if val < 2.5: color_linea = "green"
                        elif val < 3.5: color_linea = "yellow"
                        elif val <= 5.5: color_linea = "orange"
                        else: color_linea = "red"
                    elif capa_seleccionada == "Ahuellamiento":
                        val = fila_actual['AHUELLAMIENTO']
                        if val < 10: color_linea = "green"
                        elif val < 20: color_linea = "orange"
                        else: color_linea = "red"
                    elif capa_seleccionada == "Fisuras":
                        val = fila_actual['FISURAS']
                        if val < 5: color_linea = "green"
                        elif val < 15: color_linea = "orange"
                        else: color_linea = "red"
                    elif capa_seleccionada == "Intervención Sugerida":
                        val = fila_actual['Intervención Sugerida']
                        if "Fresado" in val: color_linea = "red"
                        elif "Slurry" in val or "Microfresado" in val: color_linea = "orange"
                        else: color_linea = "green"

                    # ----------------------------------------------------
                    # CORRECCIÓN: Traductor de nombres para las columnas
                    columna_real = capa_seleccionada
                    if capa_seleccionada == "Ahuellamiento":
                        columna_real = "AHUELLAMIENTO"
                    elif capa_seleccionada == "Fisuras":
                        columna_real = "FISURAS"
                    
                    texto_popup = f"<b>{capa_seleccionada}:</b> {fila_actual[columna_real]}<br><b>Abs:</b> {fila_actual['abscisa inicio']}-{fila_actual['abscisa fin']}"
                    # ----------------------------------------------------
                    
                    folium.PolyLine(
                        locations=[(fila_actual['Latitud'], fila_actual['Longitud']), (fila_siguiente['Latitud'], fila_siguiente['Longitud'])],
                        color=color_linea,
                        weight=6,
                        opacity=0.8,
                        popup=folium.Popup(texto_popup, max_width=200)
                    ).add_to(mapa)

            st_folium(mapa, width=1000, height=500)
        else:
            st.warning("Faltan coordenadas para el mapa.")
            
        st.write("### 📋 Desglose General:")
        st.dataframe(df[['TRAMO', 'abscisa inicio', 'abscisa fin', 'IRI', 'AHUELLAMIENTO', 'FISURAS', 'Intervención Sugerida', 'Costo Tramo ($)']])

    # ==========================================
    # PESTAÑA 2: EL MÓDULO 5 CON SLIDER DE TIEMPO
    # ==========================================
    with tab2:
        st.header("⏳ Simulación de Deterioro Natural")
        st.write("Selecciona cuántos años hacia el futuro quieres proyectar el daño del pavimento.")
        
        # --- AQUÍ ESTÁ EL NUEVO SLIDER ---
        años_proyeccion = st.slider(
            "Cantidad de años a simular:", 
            min_value=1, 
            max_value=30, 
            value=10, 
            step=1
        )
        st.write("---")
        
        df['Identificador'] = df['TRAMO'] + " (Abs: " + df['abscisa inicio'].astype(str) + "-" + df['abscisa fin'].astype(str) + ")"
        tramo_elegido = st.selectbox("Selecciona un segmento para proyectar:", df['Identificador'])
        
        if tramo_elegido:
            datos_tramo = df[df['Identificador'] == tramo_elegido].iloc[0]
            
            iri_actual = datos_tramo['IRI']
            ahu_actual = datos_tramo['AHUELLAMIENTO']
            fis_actual = datos_tramo['FISURAS']
            
            historia = []
            
            # EL BUCLE AHORA DEPENDE DEL SLIDER (años_proyeccion)
            for año in range(0, años_proyeccion + 1):
                historia.append({
                    "Año": f"Año {año}",
                    "IRI": round(iri_actual, 2),
                    "Ahuellamiento": round(ahu_actual, 2),
                    "Fisuras": round(fis_actual, 2)
                })
                
                iri_actual += 0.12  
                ahu_actual += 0.7   
                fis_actual += (fis_actual * 0.15) + 1 
                
                if fis_actual > 100: fis_actual = 100

            df_proyeccion = pd.DataFrame(historia)
            
            st.write(f"### Proyección a {años_proyeccion} años para {tramo_elegido}")
            
            col_graf1, col_graf2 = st.columns(2)
            with col_graf1:
                st.write("**Evolución del IRI y Ahuellamiento**")
                st.line_chart(df_proyeccion.set_index("Año")[["IRI", "Ahuellamiento"]])
            with col_graf2:
                st.write("**Evolución de Fisuras (%)**")
                st.line_chart(df_proyeccion.set_index("Año")[["Fisuras"]], color="#ff0000")
                
            st.write("**Tabla de Envejecimiento:**")
            st.dataframe(df_proyeccion.T) 

else:
    st.info("Sube tu archivo para iniciar...")