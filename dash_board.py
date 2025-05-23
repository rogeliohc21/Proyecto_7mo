import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import pandas as pd
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# configuración inicial
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
cliente = MongoClient(MONGO_URI)
db = cliente["chatbot_db"]


# app dash
app = dash.Dash(__name__)
app.title = "Dashboard de Riesgo por Usuario"

# layout
app.layout = html.Div([
    html.H1("Análisis de Riesgo de Robo de Identidad", style={"textAlign": "center"}),

    html.Div([
        html.Label("Selecciona la fuente de datos:"),
        dcc.Dropdown(
            id="selector_base",
            options=[
                {"label":"Datos simulados (usuarios_combinados)", "value": "usuarios_combinados" },
                {"label": "Datos reales del chatbot (respuestas_mixtas)", "value": "respuestas_mixtas"}
            ],
            value="respuestas_mixtas",
            clearable=False,
        ),
    ], style={"margin": "20px"}),

    dcc.Interval(id="interval", interval=5*1000, n_intervals=0),

    html.Div([
        html.Div([
            html.H3("📊 Usuarios por Nivel de Riesgo Actual"),
            dcc.Graph(id="grafica_riesgo")
        ], style={"width": "48%"}),

        html.Div([
            html.H3("🔮 Predicción de Riesgo Futuro"),
            dcc.Graph(id="grafica_prediccion")
        ], style={"width": "48%"})
    ], style={"display": "flex", "justifyContent": "space-between"}),

    html.Div([
        html.Div([
            html.H3("📍 Distribución por Alcaldía"),
            dcc.Graph(id="grafica_alcaldia")
        ], style={"width": "48%"}),

        html.Div([
            html.H3("💻 Dispositivos Más Frecuentes"),
            dcc.Graph(id="grafica_dispositivo")
        ], style={"width": "48%"})
    ], style={"display": "flex", "justifyContent": "space-between"}),

    html.H2("📋 Tabla de Usuarios"),
    dash_table.DataTable(
        id="tabla_usuarios",
        columns=[
            {"name": "telegram_id", "id": "telegram_id"},
            {"name": "nivel_riesgo", "id": "nivel_riesgo"},
            {"name": "riesgo_futuro", "id": "riesgo_futuro"},
            {"name": "alcaldia_habitual", "id": "alcaldia_habitual"},
            {"name": "dispositivo_frecuente", "id": "dispositivo_frecuente"},
        ],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left"},
        page_size=10
    )
])


# callback para actualizar tabla y grafico
@app.callback(
    [Output("tabla_usuarios", "data"),
     Output("grafica_riesgo", "figure"),
     Output("grafica_prediccion", "figure"),
     Output("grafica_alcaldia", "figure"),
     Output("grafica_dispositivo", "figure")],
    [Input("interval", "n_intervals"),
     Input("selector_base", "value")] # Añadimos el Input para el selector_base
)
def actualizar_datos(n, base): # Ahora la función recibe el valor de la base
    coleccion = db[base]
    documentos = list(coleccion.find({}))

    datos = []
    
    for doc in documentos:
        telegram_id = doc.get("telegram_id")

        if "respuesta" in doc:
            eventos = doc.get("eventos_acceso", [])
            alcaldia = "No disponible"
            dispositivo = "No disponible"
            if eventos:
                ultimo_evento = eventos[-1]
                alcaldia = ultimo_evento.get("location", "No disponible")
                dispositivo = ultimo_evento.get("device", "No disponible")
        
            datos.append({
                "telegram_id": "telegram_id",
                "nivel_riesgo": doc.get("nivel_riesgo", "N/A"),
                "riesgo_futuro": doc.get("riesgo_futuro_predicho", "N/A"),
                "alcaldia_habitual": alcaldia,
                "dispositivo_frecuente": dispositivo,
                "fuente": "usuarios_combinados"
            })

        elif "respuestas" in doc:
            respuestas = doc.get("respuestas", [])

            def obtener_respuesta(pregunta_clave):
                for r in respuestas:
                    if pregunta_clave.lower() in r["pregunta"].lower():
                        return r["respuesta"]
                return "No disponible"

            datos.append({
                "telegram_id": doc.get("telegram_id"),
                "nivel_riesgo": doc.get("nivel_riesgo", "N/A"),
                "riesgo_futuro": "No disponible",
                "alcaldia_habitual": obtener_respuesta("alcaldía"),
                "dispositivo_frecuente": obtener_respuesta("dispositivo"),
                "fuente": "respuestas_mixtas"
            })

    df = pd.DataFrame(datos)

    # === Gráficas ===
    grafica_riesgo = {
        "data": [
            {
                "x": df["nivel_riesgo"].value_counts().index,
                "y": df["nivel_riesgo"].value_counts().values,
                "type": "bar",
                "marker": {"color": ["green", "orange", "red"][:len(df["nivel_riesgo"].unique())]}
            }
        ],
        "layout": {
            "title": "Usuarios por Nivel de Riesgo Actual",
            "xaxis": {"title": "Nivel de Riesgo"},
            "yaxis": {"title": "Cantidad de Usuarios"}
        }
    }

    grafica_prediccion = {
        "data": [
            {
                "x": df["riesgo_futuro"].value_counts().index,
                "y": df["riesgo_futuro"].value_counts().values,
                "type": "bar",
                "marker": {"color": ["green", "orange", "red"][:len(df["riesgo_futuro"].unique())]}
            }
        ],
        "layout": {
            "title": "Predicción de Riesgo Futuro",
            "xaxis": {"title": "Nivel de Riesgo Futuro"},
            "yaxis": {"title": "Cantidad de Usuarios"}
        }
    }

    grafica_alcaldia = {
        "data": [
            {
                "x": df["alcaldia_habitual"].value_counts().index,
                "y": df["alcaldia_habitual"].value_counts().values,
                "type": "bar",
                "marker": {"color": "#636EFA"}
            }
        ],
        "layout": {
            "title": "Distribución de Usuarios por Alcaldía",
            "xaxis": {"title": "Alcaldía"},
            "yaxis": {"title": "Cantidad de Usuarios"}
        }
    }

    grafica_dispositivo = {
        "data": [
            {
                "labels": df["dispositivo_frecuente"].value_counts().index,
                "values": df["dispositivo_frecuente"].value_counts().values,
                "type": "pie"
            }
        ],
        "layout": {
            "title": "Uso de Dispositivos Frecuentes"
        }
    }

    return df.to_dict("records"), grafica_riesgo, grafica_prediccion, grafica_alcaldia, grafica_dispositivo

# === Ejecutar app ===
if __name__ == "__main__":
    app.run(debug=True)