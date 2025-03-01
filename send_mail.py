import time
import smtplib
import sys
from datetime import datetime
import os
import csv

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
    destinatarios = []
    if os.path.exists(MAILS_CSV):
        with open(MAILS_CSV, "r") as file:
            reader = csv.reader(file)
            next(reader)  # Saltar cabecera
            for row in reader:
                if len(row) == 2 and row[1] == "1":
                    destinatarios.append(row[0].strip().replace('"', ''))
    return destinatarios

def cargar_tolerancias():
    """Carga las tolerancias de cada central desde monitoreando.csv."""
    tolerancias = {}
    if os.path.exists(MONITOREANDO_CSV):
        with open(MONITOREANDO_CSV, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) >= 2:
                    nombre = row[0].strip()
                    tolerancia = int(row[1].strip())
                    tolerancias[nombre] = tolerancia
    return tolerancias

def cargar_historial():
    """Carga el historial de envíos recientes para evitar spam."""
    historial = {}
    if os.path.exists(LAST_EMAIL_TIME_FILE):
        with open(LAST_EMAIL_TIME_FILE, "r") as file:
            for line in file:
                partes = line.strip().split()
                if len(partes) == 2:
                    historial[partes[0]] = float(partes[1])
    return historial

def actualizar_historial(historial):
    """Actualiza el historial de envíos recientes."""
    with open(LAST_EMAIL_TIME_FILE, "w") as file:
        for servidor, timestamp in historial.items():
            file.write(f"{servidor} {timestamp}\n")

def puede_enviar_correo(servidor, historial):
    """Verifica si han pasado al menos 1 hora desde el último envío para este servidor."""
    UNA_HORA = 3600
    tiempo_actual = time.time()
    if servidor in historial and (tiempo_actual - historial[servidor]) < UNA_HORA:
        return False
    historial[servidor] = tiempo_actual
    return True

def sendmail(servidores_caidos):
    """Envía un solo correo con la lista de servidores caídos."""
    subject = "🚨 Alerta: Fallo en la red"
    message = "Los siguientes servidores han superado la tolerancia sin responder:\n\n"
    for servidor, tiempo in servidores_caidos.items():
        message += f"🔴 {servidor} - {tiempo} minutos sin respuesta\n"

    message_formatted = f'Subject: {subject}\n\n{message}'
    destinatarios = cargar_destinatarios()

    if not destinatarios:
        print(" No hay destinatarios activos en el CSV.")
        return

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(MAIL_USER, MAIL_PASSWORD)
            for destinatario in destinatarios:
                server.sendmail(MAIL_USER, destinatario, message_formatted)
                with open(MAIL_LOG_FILE, "a") as log_file:
                    log_file.write(f"{datetime.now().strftime('%d/%m/%y %H:%M:%S')} {destinatario} {message}\n")
        print(" Correo enviado a destinatarios activos.")
    except Exception as e:
        print(f" Error al enviar el correo: {e}")
        with open(ERROR_LOG_FILE, "a") as error_file:
            error_file.write(f"{datetime.now().strftime('%d/%m/%y %H:%M:%S')} Error al enviar el correo: {e}\n")

if len(sys.argv) < 2:
    print("Uso: python send_mail.py 'servidor1:tiempo,servidor2:tiempo,...'")
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
        if tiempo_caido >= tolerancia and puede_enviar_correo(nombre, historial_envios):
            servidores_para_enviar[nombre] = tiempo_caido

if servidores_para_enviar:
    sendmail(servidores_para_enviar)
    actualizar_historial(historial_envios)
else:
    print(" No se enviará correo, todos los servidores ya fueron notificados recientemente o no superaron la tolerancia.")
