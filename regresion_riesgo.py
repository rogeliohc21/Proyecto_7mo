import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# === Cargar entorno y conectar a Mongo ===
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
cliente = MongoClient(MONGO_URI)
db = cliente["chatbot_db"]
coleccion = db["usuarios_combinados"]

# === Leer datos de Mongo ===
documentos = list(coleccion.find({}))

# === Preparar los datos ===
datos = []
for doc in documentos:
    respuesta = doc.get("respuesta", {})
    anomalias = doc.get("anomalias_detectadas", 0)
    if "alcaldia_habitual" in respuesta and "dispositivo_frecuente" in respuesta and "frecuencia_cambio_contrasena" in respuesta:
        datos.append({
            "telegram_id": doc.get("telegram_id"),
            "alcaldia": respuesta["alcaldia_habitual"],
            "dispositivo": respuesta["dispositivo_frecuente"],
            "cambio_contrasena": respuesta["frecuencia_cambio_contrasena"],
            "anomalias": anomalias
        })

# Convertir a DataFrame
df = pd.DataFrame(datos)

# Codificar variables categóricas
cat_features = ["alcaldia", "dispositivo", "cambio_contrasena"]
encoder = OneHotEncoder()
X_cat = encoder.fit_transform(df[cat_features]).toarray()

# Variable numérica
y = df["anomalias"].values.reshape(-1, 1)
scaler = StandardScaler()
y_scaled = scaler.fit_transform(y)

# Entrenar modelo de regresión
modelo = LinearRegression()
modelo.fit(X_cat, y_scaled)

# Predicción y transformación inversa
y_pred_scaled = modelo.predict(X_cat)
y_pred = scaler.inverse_transform(y_pred_scaled).flatten()

# Clasificación en niveles
niveles = []
for pred in y_pred:
    if pred >= 3:
        niveles.append("🔴 Alto riesgo futuro")
    elif pred >= 2:
        niveles.append("🟡 Riesgo medio futuro")
    else:
        niveles.append("🟢 Bajo riesgo futuro")

# === Actualizar MongoDB ===
for i, doc in enumerate(df.itertuples()):
    coleccion.update_one(
        {"telegram_id": doc.telegram_id},
        {"$set": {"riesgo_futuro_predicho": niveles[i]}}
    )

print("Predicción de riesgo futuro agregada correctamente a MongoDB.")
