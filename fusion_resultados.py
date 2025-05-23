import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Cargar entorno
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Conexión a MongoDB
cliente = MongoClient(MONGO_URI)
db = cliente["chatbot_db"]
coleccion_usuarios = db["usuarios_combinados"]
coleccion_respuestas = db["respuestas_mixtas"]

# Cargar los resultados de anomalías desde la colección de usuarios
documentos = list(coleccion_usuarios.find())
datos = []

for doc in documentos:
    for evento in doc.get("eventos_acceso", []):
        login_time = pd.to_datetime(evento.get("login_time", None), errors='coerce')
        if pd.notnull(login_time):
            datos.append({
                "telegram_id": doc.get("telegram_id"),
                "device": evento.get("device"),
                "location": evento.get("location"),
                "hour": login_time.hour
            })

# Preparar DataFrame y entrenar modelo (como en detector)
df = pd.DataFrame(datos)

if not df.empty:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    import numpy as np

    encoder = OneHotEncoder()
    scaler = StandardScaler()

    X_categorico = encoder.fit_transform(df[["device", "location"]]).toarray()
    X_numerico = scaler.fit_transform(df[["hour"]])
    X = np.hstack((X_categorico, X_numerico))

    modelo = IsolationForest(contamination=0.1, random_state=42)
    modelo.fit(X)

    df["anomaly"] = modelo.predict(X)
    df["anomaly"] = df["anomaly"].map({1: 0, -1: 1})

    resumen = df.groupby("telegram_id")["anomaly"].sum().reset_index()
    resumen.columns = ["telegram_id", "anomalias_detectadas"]

    # Calcular nivel de riesgo
    def calcular_nivel(anomalias):
        if anomalias >= 3:
            return "Alto"
        elif anomalias == 2:
            return "Medio"
        else:
            return "Bajo"

    resumen["nivel_riesgo"] = resumen["anomalias_detectadas"].apply(calcular_nivel)

    # Actualizar en MongoDB y unir respuestas
    for _, row in resumen.iterrows():
        telegram_id = row["telegram_id"]

        # Buscar la respuesta correspondiente en la segunda colección
        respuesta = coleccion_respuestas.find_one({"telegram_id": telegram_id})

        # Actualizar en usuarios_combinados
        coleccion_usuarios.update_one(
            {"telegram_id": telegram_id},
            {"$set": {
                "anomalias_detectadas": int(row["anomalias_detectadas"]),
                "nivel_riesgo": row["nivel_riesgo"],
                "respuesta": respuesta.get("respuesta") if respuesta else None
            }}
        )

    print("✅ Datos fusionados correctamente en MongoDB con nivel de riesgo y respuestas.")
else:
    print("⚠️ No se encontraron datos para calcular anomalías.")
