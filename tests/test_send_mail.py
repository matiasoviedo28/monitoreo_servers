import os
import sys
import tempfile

# Asegurar que se pueda importar send_mail agregando la raíz del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import send_mail


def test_cargar_destinatarios():
    # Crear un archivo CSV temporal con destinatarios
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        tmp.write("email,activo\n")
        tmp.write("a@example.com,1\n")
        tmp.write("b@example.com,0\n")
        tmp.write("c@example.com,1\n")
        csv_path = tmp.name

    original_path = send_mail.MAILS_CSV
    send_mail.MAILS_CSV = csv_path
    try:
        destinatarios = send_mail.cargar_destinatarios()
        assert destinatarios == ["a@example.com", "c@example.com"]
    finally:
        send_mail.MAILS_CSV = original_path
        os.remove(csv_path)
