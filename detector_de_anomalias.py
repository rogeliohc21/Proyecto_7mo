import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler, OneHotEncoder
import numpy as np
import os

# Cargar Variables de entorno
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Conectar en MongoDB
cliente = MongoClient(MONGO_URI)
db = cliente["chatbot_db"]
coleccion = db["usuarios_combinados"]

# Extraccion de eventos de acceso
documentos = list(coleccion.find())
datos = []

for doc in documentos:
    for evento in doc.get("eventos_acceso", []):
        login_time = pd.to_datetime(evento.get("login_time", None), errors='coerce')
        if pd.notnull(login_time):
            datos.append({
                "telegram_id": doc.get("telegram_id"),
                "device": evento.get("device"),
                "location": evento.get("location"),
                "hour": login_time.hour,
                "es_anomalia_simulada": evento.get("es_anomalia_simulada", 0)
            })

# Crear DataFrame
df = pd.DataFrame(datos)

if df.empty:
    print("No se encontraron datos validos para entrenar el modelo.")
else:
    # Codificacion y escalado
    encoder = OneHotEncoder()
    scaler = StandardScaler()

    X_categorico = encoder.fit_transform(df[["device", "location"]]).toarray()
    X_numerico = scaler.fit_transform(df[["hour"]])

    X = np.hstack((X_categorico, X_numerico))

    # Entrenamiento del modelo
    modelo = IsolationForest(contamination=0.4, random_state=42)
    modelo.fit(X)

    # Prediccion de anomalías
    df["anomaly"] = modelo.predict(X)
    df["anomaly"] = df["anomaly"].map({1: 0, -1: 1})  # 1 = anomalo

    # Resultado por usuario
    anomalias_por_usuario = df.groupby("telegram_id")["anomaly"].sum().reset_index()
    anomalias_por_usuario.columns = ["telegram_id", "anomalias_detectadas"]

    # mostrar evaluacion simple si exiten etiquetas simuladas
    if "es_anomalia_simulda" in df.columns:
        print("\n Evaluación preliminar del modelo (deteccion vs simulación):")
        print(pd.crosstab(df["es_anomalia_simulda"], df["anomaly"], rownames=["Simulación"], colnames=["Detectada"]))

    
    
    print("\n Análisis completado. Muestra de anomalías detectadas por usuario:")
    print(anomalias_por_usuario.head())