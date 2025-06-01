import dash
from dash import Dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from statsmodels.tsa.arima.model import ARIMA
import plotly.graph_objs as go
import plotly.express as px
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
import pytz
import numpy as np # Import numpy for np.inf


# configuración inicial
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    print("Error: MONGO_URI no está configurado en el archivo .env")
    exit() # Salir de la aplicación si no hay URI de MongoDB

try:
    cliente = MongoClient(MONGO_URI)
    db = cliente["chatbot_db"]
    cliente.admin.command('ping')
    print("Conexión a MongoDB exitosa!")
except Exception as e:
    print(f"Error al conectar a MongoDB: {e}")
    exit() # Salir si la conexión falla


# app dash
app = Dash(__name__,
            external_stylesheets=[dbc.themes.DARKLY],
            meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}],
            suppress_callback_exceptions=True # Suppress callback exceptions for dynamic layouts
           )
server = app.server
app.title = "Análisis de Riesgo de Robo de Identidad"

load_figure_template('slate')

# Obtener lista de usuarios válidos para ARIMA (al menos 10 eventos)
coleccion = db["usuarios_combinados"]
usuarios_validos = []
for doc in coleccion.find():
    eventos = doc.get("eventos_acceso", [])
    if len(eventos) >= 10:
        usuarios_validos.append(doc["telegram_id"])


# --- Carga y preprocesamiento de datos para la pestaña de Análisis INEGI ---
# Asegúrate de que 'inegi.csv' esté en la misma carpeta que este script.
try:
    # Renombrar el archivo de 'inegi - Sheet1.csv' a 'inegi.csv' en tu directorio
    df_inegi = pd.read_csv("/Users/rogeliohidalgo/Documents/visual_code/pp/inegi - Sheet1.csv")

    # Renombrar columnas para redes sociales
    nombres_redes = {
        'P7_16_1': 'facebook',
        'P7_16_2': 'x', # Asumo que 'x' es Twitter
        'P7_16_3': 'instagram',
        'P7_16_4': 'linkedin',
        'P7_16_5': 'snapchat',
        'P7_16_6': 'whatsapp',
        'P7_16_7': 'youtube',
        'P7_16_8': 'pinterest',
        'P7_16_9': 'messenger',
        'P7_16_10': 'tiktok'
    }
    df_inegi.rename(columns=nombres_redes, inplace=True)
    redes_sociales_cols = list(nombres_redes.values())

    # Renombrar columnas para internet externo
    internet_externo_nombres = {
        'P7_8_4': 'sitio publico con costo',
        'P7_8_5': 'sitio publico sin costo',
        'P7_8_6': 'internet en lugares ajenos (familiares o amigos)'
    }
    df_inegi.rename(columns=internet_externo_nombres, inplace=True)
    internet_externo_cols = list(internet_externo_nombres.values())

    # Columna de compras online (P7_28) y su mapeo
    columna_compras = 'P7_28' # Asumo que esta es la columna de compras
    nombres_compras = {0: 'No contestó', 1: 'Sí', 2: 'No'} # Mapeo de valores para la columna de compras

    # Definir los grupos de horas de uso para 'P7_4'
    # Ajustado para incluir 0 y np.inf (valores muy grandes)
    bins_horas_internet = [0, 1, 3, 6, 9, 12, np.inf]
    labels_horas_internet = ['0-1 hora', '1-3 horas', '3-6 horas', '6-9 horas', '9-12 horas', 'Más de 12 horas']
    df_inegi['grupo_horas_internet'] = pd.cut(df_inegi['P7_4'], bins=bins_horas_internet, labels=labels_horas_internet, right=False, include_lowest=True)

    # Calcular el número total de redes sociales utilizadas por usuario
    df_inegi['num_redes_sociales'] = df_inegi[redes_sociales_cols].sum(axis=1)

    # Columna para uso de internet externo
    df_inegi['usa_internet_externo'] = df_inegi[internet_externo_cols].any(axis=1)

    print("Datos de INEGI cargados y preprocesados exitosamente.")

except FileNotFoundError:
    print("Error: El archivo 'inegi.csv' no se encontró. Asegúrate de que esté en la misma carpeta.")
    df_inegi = pd.DataFrame() # Crear un DataFrame vacío para evitar errores
except Exception as e:
    print(f"Error al cargar o preprocesar 'inegi.csv': {e}")
    df_inegi = pd.DataFrame()


# --- Contenido de la primera pestaña (tu dashboard actual) ---
dashboard_content = html.Div([
    html.Div([
        html.Label("Selecciona la fuente de datos:"),
        dcc.Dropdown(
            id="selector_base",
            options=[
                {"label": "Datos simulados", "value": "usuarios_combinados"},
                {"label": "Datos del chatbot", "value": "respuestas_mixtas"}
            ],
            value="respuestas_mixtas",
            style={
                'font-size': 15,
                'font-family': 'sans-serif',
                'display': 'flex',
                'gap': 12,
                'width': 300,
                'color': 'black',
            }
        ),
    ], style={'text-align': 'center', 'border-radius': 10, 'width': 400, 'color': 'white'}),

    dcc.Interval(id="interval", interval=5*1000, n_intervals=0),

    # Fila 1: Riesgo en Redes Sociales y Usuarios por Nivel de Riesgo Actual
    html.Div([
        html.Div([
            html.H3("📊 Riesgo en Redes Sociales "),
            dcc.Graph(id="grafica_virus")
        ], style={"width": "49%"}), # Ajustar ancho para dos columnas
        html.Div([
            html.H3("📊 Usuarios por Nivel de Riesgo Actual"),
            dcc.Graph(id="grafica_riesgo")
        ], style={"width": "49%"}) # Ajustar ancho para dos columnas
    ], style={"display": "flex", "justifyContent": "space-between", "margin-top": "20px"}),

    # Fila 2: Tendencia de Conexiones por Alcaldía y Dispositivos Más Frecuentes (ya en dos columnas)
    html.Div([
        html.Div([
            html.H3("📈 Tendencia de Conexiones por Alcaldía"),
            dcc.Graph(id="grafica_tendencia_alcaldia")
        ], style={"width": "48%"}),

        html.Div([
            html.H3("💻 Dispositivos Más Frecuentes"),
            dcc.Graph(id="grafica_dispositivo")
        ], style={"width": "48%"})
    ], style={"display": "flex", "justifyContent": "space-between", "margin-top": "20px"}),

    # Gráfica de Satisfacción (Mantiene 100% de ancho)
    html.Div([
        html.H3("📊 Distribución de Satisfacción de la Encuesta"),
        dcc.Graph(id="grafica_satisfaccion")
    ], style={"width": "100%", "margin-top": "20px"}),

    html.H2("📋 Tabla de Usuarios", style={'margin-top': '40px'}),
    dash_table.DataTable(
        id="tabla_usuarios",
        columns=[
            {"name": "telegram_id", "id": "telegram_id"},
            {"name": "nivel_riesgo", "id": "nivel_riesgo"},
            {"name": "riesgo_futuro", "id": "riesgo_futuro"},
            {"name": "alcaldia_habitual", "id": "alcaldia_habitual"},
            {"name": "dispositivo_frecuente", "id": "dispositivo_frecuente"},
        ],
        style_table={"overflowX": "auto", 'backgroundColor': '#303030'},
        style_cell={"textAlign": "left", 'backgroundColor': '#303030', 'color': 'white'},
        style_header={'backgroundColor': '#212121', 'color': 'white', 'fontWeight': 'bold'},
        page_size=10
    ),
])

# --- Contenido de la pestaña "Detalle de Usuario" ---
user_detail_content = html.Div([
    html.H2("Detalle Individual del Usuario", style={'font-weight':'bold','font-size':35, 'font-family':'sans-serif'}),
    html.P("Selecciona un usuario para analizar su riesgo futuro de anomalías de acceso y patrones de conexión.", style={'margin-top': '10px'}),

    html.Div([
        html.Label("Selecciona un usuario:", style={'color': 'white'}),
        dcc.Dropdown(
            id="usuario_detail_dropdown",
            options=[{"label": str(uid), "value": uid} for uid in usuarios_validos],
            placeholder="Selecciona un usuario para ver sus detalles",
            style={'width': '100%', 'color': 'black'}
        ),
    ], style={"margin": "20px 0px", "width": "50%"}),

    html.Div([
        html.Div([
            html.H3("📈 Serie de Anomalías y Predicción ARIMA", style={'margin-top': '20px'}),
            dcc.Graph(id="grafica_arima_usuario")
        ], style={"width": "100%", "marginBottom": "20px"}),

        html.Div([
            html.Div([
                html.H3("📍 Top 3 Lugares de Conexión Frecuentes", style={'margin-top': '20px'}),
                dash_table.DataTable(
                    id="tabla_lugares_conexion_frecuentes",
                    columns=[
                        {"name": "Lugar", "id": "location"},
                        {"name": "Conexiones", "id": "count"}
                    ],
                    style_table={"overflowX": "auto", 'backgroundColor': '#303030', 'maxHeight': '300px'},
                    style_cell={"textAlign": "left", 'backgroundColor': '#303030', 'color': 'white', 'padding': '10px'},
                    style_header={'backgroundColor': '#212121', 'color': 'white', 'fontWeight': 'bold'},
                    page_action='none',
                )
            ], style={"width": "49%", "display": "inline-block", "verticalAlign": "top"}),

            html.Div([
                html.H3("🚨 Últimas 3 Anomalías Detectadas", style={'margin-top': '20px'}),
                dash_table.DataTable(
                    id="tabla_anomalias_recientes",
                    columns=[
                        {"name": "Hora", "id": "login_time"},
                        {"name": "Ubicación", "id": "location"},
                        {"name": "Dispositivo", "id": "device"}
                    ],
                    style_table={"overflowX": "auto", 'backgroundColor': '#303030', 'maxHeight': '300px'},
                    style_cell={"textAlign": "left", 'backgroundColor': '#303030', 'color': 'white', 'padding': '10px'},
                    style_header={'backgroundColor': '#212121', 'color': 'white', 'fontWeight': 'bold'},
                    page_action='none',
                )
            ], style={"width": "49%", "display": "inline-block", "verticalAlign": "top", "marginLeft": "2%"}),
        ], style={"display": "flex", "justifyContent": "space-between", "flex-wrap": "wrap", "marginBottom": "20px"}),

        html.Div([
            html.H3("💻 Dispositivos de Conexión Frecuentes", style={'margin-top': '20px'}),
            dcc.Graph(id="grafica_dispositivos_usuario")
        ], style={"width": "100%", "marginTop": "20px"}),
    ], style={'padding': '20px'})
])


# --- Contenido de la nueva pestaña "Análisis INEGI" ---
inegi_analysis_content = html.Div([
    html.H2("Análisis de Datos INEGI", style={'font-weight':'bold','font-size':35, 'font-family':'sans-serif'}),
    html.P("Explora patrones de uso de internet y redes sociales basados en datos de la encuesta INEGI.", style={'margin-bottom': '20px'}),

    # Fila 1: Correlación y Proporción de Redes Sociales
    html.Div([
        html.Div([
            html.H3("🦠 Correlación: Virus vs. Uso de Redes Sociales"),
            dcc.Graph(id="inegi_grafica_correlacion_virus_redes")
        ], style={"width": "49%"}), # Ajustar ancho para dos columnas
        html.Div([
            html.H3("👥 Proporción de Usuarios de Redes Sociales"),
            dcc.Graph(id="inegi_grafica_proporcion_redes")
        ], style={"width": "49%"}) # Ajustar ancho para dos columnas
    ], style={"display": "flex", "justifyContent": "space-between", "margin-bottom": "20px"}),

    # Fila 2: Popularidad de Redes Sociales (General y con Virus)
    html.Div([
        html.Div([
            html.H3("📈 Popularidad de Redes Sociales"),
            dcc.Graph(id="inegi_grafica_popularidad_redes")
        ], style={"width": "49%"}), # Ajustar ancho para dos columnas
        html.Div([
            html.H3("😷 Popularidad de Redes Sociales (Usuarios con Virus)"),
            dcc.Graph(id="inegi_grafica_popularidad_redes_virus")
        ], style={"width": "49%"}) # Ajustar ancho para dos columnas
    ], style={"display": "flex", "justifyContent": "space-between", "margin-bottom": "20px"}),

    # Gráfica 5: Uso de Redes Sociales por Horas de Uso Diario (con Dropdown) - Mantiene 100%
    html.Div([
        html.H3("📊 Uso de Redes Sociales por Horas de Uso Diario"),
        html.Label("Selecciona una Red Social:"),
        dcc.Dropdown(
            id="inegi_dropdown_red_social",
            options=[{'label': red, 'value': red} for red in redes_sociales_cols],
            value=redes_sociales_cols[0] if redes_sociales_cols else None,
            style={'width': '50%', 'color': 'black', 'margin-bottom': '10px'}
        ),
        dcc.Graph(id="inegi_grafica_red_social_horas_uso")
    ], style={"width": "100%", "margin-bottom": "20px"}),

    # Gráfica 6: Promedio de Redes Sociales por Horas de Uso Diario - Mantiene 100%
    html.Div([
        html.H3("📊 Promedio de Redes Sociales por Horas de Uso"),
        dcc.Graph(id="inegi_grafica_promedio_redes_horas")
    ], style={"width": "100%", "margin-bottom": "20px"}),

    # Gráfica 7: Realización de Compras Online por Horas de Uso Diario - Mantiene 100%
    html.Div([
        html.H3("🛒 Compras Online por Horas de Uso Diario"),
        dcc.Graph(id="inegi_grafica_compras_horas_uso")
    ], style={"width": "100%", "margin-bottom": "20px"}),

    # Fila 3: Uso de Internet en Lugares Externos (Dropdown) y Usuarios que Usan Algún Tipo de Internet Externo
    html.Div([
        html.Div([
            html.H3("🌐 Uso de Internet en Lugares Externos"),
            html.Label("Selecciona un Tipo de Conexión Externa:"),
            dcc.Dropdown(
                id="inegi_dropdown_internet_externo",
                options=[{'label': tipo, 'value': tipo} for tipo in internet_externo_cols],
                value=internet_externo_cols[0] if internet_externo_cols else None,
                style={'width': '100%', 'color': 'black', 'margin-bottom': '10px'}
            ),
            dcc.Graph(id="inegi_grafica_internet_externo")
        ], style={"width": "49%"}), # Ajustar ancho para dos columnas
        html.Div([
            html.H3("👥 Usuarios que Usan Algún Tipo de Internet Externo"),
            dcc.Graph(id="inegi_grafica_total_internet_externo")
        ], style={"width": "49%"}) # Ajustar ancho para dos columnas
    ], style={"display": "flex", "justifyContent": "space-between", "margin-bottom": "20px"}),

    # Fila 4: Compras Online vs. Uso de Internet en {columna_externo} y Compras Online vs. Uso General de Internet Externo
    html.Div([
        html.Div([
            html.H3("🛒 Compras Online vs. Tipo de Internet Externo"),
            html.Label("Selecciona un Tipo de Conexión Externa:"),
            dcc.Dropdown(
                id="inegi_dropdown_compras_internet_externo",
                options=[{'label': tipo, 'value': tipo} for tipo in internet_externo_cols],
                value=internet_externo_cols[0] if internet_externo_cols else None,
                style={'width': '100%', 'color': 'black', 'margin-bottom': '10px'}
            ),
            dcc.Graph(id="inegi_grafica_compras_vs_internet_externo")
        ], style={"width": "49%"}), # Ajustar ancho para dos columnas
        html.Div([
            html.H3("🛒 Compras Online vs. Uso General de Internet Externo"),
            dcc.Graph(id="inegi_grafica_compras_vs_total_internet_externo")
        ], style={"width": "49%"}) # Ajustar ancho para dos columnas
    ], style={"display": "flex", "justifyContent": "space-between", "margin-bottom": "20px"}),

], style={'padding': '20px'})


# layout principal de la app
app.layout = html.Div([
    html.H1("Análisis de Riesgo de Robo de Identidad", style={'font-weight':'bold','font-size':45, 'font-family':'sans-serif'}),

    dcc.Tabs(id="tabs", value='tab-1', children=[
        dcc.Tab(label='Resumen del Riesgo', value='tab-1', style={'backgroundColor': '#212121', 'color': 'white'}, selected_style={'backgroundColor': '#007bff', 'color': 'white'}),
        dcc.Tab(label='Detalle de Usuario', value='tab-2', style={'backgroundColor': '#212121', 'color': 'white'}, selected_style={'backgroundColor': '#007bff', 'color': 'white'}),
        dcc.Tab(label='Análisis INEGI', value='tab-3', style={'backgroundColor': '#212121', 'color': 'white'}, selected_style={'backgroundColor': '#007bff', 'color': 'white'}), # Nueva Pestaña
    ], style={'width': '80%', 'margin': '20px auto'}),

    html.Div(id='tabs-content')
])


# --- Callbacks ---

# Callback para actualizar la tabla y gráficos generales (pestaña "Resumen")
@app.callback(
    [Output("tabla_usuarios", "data"),
     Output("grafica_riesgo", "figure"),
     Output("grafica_tendencia_alcaldia", "figure"),
     Output("grafica_dispositivo", "figure"),
     Output("grafica_virus", "figure"),
     Output("grafica_satisfaccion", "figure")], # Nueva salida para la gráfica de satisfacción
    [Input("interval", "n_intervals"),
     Input("selector_base", "value")]
)
def actualizar_datos(n, base):
    coleccion = db[base]
    documentos = list(coleccion.find({}))

    datos = []
    all_events_for_trend = []

    for doc in documentos:
        telegram_id = doc.get("telegram_id")

        if base == "usuarios_combinados":
            eventos = doc.get("eventos_acceso", [])
            alcaldia = "No disponible"
            dispositivo = "No disponible"
            nivel_riesgo_calc = "N/A"
            riesgo_futuro_calc = "N/A"
            if "nivel_riesgo" in doc:
                nivel_riesgo_calc = doc["nivel_riesgo"]
            if "riesgo_futuro_predicho" in doc:
                riesgo_futuro_calc = doc["riesgo_futuro_predicho"]

            if eventos:
                for evento in eventos:
                    if "login_time" in evento and "location" in evento:
                        all_events_for_trend.append({
                            "login_time": evento["login_time"],
                            "location": evento["location"]
                        })
                ultimo_evento = eventos[-1]
                alcaldia = ultimo_evento.get("location", "No disponible")
                dispositivo = ultimo_evento.get("device", "No disponible")

            datos.append({
                "telegram_id": telegram_id,
                "nivel_riesgo": nivel_riesgo_calc,
                "riesgo_futuro": riesgo_futuro_calc,
                "alcaldia_habitual": alcaldia,
                "dispositivo_frecuente": dispositivo,
                "fuente": "usuarios_combinados"
            })

        elif base == "respuestas_mixtas":
            respuestas = doc.get("respuestas", [])

            def obtener_respuesta(pregunta_clave):
                for r in respuestas:
                    if pregunta_clave.lower() in r["pregunta"].lower():
                        return r["respuesta"]
                return "No disponible"

            satisfaccion = "No disponible"
            for r in respuestas:
                if "satisfacción" in r["pregunta"].lower(): # Busca una pregunta que contenga "satisfacción"
                    satisfaccion = r["respuesta"]
                    break

            datos.append({
                "telegram_id": doc.get("telegram_id"),
                "nivel_riesgo": doc.get("nivel_riesgo", "N/A"),
                "riesgo_futuro": "No disponible (solo para datos simulados)",
                "alcaldia_habitual": obtener_respuesta("alcaldía"),
                "dispositivo_frecuente": obtener_respuesta("dispositivo"),
                "satisfaccion": satisfaccion, # Añadir el nivel de satisfacción
                "fuente": "respuestas_mixtas"
            })

    df = pd.DataFrame(datos)

    # === Gráficas ===
    df_virus = df[df['fuente'] == 'usuarios_combinados']
    if not df_virus.empty:
        riesgo_social_counts = df_virus['nivel_riesgo'].value_counts()
        grafica_virus = px.bar(
            x=riesgo_social_counts.index,
            y=riesgo_social_counts.values,
            labels={'x': 'Nivel de Riesgo', 'y': 'Número de Usuarios'},
            title='Riesgo en Redes Sociales (Basado en Nivel de Riesgo General)',
            color=riesgo_social_counts.index,
            color_discrete_map={"Bajo": "green", "Medio": "orange", "Alto": "red"}
        )
    else:
        grafica_virus = go.Figure(layout={"title": "Riesgo en Redes Sociales (Datos no disponibles para esta fuente)"})


    grafica_riesgo = px.bar(
        df["nivel_riesgo"].value_counts().index,
        df["nivel_riesgo"].value_counts().values,
        labels={'x': 'Nivel de Riesgo', 'y': 'Cantidad de Usuarios'},
        title="Usuarios por Nivel de Riesgo Actual",
        color=df["nivel_riesgo"].value_counts().index,
        color_discrete_map={"Bajo": "green", "Medio": "orange", "Alto": "red"}
    )

    df_tendencia_alcaldia = pd.DataFrame(all_events_for_trend)
    if not df_tendencia_alcaldia.empty and base == "usuarios_combinados":
        mexico_city_tz = pytz.timezone('America/Mexico_City')
        df_tendencia_alcaldia["login_time"] = pd.to_datetime(df_tendencia_alcaldia["login_time"])
        df_tendencia_alcaldia["login_time"] = df_tendencia_alcaldia["login_time"].dt.tz_localize('UTC').dt.tz_convert(mexico_city_tz)
        df_tendencia_alcaldia["fecha"] = df_tendencia_alcaldia["login_time"].dt.date

        alcaldia_daily_counts = df_tendencia_alcaldia.groupby(["fecha", "location"]).size().reset_index(name="conteo")

        grafica_tendencia_alcaldia = px.line(
            alcaldia_daily_counts,
            x="fecha",
            y="conteo",
            color="location",
            labels={'fecha': 'Fecha', 'conteo': 'Número de Conexiones', 'location': 'Alcaldía'},
            title="Tendencia de Conexiones por Alcaldía a lo largo del tiempo",
            template='slate',
            markers=True
        )
    else:
        grafica_tendencia_alcaldia = go.Figure(layout={"title": "Tendencia de Conexiones por Alcaldía (Datos no disponibles o fuente no compatible)"})


    grafica_dispositivo = px.pie(
        names=df["dispositivo_frecuente"].value_counts().index,
        values=df["dispositivo_frecuente"].value_counts().values,
        title="Uso de Dispositivos Frecuentes"
    )

    # Nueva gráfica para la satisfacción
    grafica_satisfaccion = go.Figure() # Figura por defecto vacía
    if base == "respuestas_mixtas" and "satisfaccion" in df.columns:
        df_satisfaccion = df[df['satisfaccion'] != "No disponible"].copy()
        if not df_satisfaccion.empty:
            # Intentar convertir a numérico, si falla, tratar como categórico
            df_satisfaccion['satisfaccion_num'] = pd.to_numeric(df_satisfaccion['satisfaccion'], errors='coerce')
            
            # Si hay valores numéricos válidos, usarlos. Si no, usar los originales como string.
            if df_satisfaccion['satisfaccion_num'].dropna().empty:
                satisfaccion_counts = df_satisfaccion['satisfaccion'].value_counts().sort_index()
                x_axis_label = 'Nivel de Satisfacción (Categoría)'
            else:
                satisfaccion_counts = df_satisfaccion['satisfaccion_num'].value_counts().sort_index()
                x_axis_label = 'Nivel de Satisfacción (Escala Numérica)'

            if not satisfaccion_counts.empty:
                grafica_satisfaccion = px.bar(
                    x=satisfaccion_counts.index.astype(str), # Asegurar que el eje X sea tratado como string para categorías
                    y=satisfaccion_counts.values,
                    labels={'x': x_axis_label, 'y': 'Número de Usuarios'},
                    title='Distribución del Nivel de Satisfacción de la Encuesta',
                    template='slate',
                    color=satisfaccion_counts.index.astype(str), # Colorear por el nivel de satisfacción
                    color_discrete_sequence=px.colors.sequential.Viridis # Usar una escala de colores secuencial
                )
                grafica_satisfaccion.update_layout(xaxis_type='category') # Tratar el eje X como categórico
            else:
                grafica_satisfaccion = go.Figure(layout={"title": "No hay datos de satisfacción válidos para graficar."})
        else:
            grafica_satisfaccion = go.Figure(layout={"title": "No hay datos de satisfacción disponibles para esta fuente."})
    else:
        # Si la base es "usuarios_combinados", mostrar un mensaje de no disponibilidad
        grafica_satisfaccion = go.Figure(layout={"title": "Gráfico de Satisfacción (Disponible solo para datos del chatbot)"})


    return df.to_dict("records"), grafica_riesgo, grafica_tendencia_alcaldia, grafica_dispositivo, grafica_virus, grafica_satisfaccion


# callback para la gráfica ARIMA por usuario (EN PESTAÑA 'DETALLE DE USUARIO')
@app.callback(
    Output("grafica_arima_usuario", "figure"),
    Input("usuario_detail_dropdown", "value")
)
def graficar_arima_usuario(telegram_id):
    if not telegram_id:
        return go.Figure(layout={"title": "Por favor, selecciona un usuario para ver la predicción ARIMA."})

    doc = db["usuarios_combinados"].find_one({"telegram_id": telegram_id})
    if not doc:
        return go.Figure(layout={"title": f"Usuario {telegram_id} no encontrado en la base de datos."})

    eventos = doc.get("eventos_acceso", [])
    if len(eventos) < 10:
        return go.Figure(layout={"title": f"No hay suficientes datos para el usuario {telegram_id} para análisis ARIMA (se requieren al menos 10 eventos de acceso)."})

    df_eventos = pd.DataFrame(eventos)

    mexico_city_tz = pytz.timezone('America/Mexico_City')
    df_eventos["login_time"] = pd.to_datetime(df_eventos["login_time"])
    df_eventos["login_time"] = df_eventos["login_time"].dt.tz_localize('UTC').dt.tz_convert(mexico_city_tz)

    df_eventos["fecha"] = df_eventos["login_time"].dt.date

    serie = df_eventos.groupby("fecha")["es_anomalia_simulda"].sum().sort_index()

    try:
        if len(serie) < 2:
             return go.Figure(layout={"title": f"No hay suficientes puntos de datos únicos para el usuario {telegram_id} para ajustar el modelo ARIMA después de agrupar por fecha."})

        modelo = ARIMA(serie, order=(1,1,1))
        modelo_fit = modelo.fit()
        forecast = modelo_fit.forecast(steps=5)
    except Exception as e:
        return go.Figure(layout={"title": f"Error al ajustar ARIMA para el usuario {telegram_id}: {str(e)}. Intenta con otro usuario o verifica los datos."})

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=serie.index,
        y=serie.values,
        mode='lines+markers',
        name='Anomalías reales',
        line=dict(color='#BF00FF', width=4),
        marker=dict(
            color='#FF9900',
            size=8,
            line=dict(width=1, color='DarkSlateGrey')
        )
    ))
    fig.add_trace(go.Scatter(
        x=pd.date_range(start=serie.index[-1], periods=6, freq='D')[1:],
        y=forecast,
        mode='lines+markers',
        name='Predicción ARIMA',
        line=dict(color='#FF0000', width=4, dash='dash')
    ))

    fig.update_layout(
        title=f"Serie de Anomalías y Predicción ARIMA - Usuario {telegram_id}",
        xaxis_title="Fecha",
        yaxis_title="Número de Anomalías",
        template='slate',
        height=450
    )
    return fig


# CALLBACK: para la tabla de Top 3 Lugares de Conexión Frecuentes
@app.callback(
    Output("tabla_lugares_conexion_frecuentes", "data"),
    Input("usuario_detail_dropdown", "value")
)
def actualizar_tabla_lugares_conexion_frecuentes(telegram_id):
    if not telegram_id:
        return []

    doc = db["usuarios_combinados"].find_one({"telegram_id": telegram_id})
    if not doc:
        return []

    eventos = doc.get("eventos_acceso", [])
    if not eventos:
        return []

    df_eventos = pd.DataFrame(eventos)

    location_counts = df_eventos["location"].dropna().value_counts().reset_index()
    location_counts.columns = ["location", "count"]
    top_3_locations = location_counts.head(3)

    return top_3_locations.to_dict("records")


# CALLBACK: para la tabla de Últimas 3 Anomalías
@app.callback(
    Output("tabla_anomalias_recientes", "figure"), # Changed output to figure
    Input("usuario_detail_dropdown", "value")
)
def actualizar_tabla_anomalias_usuario(telegram_id):
    if not telegram_id:
        return go.Figure(layout={"title": "Por favor, selecciona un usuario."}) # Return a figure

    doc = db["usuarios_combinados"].find_one({"telegram_id": telegram_id})
    if not doc:
        return go.Figure(layout={"title": f"Usuario {telegram_id} no encontrado."}) # Return a figure

    eventos = doc.get("eventos_acceso", [])
    if not eventos:
        return go.Figure(layout={"title": f"No hay datos de eventos para el usuario {telegram_id}."}) # Return a figure

    df_eventos = pd.DataFrame(eventos)

    anomalias_df = df_eventos[df_eventos["es_anomalia_simulda"] == 1].copy()

    if anomalias_df.empty:
        return go.Figure(layout={"title": f"No se detectaron anomalías para el usuario {telegram_id}."}) # Return a figure

    mexico_city_tz = pytz.timezone('America/Mexico_City')
    anomalias_df["login_time"] = pd.to_datetime(anomalias_df["login_time"])
    anomalias_df["login_time"] = anomalias_df["login_time"].dt.tz_localize('UTC').dt.tz_convert(mexico_city_tz)
    anomalias_df["login_time_str"] = anomalias_df["login_time"].dt.strftime('%Y-%m-%d %H:%M:%S') # New column for string format

    anomalias_df = anomalias_df.sort_values(by="login_time", ascending=False)

    top_3_anomalias = anomalias_df.head(3)

    # Create a table using plotly.graph_objs.Figure
    header_values = ["Hora", "Ubicación", "Dispositivo"]
    cell_values = [
        top_3_anomalias["login_time_str"],
        top_3_anomalias["location"],
        top_3_anomalias["device"]
    ]

    fig = go.Figure(data=[go.Table(
        header=dict(values=header_values,
                    fill_color='paleturquoise',
                    align='left'),
        cells=dict(values=cell_values,
                   fill_color='lavender',
                   align='left'))
    ])
    fig.update_layout(title_text=f"Últimas 3 Anomalías Detectadas - Usuario {telegram_id}")
    return fig


# CALLBACK: para la gráfica de barras de dispositivos por usuario
@app.callback(
    Output("grafica_dispositivos_usuario", "figure"),
    Input("usuario_detail_dropdown", "value")
)
def graficar_dispositivos_usuario(telegram_id):
    if not telegram_id:
        return go.Figure(layout={"title": "Por favor, selecciona un usuario para ver sus dispositivos de conexión."})

    doc = db["usuarios_combinados"].find_one({"telegram_id": telegram_id})
    if not doc:
        return go.Figure(layout={"title": f"Usuario {telegram_id} no encontrado en la base de datos."})

    eventos = doc.get("eventos_acceso", [])
    if not eventos:
        return go.Figure(layout={"title": f"No hay datos de eventos de acceso para el usuario {telegram_id}."})

    df_eventos = pd.DataFrame(eventos)

    device_counts = df_eventos["device"].dropna().value_counts().reset_index()
    device_counts.columns = ['device', 'count']

    if device_counts.empty:
        return go.Figure(layout={"title": f"No se encontraron dispositivos para el usuario {telegram_id}."})

    fig = px.bar(
        device_counts,
        x='device',
        y='count',
        color='device',
        labels={'device': 'Tipo de Dispositivo', 'count': 'Número de Conexiones'},
        title=f"Dispositivos de Conexión Frecuentes - Usuario {telegram_id}",
        template='slate',
        height=400
    )
    fig.update_layout(
        xaxis={'categoryorder':'total descending'}
    )
    return fig


# --- Callbacks para la pestaña "Análisis INEGI" ---
# Gráfica 1: Correlación de usuarios con virus y uso de redes sociales (Scatter plot)
@app.callback(
    Output("inegi_grafica_correlacion_virus_redes", "figure"),
    Input("tabs", "value") # Se activa cuando se selecciona la pestaña
)
def update_inegi_grafica_correlacion_virus_redes(tab):
    if tab != 'tab-3' or df_inegi.empty:
        return go.Figure(layout={"title": "Cargando datos..." if tab == 'tab-3' else "Selecciona la pestaña Análisis INEGI"})

    # Asumiendo 'P7_18_1' es Virus y 'P7_15' es Uso de Redes Sociales
    if 'P7_18_1' not in df_inegi.columns or 'P7_15' not in df_inegi.columns:
        return go.Figure(layout={"title": "Columnas 'P7_18_1' o 'P7_15' no encontradas en el DataFrame INEGI."})

    df_plot = df_inegi.copy()
    # Convert P7_15 to numeric, coercing errors to NaN
    df_plot['P7_15'] = pd.to_numeric(df_plot['P7_15'], errors='coerce')

    # Convert P7_18_1 to numeric, coercing errors to NaN.
    # Then filter to keep only 0 and 1, assuming these are the relevant binary values.
    df_plot['P7_18_1'] = pd.to_numeric(df_plot['P7_18_1'], errors='coerce')
    df_plot = df_plot[df_plot['P7_18_1'].isin([0, 1])] # Keep only 0 and 1 for virus status

    # Drop rows where either P7_18_1 or P7_15 are NaN after conversions/filtering
    df_plot.dropna(subset=['P7_18_1', 'P7_15'], inplace=True)

    if df_plot.empty:
        return go.Figure(layout={"title": "No hay datos suficientes para la correlación después de filtrar."})

    fig = px.scatter(df_plot, x='P7_18_1', y='P7_15',
                     title='Correlación de Usuarios con Virus y Uso de Redes Sociales',
                     labels={'P7_18_1': 'Infección por Virus (0=No, 1=Sí)', 'P7_15': 'Uso de Redes Sociales'},
                     template='slate',
                     # Removed jitter as it causes TypeError in older Plotly Express versions
                     # jitter=0.2,
                     # Add color to distinguish between 'No' and 'Sí' virus categories
                     color='P7_18_1',
                     color_discrete_map={0: 'blue', 1: 'red'} # Example colors
                    )
    # Update x-axis ticks to show 'No' and 'Sí' labels
    fig.update_xaxes(tickvals=[0, 1], ticktext=['No', 'Sí'])
    return fig

# Gráfica 2: Usuarios de redes sociales (Proporción - Pie chart)
@app.callback(
    Output("inegi_grafica_proporcion_redes", "figure"),
    Input("tabs", "value")
)
def update_inegi_grafica_proporcion_redes(tab):
    if tab != 'tab-3' or df_inegi.empty:
        return go.Figure(layout={"title": "Cargando datos..." if tab == 'tab-3' else ""})

    if 'P7_15' not in df_inegi.columns:
        return go.Figure(layout={"title": "Columna 'P7_15' no encontrada."})

    # Asegurarse de que P7_15 sea numérica y manejar valores no válidos (por ejemplo, 9 o NaN)
    df_plot = df_inegi.copy()
    df_plot['P7_15'] = pd.to_numeric(df_plot['P7_15'], errors='coerce')

    # Filtrar solo valores que representen Sí o No (1 y 2 según tu script original)
    # y cualquier otro valor significativo. Aquí asumo 1=Sí, 2=No, 9=No especificado.
    frec = df_plot['P7_15'].value_counts().sort_index()

    # Mapear etiquetas numéricas a strings descriptivos
    labels_map = {1: 'Sí', 2: 'No', 9: 'No especificado'}
    frec_labels = [labels_map.get(idx, f"Valor {int(idx)}") for idx in frec.index]

    if frec.empty:
        return go.Figure(layout={"title": "No hay datos para la proporción de redes sociales."})

    fig = px.pie(names=frec_labels, values=frec.values,
                 title='Proporción de Usuarios de Redes Sociales',
                 template='slate',
                 # Añadir una secuencia de colores más atractiva
                 color_discrete_sequence=px.colors.sequential.Viridis # Puedes probar otras como 'Plasma', 'Jet', 'Rainbow'
                )
    fig.update_traces(textinfo='percent+label')
    return fig

# Gráfica 3: Popularidad de Redes Sociales (Bar chart)
@app.callback(
    Output("inegi_grafica_popularidad_redes", "figure"),
    Input("tabs", "value")
)
def update_inegi_grafica_popularidad_redes(tab):
    if tab != 'tab-3' or df_inegi.empty:
        return go.Figure(layout={"title": "Cargando datos..." if tab == 'tab-3' else ""})

    if not all(col in df_inegi.columns for col in redes_sociales_cols):
        return go.Figure(layout={"title": "Columnas de redes sociales no encontradas."})

    df_redes = df_inegi[redes_sociales_cols].copy()
    # Asegurarse de que los valores sean 0 o 1, y sumar directamente
    conteo_redes = df_redes.apply(lambda x: (x == 1).sum()).sort_values(ascending=False)

    if conteo_redes.empty:
        return go.Figure(layout={"title": "No hay datos de popularidad de redes sociales."})

    fig = px.bar(x=conteo_redes.index, y=conteo_redes.values,
                 title='Popularidad de Redes Sociales',
                 labels={'x': 'Red Social', 'y': 'Número de Usuarios'},
                 template='slate',
                 color=conteo_redes.index, # Colorear por el nombre de la red social
                 color_discrete_sequence=px.colors.qualitative.Plotly # Secuencia de colores cualitativos
                )
    return fig

# Gráfica 4: Popularidad de redes sociales entre usuarios positivos a virus (Bar chart)
@app.callback(
    Output("inegi_grafica_popularidad_redes_virus", "figure"),
    Input("tabs", "value")
)
def update_inegi_grafica_popularidad_redes_virus(tab):
    if tab != 'tab-3' or df_inegi.empty:
        return go.Figure(layout={"title": "Cargando datos..." if tab == 'tab-3' else ""})

    if 'P7_18_1' not in df_inegi.columns or not all(col in df_inegi.columns for col in redes_sociales_cols):
        return go.Figure(layout={"title": "Columnas necesarias no encontradas."})

    df_positivos = df_inegi[df_inegi['P7_18_1'] == 1].copy()
    if df_positivos.empty:
        return go.Figure(layout={"title": "No hay usuarios positivos a virus para analizar."})

    df_redes_positivos = df_positivos[redes_sociales_cols].copy()
    conteo_redes_positivos = df_redes_positivos.apply(lambda x: (x == 1).sum()).sort_values(ascending=False)

    if conteo_redes_positivos.empty:
        return go.Figure(layout={"title": "No hay datos de popularidad de redes sociales para usuarios con virus."})

    fig = px.bar(x=conteo_redes_positivos.index, y=conteo_redes_positivos.values,
                 title='Popularidad de Redes Sociales entre Usuarios Positivos a Virus',
                 labels={'x': 'Red Social', 'y': 'Número de Usuarios Positivos'},
                 template='slate',
                 color=conteo_redes_positivos.index, # Colorear por el nombre de la red social
                 color_discrete_sequence=px.colors.qualitative.Bold # Otra secuencia de colores cualitativos
                )
    return fig

# Gráfica 5: Uso de Redes Sociales por Horas de Uso Diario (con Dropdown)
@app.callback(
    Output("inegi_grafica_red_social_horas_uso", "figure"),
    Input("inegi_dropdown_red_social", "value")
)
def update_inegi_grafica_red_social_horas_uso(selected_red_social):
    if df_inegi.empty or selected_red_social is None:
        return go.Figure(layout={"title": "Selecciona una red social."})

    if 'grupo_horas_internet' not in df_inegi.columns or selected_red_social not in df_inegi.columns:
        return go.Figure(layout={"title": f"Columnas necesarias para {selected_red_social} no encontradas."})

    df_plot = df_inegi.copy()
    # Asegurarse de que los datos de la red social sean tratados como enteros
    # Mapeo de valores si 0, 1, 2... tienen un significado específico, o si hay 9s (No especificado)
    # Reemplazar NaN con un valor para que crosstab no los ignore. Aquí asumimos 9 para NaN.
    df_plot[selected_red_social] = pd.to_numeric(df_plot[selected_red_social], errors='coerce').fillna(9).astype(int)

    cross_tab = pd.crosstab(df_plot['grupo_horas_internet'], df_plot[selected_red_social])

    # Mapear los nombres de las columnas para que sean legibles y coincidan con los valores que pueden existir
    # Asegúrate de que este mapeo sea exacto a los valores en tu CSV (0, 1, 9, etc.)
    column_mapping = {
        0: 'No',
        1: 'Sí',
        9: 'No especificado'
    }

    # Renombrar solo las columnas que existan en cross_tab.columns
    # Esto evita el ValueError si alguna columna (ej. '9') no está presente
    cols_to_rename = {col: column_mapping[col] for col in cross_tab.columns if col in column_mapping}
    cross_tab.rename(columns=cols_to_rename, inplace=True)

    proportions = cross_tab.div(cross_tab.sum(axis=1), axis=0) * 100
    proportions.index.name = 'Horas de Uso Diario'

    # Seleccionar solo las columnas que queremos graficar ('Sí' y 'No'), ignorando 'No especificado'
    cols_to_plot = [col for col in ['Sí', 'No'] if col in proportions.columns]

    if proportions.empty or not cols_to_plot:
        return go.Figure(layout={"title": f"No hay datos suficientes para graficar 'Sí' o 'No' para {selected_red_social}."})

    fig = px.bar(proportions, x=proportions.index, y=cols_to_plot,
                 title=f'Uso de {selected_red_social} por Horas de Uso Diario',
                 labels={'value': 'Porcentaje de Usuarios', 'variable': 'Usa'},
                 barmode='group', # Barras agrupadas
                 template='slate',
                 # Colores específicos para 'Sí' y 'No'
                 color_discrete_map={'Sí': 'green', 'No': 'red'}
                )
    return fig

# Gráfica 6: Promedio de Redes Sociales por Horas de Uso Diario
@app.callback(
    Output("inegi_grafica_promedio_redes_horas", "figure"),
    Input("tabs", "value")
)
def update_inegi_grafica_promedio_redes_horas(tab):
    if tab != 'tab-3' or df_inegi.empty:
        return go.Figure(layout={"title": "Cargando datos..." if tab == 'tab-3' else ""})

    if 'grupo_horas_internet' not in df_inegi.columns or 'num_redes_sociales' not in df_inegi.columns:
        return go.Figure(layout={"title": "Columnas necesarias no encontradas."})

    promedio_redes_por_grupo = df_inegi.groupby('grupo_horas_internet')['num_redes_sociales'].mean().reset_index()
    promedio_redes_por_grupo.columns = ['grupo_horas_internet', 'promedio']

    if promedio_redes_por_grupo.empty:
        return go.Figure(layout={"title": "No hay datos para el promedio de redes sociales por horas de uso."})

    fig = px.line(promedio_redes_por_grupo, x='grupo_horas_internet', y='promedio',
                 title='Promedio de Redes Sociales por Horas de Uso Diario',
                 labels={'grupo_horas_internet': 'Horas de Uso Diario', 'promedio': 'Promedio de Redes Sociales'},
                 template='slate',
                 markers=True, # Añadir marcadores para los puntos de la línea
                 color_discrete_sequence=px.colors.qualitative.Pastel # Secuencia de colores cualitativos
                )
    fig.update_layout(
        yaxis_range=[0, 10] # Sincronizar el rango del eje Y de 0 a 10
    )
    return fig

# Gráfica 7: Realización de Compras Online por Horas de Uso Diario
@app.callback(
    Output("inegi_grafica_compras_horas_uso", "figure"),
    Input("tabs", "value")
)
def update_inegi_grafica_compras_horas_uso(tab):
    if tab != 'tab-3' or df_inegi.empty:
        return go.Figure(layout={"title": "Cargando datos..." if tab == 'tab-3' else ""})

    if 'grupo_horas_internet' not in df_inegi.columns or columna_compras not in df_inegi.columns:
        return go.Figure(layout={"title": "Columnas necesarias no encontradas."})

    df_plot = df_inegi.copy()
    df_plot[columna_compras] = pd.to_numeric(df_plot[columna_compras], errors='coerce').fillna(0).astype(int) # Asumimos 0 para NaN si es un valor de no respuesta

    cross_tab_compras = pd.crosstab(df_plot['grupo_horas_internet'], df_plot[columna_compras])

    # Renombrar solo las columnas que existan
    cols_to_rename_compras = {col: nombres_compras[col] for col in cross_tab_compras.columns if col in nombres_compras}
    cross_tab_compras.rename(columns=cols_to_rename_compras, inplace=True)

    proportions_compras = cross_tab_compras.div(cross_tab_compras.sum(axis=1), axis=0) * 100
    proportions_compras.index.name = 'Horas de Uso Diario'

    # Seleccionar solo las columnas 'Sí' y 'No' para graficar si existen
    cols_to_plot_compras = [col for col in ['Sí', 'No'] if col in proportions_compras.columns]

    if proportions_compras.empty or not cols_to_plot_compras:
        return go.Figure(layout={"title": "No hay datos para la realización de compras online."})

    fig = px.bar(proportions_compras, x=proportions_compras.index, y=cols_to_plot_compras,
                 title='Realización de Compras Online por Horas de Uso Diario',
                 labels={'value': 'Porcentaje de Usuarios', 'variable': 'Compra Online'},
                 barmode='group',
                 template='slate')
    return fig

# Gráfica 8: Uso de Internet en Lugares Externos (con Dropdown)
@app.callback(
    Output("inegi_grafica_internet_externo", "figure"),
    Input("inegi_dropdown_internet_externo", "value")
)
def update_inegi_grafica_internet_externo(selected_internet_externo):
    if df_inegi.empty or selected_internet_externo is None:
        return go.Figure(layout={"title": "Selecciona un tipo de conexión externa."})

    if selected_internet_externo not in df_inegi.columns:
        return go.Figure(layout={"title": f"Columna '{selected_internet_externo}' no encontrada."})

    df_plot = df_inegi.copy()
    # Asegurarse de que la columna sea numérica y manejar NaN/otros valores
    df_plot[selected_internet_externo] = pd.to_numeric(df_plot[selected_internet_externo], errors='coerce').fillna(9).astype(int)

    conteo = df_plot[selected_internet_externo].value_counts().sort_index()

    # Mapear etiquetas numéricas a strings descriptivos
    labels_map_internet_externo = {0: 'No', 1: 'Sí', 9: 'No especificado'} # Ajusta si hay otros valores
    conteo_labels = [labels_map_internet_externo.get(idx, f"Valor {int(idx)}") for idx in conteo.index]

    if conteo.empty:
        return go.Figure(layout={"title": f"No hay datos para {selected_internet_externo}."})

    fig = px.bar(x=conteo_labels, y=conteo.values,
                 title=f'Uso de Internet en {selected_internet_externo}',
                 labels={'x': 'Respuesta', 'y': 'Número de Usuarios'},
                 template='slate',
                 color=conteo_labels, # Colorear por la etiqueta de respuesta
                 color_discrete_sequence=px.colors.qualitative.D3 # Secuencia de colores cualitativos
                )
    return fig

# Gráfica 9: Usuarios que Usan Algún Tipo de Internet Externo
@app.callback(
    Output("inegi_grafica_total_internet_externo", "figure"),
    Input("tabs", "value")
)
def update_inegi_grafica_total_internet_externo(tab):
    if tab != 'tab-3' or df_inegi.empty:
        return go.Figure(layout={"title": "Cargando datos..." if tab == 'tab-3' else ""})

    if 'usa_internet_externo' not in df_inegi.columns:
        return go.Figure(layout={"title": "Columna 'usa_internet_externo' no encontrada."})

    conteo_externo_total = df_inegi['usa_internet_externo'].value_counts().reset_index()
    conteo_externo_total.columns = ['usa_internet_externo', 'count']
    conteo_externo_total['usa_internet_externo_label'] = conteo_externo_total['usa_internet_externo'].map({True: 'Sí', False: 'No'})

    if conteo_externo_total.empty:
        return go.Figure(layout={"title": "No hay datos para usuarios que usan algún tipo de internet externo."})

    fig = px.bar(conteo_externo_total, x='usa_internet_externo_label', y='count',
                 title='Usuarios que Usan Algún Tipo de Internet Externo',
                 labels={'usa_internet_externo_label': 'Usa Internet Externo', 'count': 'Número de Usuarios'},
                 template='slate',
                 color='usa_internet_externo_label', # Colorear por la etiqueta
                 color_discrete_sequence=px.colors.qualitative.Set1 # Usar una secuencia de colores cualitativa diferente
                )
    return fig

# Gráfica 10: Compras Online vs. Uso de Internet en {columna_externo} (con Dropdown)
@app.callback(
    Output("inegi_grafica_compras_vs_internet_externo", "figure"),
    Input("inegi_dropdown_compras_internet_externo", "value")
)
def update_inegi_grafica_compras_vs_internet_externo(selected_col_externo):
    if df_inegi.empty or selected_col_externo is None:
        return go.Figure(layout={"title": "Selecciona un tipo de conexión externa."})

    if selected_col_externo not in df_inegi.columns or columna_compras not in df_inegi.columns:
        return go.Figure(layout={"title": "Columnas necesarias no encontradas."})

    df_plot = df_inegi.copy()
    df_plot[selected_col_externo] = pd.to_numeric(df_plot[selected_col_externo], errors='coerce').fillna(9).astype(int)
    df_plot[columna_compras] = pd.to_numeric(df_plot[columna_compras], errors='coerce').fillna(0).astype(int)

    cross_tab = pd.crosstab(df_plot[selected_col_externo], df_plot[columna_compras])

    # Mapeo para la columna de internet externo
    internet_externo_values_map = {0: 'No', 1: 'Sí', 9: 'No especificado'}
    cross_tab.index = cross_tab.index.map(internet_externo_values_map)

    # Renombrar columnas de compras
    cols_to_rename_compras = {col: nombres_compras[col] for col in cross_tab.columns if col in nombres_compras}
    cross_tab.rename(columns=cols_to_rename_compras, inplace=True)

    proportions = cross_tab.div(cross_tab.sum(axis=1), axis=0) * 100
    proportions.index.name = 'Usa Internet en ' + selected_col_externo

    cols_to_plot = [col for col in ['Sí', 'No'] if col in proportions.columns]
    if proportions.empty or not cols_to_plot:
        return go.Figure(layout={"title": f"No hay datos de 'Sí' o 'No' para compras online y {selected_col_externo}."})

    fig = px.bar(proportions, x=proportions.index, y=cols_to_plot,
                 title=f'Compras Online vs. Uso de Internet en {selected_col_externo}',
                 labels={'value': 'Porcentaje de Usuarios', 'variable': 'Compra Online'},
                 barmode='group',
                 template='slate')
    return fig

# Gráfica 11: Compras Online vs. Uso de Algún Internet Externo
@app.callback(
    Output("inegi_grafica_compras_vs_total_internet_externo", "figure"),
    Input("tabs", "value")
)
def update_inegi_grafica_compras_vs_total_internet_externo(tab):
    if tab != 'tab-3' or df_inegi.empty:
        return go.Figure(layout={"title": "Cargando datos..." if tab == 'tab-3' else ""})

    if 'usa_internet_externo' not in df_inegi.columns:
        return go.Figure(layout={"title": "Columna 'usa_internet_externo' no encontrada."})

    conteo_externo_total = df_inegi['usa_internet_externo'].value_counts().reset_index()
    conteo_externo_total.columns = ['usa_internet_externo', 'count']
    conteo_externo_total['usa_internet_externo_label'] = conteo_externo_total['usa_internet_externo'].map({True: 'Sí', False: 'No'})

    if conteo_externo_total.empty:
        return go.Figure(layout={"title": "No hay datos para usuarios que usan algún tipo de internet externo."})

    fig = px.bar(conteo_externo_total, x='usa_internet_externo_label', y='count',
                 title='Compras Online vs. Uso de Algún Internet Externo',
                 labels={'usa_internet_externo_label': 'Usa Internet Externo', 'count': 'Número de Usuarios'},
                 template='slate',
                 color='usa_internet_externo_label', # Colorear por la etiqueta
                 color_discrete_sequence=px.colors.qualitative.Pastel # Usar una secuencia de colores cualitativa diferente
                )
    return fig


# Callback para cambiar el contenido de las pestañas
@app.callback(Output('tabs-content', 'children'),
              Input('tabs', 'value'))
def render_content(tab):
    if tab == 'tab-1':
        return dashboard_content
    elif tab == 'tab-2':
        return user_detail_content
    elif tab == 'tab-3': # Nueva pestaña
        return inegi_analysis_content
    return html.Div("Selecciona una pestaña")


# === Ejecutar app ===
if __name__ == "__main__":
    app.run(debug=True)