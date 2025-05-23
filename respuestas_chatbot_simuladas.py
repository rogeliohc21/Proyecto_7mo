import pandas as pd
from faker import Faker
import random

faker = Faker()
datos = []

for _ in range(200): # Se puede cambiar el numero
    fila = {
        "usa_2fa": random.choice(["Si", "No"]),
        "reutiliza_contrasena": random.choice(["Si", "No"]),
        "ubicaciones_frecuentes": random.choice(['cuauhtemoc', 'benito_juarez', 'coyoacan', 'alvaro_obregon', 'magdalena_contreras', 'tlalpan']),
        "dispositivos_usados": random.choice(['desktop', 'smartphone', 'tablet', 'laptop']),
        "cambia_contrasena": random.choice(['Mensual', 'Semestral', 'Trimestral', 'Bimestral', 'Anual', 'Nunca'])

    }
    datos.append(fila)

df = pd.DataFrame(datos)
df.to_csv('respuestas_chatbot_simuladas.csv', index=False)
print("Archivo CSV generado correctamente.")