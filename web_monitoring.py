from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import os

app = Flask(__name__)
app.secret_key = "tu_clave_secreta"

STATUS_FILE = "server_status.txt"

def leer_estado():
    servidores = []
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            for line in f:
                datos = line.strip().split()
                if len(datos) >= 5:
                    servidores.append({
                        "nombre": datos[0],
                        "estado": datos[1],
                        "ultima_caida": datos[2] + " " + datos[3] if datos[2] != "-" else "-",
                        "ultima_recuperacion": datos[4] + " " + datos[5] if datos[4] != "-" else "-",
                        "tiempo_acumulado": datos[6] if len(datos) > 6 else "0",
                        "ping": datos[5] + " ms" if "ms" not in datos[5] else datos[5]
                    })
    return servidores

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/status")
def status():
    if "user" not in session:
        return jsonify({"error": "No autorizado"}), 403
    return jsonify(leer_estado())

@app.route("/stats")
def stats():
    if "user" not in session:
        return jsonify({"error": "No autorizado"}), 403

    estadisticas = []
    with open("server_status.txt", "r") as f:
        for linea in f:
            datos = linea.strip().split()
            if len(datos) >= 5:
                nombre = datos[0]
                tiempo_acumulado = datos[4]  # Tomamos el último valor como tiempo acumulado
                estadisticas.append({"nombre": nombre, "tiempo_acumulado": tiempo_acumulado})

    return jsonify({"estadisticas": estadisticas})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "password":
            session["user"] = username
            return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
