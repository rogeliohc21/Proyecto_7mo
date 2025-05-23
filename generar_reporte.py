from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.units import inch
import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import matplotlib.pyplot as plt
import os


def generar_nivel_riesgo(respuestas):
        if len(respuestas) < 7:
            raise ValueError("Se requieren al menos 7 respuestas.")
        total = sum(1 for r in respuestas[:7] if r["respuesta"].strip().lower() == "sí")
        if total <= 2:
            return 1, "🟢 Bajo riesgo", colors.green
        elif total <= 4:
            return 2, "🟡 Riesgo medio", colors.yellow
        else:
            return 3, "🔴 Alto riesgo", colors.red


    # 2. Dibujar la gráfica
def dibujar_grafica(canvas, nivel, color_barra):
    canvas.saveState()
    canvas.translate(inch, 5 * inch)
    
    nivel = max(0, min(nivel, 3))  # Asegura que esté entre 0 y 3
    
    # Marco de la barra
    canvas.setStrokeColor(colors.black)
    canvas.rect(0, 0, 4 * inch, 0.75 * inch, fill=0)

    # Barra de nivel
    canvas.setFillColor(color_barra)
    canvas.rect(0, 0, (nivel / 3) * 4 * inch, 0.75 * inch, fill=1)

    # Etiquetas
    canvas.setFont("Helvetica-Bold", 14)
    canvas.setFillColor(colors.black)
    canvas.drawString(-0.5 * inch, 0.35 * inch, "Riesgo")
    canvas.drawString(2 * inch, 0.99 * inch, "Nivel de Riesgo")

    # Líneas de marcas
    canvas.line(0, 0, 4 * inch, 0)
    for i in range(4):
        x = (i / 3) * 4 * inch
        canvas.line(x, 0, x, -0.1 * inch)
        canvas.drawString(x - 0.1 * inch, -0.25 * inch, str(i))

    canvas.restoreState()



def crear_reporte_pdf(nombre_pdf, respuestas, nivel_riesgo, texto_riesgo, color_riesgo):
    c = canvas.Canvas(nombre_pdf, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Reporte de Seguridad Digital")

    c.setFont("Helvetica", 12)
    y = height - 100
    for item in respuestas:
        pregunta = item.get("pregunta", "Pregunta desconocida")
        respuesta = item.get("respuesta", "Sin respuesta")
        c.drawString(72, y, f"{pregunta}: {respuesta}")
        y -= 20

    # Dibuja gráfica del nivel de riesgo
    if nivel_riesgo == 0:
        color = colors.green
    elif nivel_riesgo == 1:
        color = colors.yellow
    elif nivel_riesgo == 2:
        color = colors.orange
    else:
        color = colors.red

    dibujar_grafica(c, nivel_riesgo, color_riesgo)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 120, f"Nivel de riesgo: {texto_riesgo}")

    c.save()


