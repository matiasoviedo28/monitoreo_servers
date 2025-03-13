import time
import smtplib
import sys
from datetime import datetime
import os
import csv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Variables de correo
MAIL_USER = "mail_de_envios_de_alertas@gmail.com"
MAIL_PASSWORD = "password_segura"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Archivos de configuración
MAILS_CSV = "/home/ubuntu/COOP/mails.csv"
MONITOREANDO_CSV = "/home/ubuntu/COOP/monitoreando.csv"
LAST_EMAIL_TIME_FILE = "/home/ubuntu/COOP/last_email_time.txt"
MAIL_LOG_FILE = "/home/ubuntu/COOP/mail_log.txt"
ERROR_LOG_FILE = "/home/ubuntu/COOP/error_log.txt"

def cargar_destinatarios():
    """Carga los correos electrónicos activos desde el archivo CSV."""
    print("📥 Cargando destinatarios desde:", MAILS_CSV)
    destinatarios = []
    if os.path.exists(MAILS_CSV):
        with open(MAILS_CSV, "r") as file:
            reader = csv.reader(file)
            next(reader)  # Saltar cabecera
            for row in reader:
                if len(row) == 2 and row[1] == "1":
                    destinatarios.append(row[0].strip().replace('"', ''))
    print("📧 Destinatarios cargados:", destinatarios)
    return destinatarios

def cargar_tolerancias():
    """Carga las tolerancias de cada central desde monitoreando.csv."""
    print("📥 Cargando tolerancias desde:", MONITOREANDO_CSV)
    tolerancias = {}
    if os.path.exists(MONITOREANDO_CSV):
        with open(MONITOREANDO_CSV, "r") as file:
            reader = csv.reader(file)
            next(reader)  # Saltar cabecera
            for row in reader:
                if len(row) >= 3:  # Asegurar que haya 3 columnas
                    nombre = row[0].strip().replace('"', '')  # Quitar comillas
                    tolerancia = int(row[2].strip())  # Usar tercera columna
                    tolerancias[nombre] = tolerancia
                    print("✅ Cargado:", nombre, "->", tolerancia)
    return tolerancias

def cargar_historial():
    """Carga el historial de envíos recientes para evitar spam."""
    print("📥 Cargando historial de envíos desde:", LAST_EMAIL_TIME_FILE)
    historial = {}
    if not os.path.exists(LAST_EMAIL_TIME_FILE):  
        open(LAST_EMAIL_TIME_FILE, "w").close()  # Crear archivo vacío si no existe
    
    with open(LAST_EMAIL_TIME_FILE, "r") as file:
        for line in file:
            partes = line.strip().split()
            if len(partes) == 2:
                historial[partes[0]] = float(partes[1])
    print("📄 Historial cargado:", historial)
    return historial

def actualizar_historial(historial):
    """Actualiza el historial de envíos recientes."""
    print("📝 Actualizando historial con:", historial)
    with open(LAST_EMAIL_TIME_FILE, "w") as file:
        for servidor, timestamp in historial.items():
            line = f"{servidor} {timestamp}\n"
            print("✍ Escribiendo en historial:", line.strip())
            file.write(line)

def puede_enviar_correo(servidor, historial):
    """Verifica si han pasado al menos 1 hora desde el último envío para este servidor."""
    UNA_HORA = 3600
    tiempo_actual = time.time()
    
    if servidor in historial:
        diferencia = tiempo_actual - historial[servidor]
        print(f"⏳ {servidor} fue notificado hace {diferencia:.2f} segundos.")
        if diferencia < UNA_HORA:
            print(f"🚫 {servidor} fue notificado recientemente. No se enviará correo.")
            return False
    
    print(f"✅ {servidor} puede ser notificado.")
    historial[servidor] = tiempo_actual
    return True

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def sendmail(servidores_caidos):
    """Envía un solo correo con la lista de servidores caídos."""
    print(f"📧 Enviando correo para: {servidores_caidos}")

    subject = "Alerta: Fallo en la red"
    message = "Los siguientes servidores han superado la tolerancia sin responder:\n\n"
    
    for servidor, tiempo in servidores_caidos.items():
        message += f"🔴 {servidor} - {tiempo} minutos sin respuesta\n"  # El emoji sigue aquí

    destinatarios = cargar_destinatarios()

    if not destinatarios:
        print("❌ No hay destinatarios activos en el CSV.")
        return

    # Configurar el mensaje con codificación UTF-8
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = MAIL_USER
    msg["To"] = ", ".join(destinatarios)
    msg.attach(MIMEText(message, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(MAIL_USER, MAIL_PASSWORD)
            for destinatario in destinatarios:
                server.sendmail(MAIL_USER, destinatario, msg.as_string())
                with open(MAIL_LOG_FILE, "a") as log_file:
                    log_file.write(f"{datetime.now().strftime('%d/%m/%y %H:%M:%S')} {destinatario} {message}\n")
        print("✅ Correo enviado con éxito.")
    except Exception as e:
        print(f"❌ Error al enviar el correo: {e}")
        with open(ERROR_LOG_FILE, "a") as error_file:
            error_file.write(f"{datetime.now().strftime('%d/%m/%y %H:%M:%S')} Error al enviar el correo: {e}\n")



# ---------------------- PROCESO PRINCIPAL ----------------------
print("🚀 Iniciando send_mail.py...")

if len(sys.argv) < 2:
    print("⚠️ Uso: python send_mail.py 'servidor1:tiempo,servidor2:tiempo,...'")
    sys.exit(1)

servidores_input = sys.argv[1].split(',')
historial_envios = cargar_historial()
tolerancias = cargar_tolerancias()

# Filtrar servidores que superan su tolerancia y pueden enviar correo
servidores_para_enviar = {}

for entrada in servidores_input:
    partes = entrada.split(":")
    if len(partes) == 2:
        nombre, tiempo_caido = partes[0], int(partes[1])
        tolerancia = tolerancias.get(nombre, 5)  # Si no está en CSV, usa 5 min

        print(f"🔍 Evaluando {nombre}: Caído {tiempo_caido} min, Tolerancia {tolerancia}")

        if tiempo_caido >= tolerancia and puede_enviar_correo(nombre, historial_envios):
            print(f"✅ {nombre} superó la tolerancia y no ha sido notificado recientemente.")
            servidores_para_enviar[nombre] = tiempo_caido

if servidores_para_enviar:
    print("🔍 Servidores para enviar correo:", servidores_para_enviar)
    sendmail(servidores_para_enviar)
    actualizar_historial(historial_envios)
else:
    print("✅ No se enviará correo, todos los servidores ya fueron notificados recientemente o no superaron la tolerancia.")
