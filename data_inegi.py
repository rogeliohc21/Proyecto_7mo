import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


df = pd.read_csv("/Users/rogeliohidalgo/Documents/visual_code/pp/inegi - Sheet1.csv")






print(df.head())

# descargar en excel

#cdmx_inegi_1.to_excel('inegi.xlsx', index=False)




#Análisis: 
# Investiga la proporción de usuarios que realizan estas actividades y si existe 
# una correlación con haber experimentado infecciones por virus.
#Análisis: Determina la proporción de usuarios que utilizan redes sociales y cuáles 
# son las más populares. Cruza esta información con la ocurrencia de infecciones por 
# virus o la preocupación por la privacidad y el robo de información.
#Análisis: Investiga la distribución de la frecuencia y las horas de uso de internet.
# ¿Los usuarios más frecuentes o con mayor tiempo de conexión realizan más actividades 
# de riesgo (compras, redes sociales)?
#Análisis: Analiza la distribución de las horas dedicadas al uso de dispositivos ajenos. 
# ¿Hay un grupo considerable que los utiliza durante varias horas al día?
#Análisis: Calcula la proporción de usuarios que responden afirmativamente a la pregunta 
# sobre el uso de dispositivos ajenos en los últimos 3 meses. Cruza esta información con 
# otras variables como la frecuencia de uso de internet, los lugares de conexión y el uso de redes sociales.

#


#Análisis: 
# Investiga la proporción de usuarios que realizan estas actividades y si existe 
# una correlación con haber experimentado infecciones por virus.


# Correlación de Spearman
correlacion_spearman = df['P7_18_1'].corr(df['P7_17_1'], method='spearman')
print(f"Correlación de Spearman: {correlacion_spearman}")

correlacion_spearman = df['P7_18_1'].corr(df['P7_15'], method='spearman')
print(f"Correlación de Spearman: {correlacion_spearman}")

sns.scatterplot(x='P7_18_1', y='P7_15', data=df)
plt.title('Correlacion de usuarios con virus y uso de redes sociales')
plt.xlabel('virus')
plt.ylabel('uso de redes')
plt.grid(True)
plt.show()

#Análisis: Determina la proporción de usuarios que utilizan redes sociales y cuáles 
# son las más populares. Cruza esta información con la ocurrencia de infecciones por 
# virus o la preocupación por la privacidad y el robo de información.
print(df['P7_15'].unique())
df['P7_15'] = pd.to_numeric(df['P7_15'], errors='coerce')
frec = df['P7_15'].value_counts()
tamaños = frec.values
etiqueta = frec.index

fig, ax = plt.subplots()
ax.pie(tamaños, labels=etiqueta, autopct='%1.1f%%')
ax.axis('equal')
plt.title('usuarios de redes sociales')
plt.show()

#grafico de barras
nombres_redes = {
    'P7_16_1': 'facebook', 
    'P7_16_2': 'x',
    'P7_16_3': 'instagram', 
    'P7_16_4': 'linkedin',	
    'P7_16_5': 'snapchat',	
    'P7_16_6': 'whatsapp',	
    'P7_16_7': 'youtube',	
    'P7_16_8': 'pinterest', 
    'P7_16_9': 'messenger', 
    'P7_16_10': 'tiktok'
}

df.rename(columns=nombres_redes, inplace=True)
redes_sociales = list(nombres_redes.values())
df_redes = df[redes_sociales]
print(df_redes.head())

df['total_redes'] = df_redes.sum(axis=1)
conteo_redes = df_redes.apply(lambda x: (x == 1).sum()).sort_values(ascending=False)
plt.figure(figsize=(10, 6))
conteo_redes.plot(kind='bar')
plt.title('Popularidad de Redes Sociales')
plt.xlabel('Red Social')
plt.ylabel('Numero de Usuarios')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()

df_positivos = df[df['P7_18_1'] == 1].copy()

df_redes_positivos = df_positivos[redes_sociales]
conteo_redes_positivos = df_redes_positivos.apply(lambda x: (x == 1).sum()).sort_values(ascending=False)

plt.figure(figsize=(10, 6))
conteo_redes_positivos.plot(kind='bar', color='skyblue')
plt.title('Popularidad de redes sociales entre usuarios positivo a (virus)')
plt.xlabel('red social')
plt.ylabel('numero de usuarios positivos')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Asumo que tienes una columna llamada 'horas_internet_dia' y 'realiza_compras_online'
# Reemplaza estos nombres si tus columnas se llaman diferente

# Definir los grupos de horas de uso
bins = [0, 3, 6, 9, 12]  # Puedes ajustar estos rangos según tu criterio
labels = ['Menos de 1 hora', '1-3 horas', '3-6 horas', 'Más de 6 horas']
df['grupo_horas_internet'] = pd.cut(df['P7_4'], bins=bins, labels=labels, right=False)

# --- Análisis de Redes Sociales ---
print("\n--- Análisis de Redes Sociales por Horas de Uso ---")
redes_sociales = ['facebook', 'x', 'instagram', 'linkedin', 'snapchat', 'whatsapp', 'youtube', 'pinterest', 'messenger', 'tiktok']
df_redes = df[redes_sociales]

for red in redes_sociales:
    cross_tab = pd.crosstab(df['grupo_horas_internet'], df[red])
    print(f"\nTabla de contingencia para {red}:")
    print(cross_tab)
    proportions = cross_tab.div(cross_tab.sum(axis=1), axis=0) * 100
    proportions.plot(kind='bar', stacked=False, title=f'Uso de {red} por Horas de Uso Diario')
    plt.ylabel('Porcentaje de Usuarios')
    plt.xlabel('Horas de Uso Diario')
    plt.xticks(rotation=45, ha='right')
    plt.legend(title='Usa', labels=['No', 'Sí'])
    plt.tight_layout()
    plt.show()

# Calcular el número promedio de redes sociales utilizadas por grupo
df['num_redes_sociales'] = df_redes.sum(axis=1)
promedio_redes_por_grupo = df.groupby('grupo_horas_internet')['num_redes_sociales'].mean()
print("\nPromedio de redes sociales utilizadas por grupo de horas de uso:")
print(promedio_redes_por_grupo)
promedio_redes_por_grupo.plot(kind='bar', title='Promedio de Redes Sociales por Horas de Uso Diario')
plt.ylabel('Promedio de Redes Sociales')
plt.xlabel('Horas de Uso Diario')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()

# --- Análisis de Compras en Línea ---
print("\n--- Análisis de Compras en Línea por Horas de Uso ---")
cross_tab_compras = pd.crosstab(df['grupo_horas_internet'], df['P7_28'])
print("\nTabla de contingencia para Compras en Línea:")
print(cross_tab_compras)

proportions_compras = cross_tab_compras.div(cross_tab_compras.sum(axis=1), axis=0) * 100
proportions_compras.plot(kind='bar', stacked=False, title='Realización de Compras Online por Horas de Uso Diario')
plt.ylabel('Porcentaje de Usuarios')
plt.xlabel('Horas de Uso Diario')
plt.xticks(rotation=45, ha='right')
plt.legend(title='Compra Online', labels=['No contestó', 'Sí', 'No'])
plt.tight_layout()
plt.show()

import pandas as pd
import matplotlib.pyplot as plt

# Asumiendo los nombres de tus columnas
internet_externo = {
    'P7_8_4': 'sitio publico con costo',
    'P7_8_5': 'sitio publico sin costo',
    'P7_8_6': 'internte en lugares ajenos (familiares o amigos)'
}
df.rename(columns=internet_externo, inplace=True)
internet_externo_1 = list(internet_externo.values())
columnas_internet_externo = internet_externo_1
for columna in columnas_internet_externo:
    conteo = df[columna].value_counts().sort_index()
    print(f"\nConteo de usuarios que usan internet en '{columna}':")
    print(conteo)

    plt.figure(figsize=(6, 4))
    conteo.plot(kind='bar')
    plt.title(f'Uso de Internet en {columna}')
    plt.xlabel('Respuesta (0=No, 1=Sí)')
    plt.ylabel('Número de Usuarios')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.show()

# Adicionalmente, podemos ver si hay usuarios que usan múltiples tipos de internet externo
df['usa_internet_externo'] = df[columnas_internet_externo].any(axis=1)
conteo_externo_total = df['usa_internet_externo'].value_counts()
print("\nConteo de usuarios que usan algún tipo de internet externo:")
print(conteo_externo_total)

plt.figure(figsize=(6, 4))
conteo_externo_total.plot(kind='bar')
plt.title('Usuarios que Usan Algún Tipo de Internet Externo')
plt.xlabel('Usa Internet Externo (False=No, True=Sí)')
plt.ylabel('Número de Usuarios')
plt.xticks(rotation=0)
plt.tight_layout()
plt.show()

# También podemos ver combinaciones del uso de internet externo
df['combinacion_externo'] = df[columnas_internet_externo].astype(str).agg('-'.join, axis=1)
conteo_combinaciones = df['combinacion_externo'].value_counts().sort_values(ascending=False)
print("\nCombinaciones de uso de internet externo:")
print(conteo_combinaciones)

plt.figure(figsize=(10, 6))
conteo_combinaciones.plot(kind='bar')
plt.title('Combinaciones de Uso de Internet Externo')
plt.xlabel('Combinación (Con Costo-Sin Costo-Lugares Ajenos)')
plt.ylabel('Número de Usuarios')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()


import pandas as pd
import matplotlib.pyplot as plt

# ... (Tu código anterior para cargar y limpiar el DataFrame) ...

internet_externo = {
    'P7_8_4': 'sitio publico con costo',
    'P7_8_5': 'sitio publico sin costo',
    'P7_8_6': 'internte en lugares ajenos (familiares o amigos)'
}
df.rename(columns=internet_externo, inplace=True)
columnas_internet_externo = list(internet_externo.values())
columna_compras = 'realiza_compras_online'  # Asegúrate de que este sea el nombre correcto
nombres_compras = {0: 'No contestó', 1: 'Sí', 2: 'No'}

for columna_externo in columnas_internet_externo:
    try:
        cross_tab = pd.crosstab(df[columna_externo], df[columna_compras])
        cross_tab.rename(columns=nombres_compras, inplace=True)
        print(f"\nCruce entre '{columna_externo}' y '{columna_compras}':")
        print(cross_tab)

        proportions = cross_tab.div(cross_tab.sum(axis=1), axis=0) * 100
        proportions.plot(kind='bar', stacked=False)
        plt.title(f'Compras Online vs. Uso de Internet en {columna_externo}')
        plt.xlabel(f'Usa Internet en {columna_externo}')
        plt.ylabel('Porcentaje de Usuarios')
        plt.xticks(rotation=0)
        plt.legend(title='Compra Online')
        plt.tight_layout()
        plt.show()
    except KeyError as e:
        print(f"Error: La columna '{e}' no se encontró en el DataFrame para el cruce con compras en línea.")

# También podemos analizar si aquellos que usan CUALQUIER tipo de internet externo compran más online
try:
    df['usa_internet_externo'] = df[columnas_internet_externo].any(axis=1)
    cross_tab_externo_vs_compras = pd.crosstab(df['usa_internet_externo'], df[columna_compras])
    cross_tab_externo_vs_compras.rename(columns=nombres_compras, inplace=True)
    print("\nCruce entre 'Usa Algún Internet Externo' y 'Compras Online':")
    print(cross_tab_externo_vs_compras)

    proportions_externo_vs_compras = cross_tab_externo_vs_compras.div(cross_tab_externo_vs_compras.sum(axis=1), axis=0) * 100
    proportions_externo_vs_compras.plot(kind='bar', stacked=False)
    plt.title('Compras Online vs. Uso de Algún Internet Externo')
    plt.xlabel('Usa Algún Internet Externo (False=No, True=Sí)')
    plt.ylabel('Porcentaje de Usuarios')
    plt.xticks(rotation=0)
    plt.legend(title='Compra Online')
    plt.tight_layout()
    plt.show()
except KeyError as e:
    print(f"Error: La columna '{e}' no se encontró en el DataFrame para el cruce general de internet externo con compras en línea.")

# También podemos ver combinaciones del uso de internet externo
try:
    df['combinacion_externo'] = df[columnas_internet_externo].astype(str).agg('-'.join, axis=1)
    cross_tab_combinaciones_compras = pd.crosstab(df['combinacion_externo'], df[columna_compras])
    cross_tab_combinaciones_compras.rename(columns=nombres_compras, inplace=True)
    print("\nCruce entre 'Combinación de Uso de Internet Externo' y 'Compras Online':")
    print(cross_tab_combinaciones_compras)

    # No generamos un gráfico para tantas combinaciones para mantener la claridad
except KeyError as e:
    print(f"Error: La columna '{e}' no se encontró en el DataFrame para el cruce de combinaciones de internet externo con compras en línea.")