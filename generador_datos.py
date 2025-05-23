import pandas as pd
from pymongo import MongoClient
from faker import Faker
from dotenv import load_dotenv
import os
import random 
from datetime import datetime, timedelta

# cargar variable de entorno
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

#Conexion a Mongo DB 
cliente = MongoClient(MONGO_URI)
db = cliente["chatbot_db"]
coleccion = db["usuarios_combinados"]

# === limpiar la coleccion antes de insertar nuevos datos ===
coleccion.delete_many({})

# Iniciar Faker y semilla para reproducibilidad
faker = Faker()

# Lee las respuestas del chatbot simuladas
df_respuestas = pd.read_csv('respuestas_chatbot_simuladas.csv')

usuarios_combinados = []

for index, row in df_respuestas.iterrows():
    telegram_id = random.randint(1000000000, 9999999999)  # simulamos un telegram id

    #simular uno o varios accesos por usuario
    eventos_acceso = []
    for _ in range(random.randint(1, 8)):
        # Se define si el acceso sera anomalo con cierta probabilidad
        es_anomalia = random.random() < 0.4  # 30% de probabilidad de ser anómalo

        # Generador de datos anómalos o normales
        location = random.choice(['cuauhtemoc', 'benito_juarez', 'coyoacan', 'alvaro_obregon', 'magdalena_contreras', 'tlalpan', 'iztapalapa', 'venustiano_carranza', 'miguel_hidalgo', 'gustavo_a_madero', 'xochimilco', 'iztacalco', 'milpa_alta', 'miguel_hidalgo', 'tlahuac', 'azcapotzalco', 'Cuajimalpa', 'tlahuac'
        ]) if not es_anomalia else random.choice(['nezahualcoyotl', 'tlalnepantla', 'iztaplapa', 'tlahuac', 'ecatepec', 'naucalpan', 'tultitlan', 'chimalhuacan', 'hidalgo', 'puebla', 'coacalco', 'rusia', 'korea_del_sur','estados_unidos'])
        
        device = random.choice(["desktop", "smartphone", "tablet", "laptop"
        ]) if not es_anomalia else random.choice(["dispositivo_desconocido", "laptop", "raspberry_pi", "smart_tv", "kiosk"])

        hour = random.randint(7, 22) if not es_anomalia else random.choice([1, 2, 3, 4])
        fecha_base = faker.date_between(start_date='-6M', end_date='now')
        login_time = datetime.combine(fecha_base, datetime.min.time()) + timedelta(hours=hour)

        evento = {
            "login_time": str(login_time),
            "ip": faker.ipv4(),
            "device": device,
            "location": location,
            "es_anomalia_simulda": int(es_anomalia)
        }
        eventos_acceso.append(evento)

    usuario = {
        "telegram_id": telegram_id,
        "respuesta": {
            "usa_2fa": row['usa_2fa'],
            "reutiliza_contrasena": row['reutiliza_contrasena'],
            "alcaldia_habitual": row['ubicaciones_frecuentes'],
            "dispositivo_frecuente": row['dispositivos_usados'],
            "frecuencia_cambio_contrasena": row['cambia_contrasena'],

        },
        "eventos_acceso": eventos_acceso
    }

    usuarios_combinados.append(usuario)

# Insertar en MongoDB
coleccion.insert_many(usuarios_combinados)
print("Datos (con anomalias simuladas) insertados correctamente en MongoDB.")