# app.py
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
)
from pymongo import MongoClient
from dotenv import load_dotenv
import tempfile
import os
import re

# Assuming generar_reporte.py is in the same directory
from generar_reporte import crear_reporte_pdf, generar_nivel_riesgo

# === Cargar .env ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # This will be your Render app's URL

# === Conectar a Mongo ===
cliente = MongoClient(MONGO_URI)
db = cliente["chatbot_db"]
coleccion = db["respuestas_mixtas"]

# === Estados de la conversación ===
RESPONDIENDO = range(1)

# === Delegaciones de la CDMX ===
ALCALDIAS_CDMX = [
    "Álvaro Obregón", "Azcapotzalco", "Benito Juárez", "Coyoacán",
    "Cuajimalpa de Morelos", "Cuauhtémoc", "Gustavo A. Madero",
    "Iztacalco", "Iztapalapa", "La Magdalena Contreras", "Miguel Hidalgo",
    "Milpa Alta", "Tláhuac", "Tlalpan", "Venustiano Carranza", "Xochimilco"
]

# === Definir las preguntas y tipo ===
PREGUNTAS = [
    {"texto": "¿Has aceptado solicitudes de personas que no conoces en redes sociales?", "tipo": "si_no"},
    {"texto": "¿Has compartido tu número, dirección o datos personales en redes?", "tipo": "si_no"},
    {"texto": "¿Cambias tu contraseña de manera seguida?", "tipo": "si_no"},
    {"texto": "¿Has hecho clic en enlaces externos desde tus redes sociales?", "tipo": "si_no"},
    {"texto": "¿Tu perfil está configurado como público?", "tipo": "si_no"},
    {"texto": "¿Usas la misma contraseña en varias plataformas?", "tipo": "si_no"},
    {"texto": "¿Tienes activada la verificación en dos pasos (2FA)?", "tipo": "si_no"},
    {"texto": "¿Desde qué alcaldía accedes normalmente?", "tipo": "opciones", "opciones": ALCALDIAS_CDMX},
    {"texto": "¿Con qué tipo de dispositivo te conectas más seguido?", "tipo": "opciones", "opciones": ["Laptop", "Smartphone", "Tablet", "PC de escritorio", "Otro"]},
    {"texto": "¿Con qué frecuencia cambias tu contraseña?", "tipo": "opciones", "opciones": ["Mensual", "Bimestral", "Trimestral", "Semestral", "Anual", "Nunca"]}
]

user_data_temp = {}

# === Mensaje inicial con descripción ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data_temp[user_id] = {"telegram_id": user_id, "respuestas": [], "pregunta_idx": 0}

    keyboard = [[InlineKeyboardButton("🟢 Comenzar", callback_data="comenzar_test")]]
    markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            "👋 *¡Bienvenido/a al Test de Seguridad en Redes Sociales!*\n\n"
            "¿Alguna vez te has preguntado qué tan expuesto estás en internet? Este test está diseñado para ayudarte a reflexionar sobre tus hábitos digitales y detectar posibles riesgos en el uso de tus redes sociales.\n\n"
            "A través de unas cuantas preguntas simples, podrás identificar si estás tomando medidas adecuadas para proteger tu identidad y tu privacidad en línea.\n\n"
            "🔐 *Aviso de privacidad:* Tus respuestas son confidenciales y serán usadas únicamente para fines educativos y de análisis de riesgo. No se comparten con terceros.\n\n"
            "💡 Al finalizar, recibirás un resumen con tus respuestas que puede ayudarte a tomar mejores decisiones.\n\n"
            "Cuando estés listo/a, presiona el botón para comenzar 👇"
        ),
        parse_mode="Markdown",
        reply_markup=markup
    )
    return RESPONDIENDO

# === Comienzo del test ===
async def iniciar_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data_temp[user_id] = {
        "telegram_id": user_id,
        "respuestas": [],
        "pregunta_idx": 0
    }
    await enviar_pregunta(update, context)
    return RESPONDIENDO

# === Enviar preguntas según el tipo ===
async def enviar_pregunta(update_or_query, context):
    user_id = update_or_query.effective_user.id
    idx = user_data_temp[user_id]["pregunta_idx"]

    if idx >= len(PREGUNTAS):
        respuestas = user_data_temp[user_id]["respuestas"]
        total = sum(1 for r in respuestas[:7] if r["respuesta"] == "Sí")
        if total <= 2:
            nivel_riesgo= "🟢 Bajo riesgo"
        elif total <= 4:
            nivel_riesgo = "🟡 Riesgo medio"
        else:
            nivel_riesgo = "🔴 Alto riesgo"

        user_data_temp[user_id]["nivel_riesgo"] = nivel_riesgo
        coleccion.insert_one(user_data_temp[user_id])
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            nombre_pdf = temp_pdf.name
            nivel_num, texto_riesgo, color_riesgo = generar_nivel_riesgo(respuestas)
            crear_reporte_pdf(nombre_pdf, respuestas, nivel_num, texto_riesgo, color_riesgo)

        with open(nombre_pdf, "rb") as pdf_file:
            await context.bot.send_document(
                chat_id=user_id,
                document=pdf_file,
                caption="📄 Aquí tienes tu reporte de seguridad digital"
            )
        os.remove(nombre_pdf)

        pdf_files = [
            "media/infografia.pdf",
            "media/mapa_instituciones.pdf",
            "media/marco_legal.pdf"
        ]
        
        for pdf_file in pdf_files:
            if os.path.exists(pdf_file): # Check if file exists
                with open(pdf_file, "rb") as file:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=file,
                        caption="📄 Recursos que te pueden ayudar en caso riesgo"
                    )
            else:
                print(f"Warning: File not found at {pdf_file}")


        keyboard_satisfaccion = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐️ Muy satisfecho", callback_data="satisfaccion_muy_satisfecho")],
            [InlineKeyboardButton("😐 Neutral", callback_data="satisfaccion_neutral")],
            [InlineKeyboardButton("❌ Muy Insatisfecho", callback_data="satisfaccion_muy_insatisfecho")]
        ])
        await context.bot.send_message(
            chat_id=user_id,
            text="¿Qué tan satisfecho/a estás con el test?",
            reply_markup=keyboard_satisfaccion,
            parse_mode=ParseMode.MARKDOWN
        )
        
        mensaje_final = (
            f"🎉 ¡Gracias por responder! Has terminado el test.\n\n"
            f"🔎 *Resultado:* {nivel_riesgo}\n\n"
            f"⚠️ *Recomendación:* Si no reconoces alguno de estos accesos o te preocupa tu seguridad,\n"
            f"te sugerimos cambiar tu contraseña y revisar tu actividad en redes sociales."
        )

        keyboard = [[InlineKeyboardButton("🔄 Volver a empezar", callback_data="comenzar_test")]]
        markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id,
            text=mensaje_final + "\n\n¿Quieres repetir el test?",
            reply_markup=markup,
            parse_mode="Markdown"
        )

        del user_data_temp[user_id]
        return ConversationHandler.END

    pregunta = PREGUNTAS[idx]
    texto = pregunta["texto"]
    if pregunta["tipo"] == "si_no":
        keyboard = [[InlineKeyboardButton("Sí", callback_data="Sí"), InlineKeyboardButton("No", callback_data="No")]]
        markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user_id, text=texto, reply_markup=markup)
    elif pregunta["tipo"] == "opciones":
        keyboard = [[InlineKeyboardButton(op, callback_data=op)] for op in pregunta["opciones"]]
        markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user_id, text=texto, reply_markup=markup)

# === Procesar respuestas por botón ===
async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "comenzar_test":
        return await iniciar_test(update, context)
    elif query.data.startswith("satisfaccion"):
        nivel = query.data.split("_", 1)[1].replace("_", " ").capitalize()
        coleccion.update_one(
            {"telegram_id": user_id},
            {"$set": {"satisfaccion": nivel}},
            upsert=True
        )
        await query.edit_message_text(
            text=f"✅ *Gracias por tu opinión:* {nivel}",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    idx = user_data_temp[user_id]["pregunta_idx"]
    pregunta = PREGUNTAS[idx]["texto"]
    respuesta = query.data
    user_data_temp[user_id]["respuestas"].append({"pregunta": pregunta, "respuesta": respuesta})

    new_text = f"{pregunta}\n\n✅ Respuesta: {respuesta}"
    await query.edit_message_text(text=new_text)
    user_data_temp[user_id]["pregunta_idx"] += 1
    await enviar_pregunta(update, context)
    return RESPONDIENDO

# === Cancelar ===
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Has cancelado la conversación.")
    user_id = update.effective_user.id
    if user_id in user_data_temp:
        del user_data_temp[user_id]
    return ConversationHandler.END

# === Flask Application Setup ===
app_flask = Flask(__name__)
application = Application.builder().token(TELEGRAM_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        RESPONDIENDO: [
            CallbackQueryHandler(manejar_callback)
        ]
    },
    fallbacks=[CommandHandler('cancelar', cancelar)]
)

application.add_handler(conv_handler)

@app_flask.route('/')
def index():
    return "Bot is running!"

@app_flask.route('/telegram', methods=['POST'])
async def telegram_webhook():
    update_json = request.get_json()
    if not update_json:
        return jsonify({"status": "no data"}), 200

    update = Update.de_json(update_json, application.bot)
    await application.process_update(update)
    return jsonify({"status": "ok"}), 200

# === Main execution for Render ===
if __name__ == '__main__':
    # Set up the webhook on Telegram when the app starts
    print("Setting up webhook...")
    try:
        # This will set the webhook URL for your bot
        # Make sure WEBHOOK_URL is set correctly in your environment variables on Render
        application.bot.set_webhook(url=WEBHOOK_URL).wait()
        print(f"Webhook set to: {WEBHOOK_URL}")
    except Exception as e:
        print(f"Error setting webhook: {e}")
        # In a production environment, you might want to log this error
        # and consider a retry mechanism or alert system.

    port = int(os.environ.get("PORT", 5000))
    app_flask.run(host="0.0.0.0", port=port)
