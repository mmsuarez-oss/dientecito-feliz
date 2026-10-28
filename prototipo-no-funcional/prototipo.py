"""Prototipo no funcional de Clínicas Odontológicas (Flask + HTML).

No es el sistema: es un prototipo no funcional para mostrar las pantallas y el
flujo de trabajo. Todo vive en memoria (listas y diccionarios de Python), sin
SQL ni SQLite, y se pierde al reiniciar. La página no lleva JavaScript: todo lo
que decide algo está en Python.

Ejecutar:  python prototipo.py
"""
import itertools
from datetime import date

from flask import (Flask, Response, flash, redirect, render_template, request,
                   session, url_for)

# Cuentas de ejemplo con CIF ficticios: dos por cada tipo y una de la Facultad
CUENTAS = {"00000001": ("Dra. Grace Mendoza", "profesor"),
           "00000004": ("Dr. Gustavo Rivas", "profesor"),
           "00000002": ("Grace Alvarado", "estudiante"),
           "00000005": ("Gabriel Espinoza", "estudiante"),
           "00000007": ("Gina Saavedra", "admin")}
CLAVE_EJEMPLO = "uam2026"  # en el sistema real la clave va cifrada en la base de datos
ROLES = {"profesor": "Profesor", "estudiante": "Estudiante", "admin": "Facultad"}
# Pestanas de cada rol: (nombre, endpoint)
MENUS = {"estudiante": [("Inicio", "menu"), ("Mis pacientes", "pacientes"), ("Mis citas", "citas"), ("Salas", "salas")],
         # El profesor solo revisa: no registra pacientes, citas ni tratamientos
         "profesor": [("Inicio", "menu"), ("Pacientes", "pacientes"), ("Citas", "citas"), ("Salas", "salas")],
         "admin": [("Inicio", "menu"), ("Pacientes", "pacientes"), ("Citas", "citas"), ("Salas", "salas")]}
QUE_HACE = {"estudiante": ["Registrar a sus pacientes y la razón por la que vienen",
                           "Agendar sus citas con la razón de cada cita",
                           "Llenar el odontograma y pedir la revisión del profesor",
                           "Firmar e imprimir el consentimiento del paciente"],
            "profesor": ["Revisar y aprobar lo que registra cada estudiante",
                         "Ver el historial de qué le hizo cada estudiante a cada paciente",
                         "No registra pacientes, citas ni tratamientos"],
            "admin": ["Crear las cuentas y administrar las salas",
                      "Cambiar un paciente de estudiante archivando el trabajo del anterior"]}
EN_PROCESO = {"Odontograma": "Foto presencial y odontograma digital",
              "Tratamientos y cobros": "Procedimientos, tarifario y abonos",
              "Inventario": "Materiales de la clínica",
              "Bitácora": "Registro de lo que hace cada usuario"}

app = Flask(__name__)
app.secret_key = "prototipo-clinicas-odontologicas"  # firma la cookie que recuerda quien entro

# Datos de esta corrida del prototipo (se pierden al reiniciar)
PACIENTES = []  # nombre, cedula, telefono, razon, estudiante (CIF), aprobado, firma, trabajo
CITAS = []      # paciente_id, fecha, hora, sala, razon
SALAS = [{"nombre": "Sala 1", "disponible": True},
         {"nombre": "Sala 2", "disponible": True},
         {"nombre": "Sala 3", "disponible": False}]
_id_paciente = itertools.count(1)
_id_cita = itertools.count(1)


def hoy():
    return date.today().isoformat()

def quien():
    """CIF, rol y nombre de quien entro; None si no hay sesion."""
    cif = session.get("cif")
    return (cif, *CUENTAS[cif]) if cif in CUENTAS else None

def comun():
    """Datos que necesita la plantilla base en todas las paginas."""
    cif, nombre, rol = quien()
    return {"cif": cif, "nombre": nombre, "rol": ROLES[rol], "es_rol": rol, "pestanas": MENUS[rol]}

def paciente(pid):
    """El paciente, solo si el usuario puede verlo: cada estudiante ve unicamente los suyos."""
    cif, _, rol = quien()
    p = next((x for x in PACIENTES if x["id"] == pid), None)
    if p and rol == "estudiante" and p["estudiante"] != cif:
        return None
    return p

def mis_pacientes():
    cif, _, rol = quien()
    return [p for p in PACIENTES if rol != "estudiante" or p["estudiante"] == cif]

def nombre_de(cif):
    return CUENTAS[cif][0] if cif in CUENTAS else "sin asignar"


@app.before_request
def exigir_sesion():
    if request.endpoint not in ("entrar", "static") and quien() is None:
        return redirect(url_for("entrar"))


@app.route("/", methods=["GET", "POST"])
def entrar():
    datos = {"cif": "", "error_cif": "", "error_clave": "", "aviso": ""}
    if request.method == "POST":
        if request.form.get("accion") != "entrar":  # las opciones que todavia no estan hechas
            datos["aviso"] = "Esta opción todavía está en proceso."
            return render_template("entrar.html", **datos)
        cif = request.form.get("cif", "").strip()
        clave = request.form.get("clave", "")
        datos["cif"] = cif
        if not cif:
            datos["error_cif"] = "Escriba su CIF."
        if not clave:
            datos["error_clave"] = "Escriba su contraseña."
        if cif and clave:
            if cif in CUENTAS and clave == CLAVE_EJEMPLO:
                session["cif"] = cif
                return redirect(url_for("menu"))
            datos["aviso"] = "CIF o contraseña incorrectos."
    return render_template("entrar.html", **datos)


@app.route("/menu")
def menu():
    return render_template("menu.html", **comun(), que_hace=QUE_HACE[quien()[2]],
                           en_proceso=list(EN_PROCESO.items()))


@app.route("/pacientes", methods=["GET", "POST"])
def pacientes():
    cif, _, rol = quien()
    form = {}
    if request.method == "POST":
        accion = request.form.get("accion")
        if accion == "registrar" and rol == "estudiante":
            form = {c: request.form.get(c, "").strip() for c in ("nombre", "cedula", "telefono")}
            if not form["nombre"] or not form["cedula"]:
                flash("El nombre y la cédula del paciente son obligatorios.", "error")
            elif any(p["cedula"] == form["cedula"] for p in PACIENTES):
                flash("Ya existe un paciente con esa cédula.", "error")
            else:
                pid = next(_id_paciente)
                PACIENTES.append({"id": pid, **form, "razon": "", "estudiante": cif, "aprobado": False, "firma": "",
                                  "trabajo": [{"estudiante": cif, "desde": hoy(), "hasta": None, "resumen": ""}]})
                # Paso siguiente: la razon por la que esta el paciente
                return redirect(url_for("razon", pid=pid))
        elif accion == "aprobar" and rol == "profesor":  # el profesor solo revisa
            p = paciente(request.form.get("id", type=int))
            if p:
                p["aprobado"] = request.form.get("aprobado") == "1"
                flash("Paciente aprobado." if p["aprobado"] else "Aprobación retirada.", "ok")
    return render_template("pacientes.html", **comun(), pacientes=mis_pacientes(), form=form, nombre_de=nombre_de)


@app.route("/pacientes/<int:pid>/razon", methods=["GET", "POST"])
def razon(pid):
    """Paso 2 del registro: por qué está el paciente y, si ya se sabe, su primera cita."""
    p = paciente(pid)
    if not p or quien()[2] != "estudiante":
        return redirect(url_for("pacientes"))
    if request.method == "POST":
        razon = request.form.get("razon", "").strip()
        fecha, hora = request.form.get("fecha", ""), request.form.get("hora", "")
        if not razon:
            flash("Escriba la razón por la que viene el paciente.", "error")
        else:
            p["razon"] = razon
            if fecha and hora:
                CITAS.append({"id": next(_id_cita), "paciente_id": pid, "fecha": fecha, "hora": hora,
                              "sala": request.form.get("sala", ""),
                              "razon": request.form.get("razon_cita", "").strip() or razon})
                flash("Razón guardada y cita agendada.", "ok")
            else:
                flash("Razón de la consulta guardada.", "ok")
            return redirect(url_for("expediente", pid=pid))
    return render_template("razon.html", **comun(), p=p, hoy=hoy(), salas=SALAS)


@app.route("/pacientes/<int:pid>")
def expediente(pid):
    p = paciente(pid)
    if not p:
        return redirect(url_for("pacientes"))
    return render_template("expediente.html", **comun(), p=p, nombre_de=nombre_de,
                           citas=[c for c in CITAS if c["paciente_id"] == pid])


@app.route("/pacientes/<int:pid>/traspaso", methods=["GET", "POST"])
def traspaso(pid):
    """Cambiar de estudiante: el trabajo del anterior se archiva con el resumen de lo que le hizo."""
    p = paciente(pid)
    if not p or quien()[2] != "admin":
        return redirect(url_for("pacientes"))
    estudiantes = [(c, n) for c, (n, r) in CUENTAS.items() if r == "estudiante"]
    if request.method == "POST":
        nuevo = request.form.get("estudiante", "")
        resumen = request.form.get("resumen", "").strip()
        if nuevo not in dict(estudiantes) or nuevo == p["estudiante"]:
            flash("Elija el estudiante que recibe al paciente.", "error")
        elif not resumen:
            flash("Escriba qué se le hizo al paciente y qué trabajó el estudiante anterior.", "error")
        else:
            abierta = next((t for t in p["trabajo"] if t["hasta"] is None), None)
            if abierta:
                abierta.update(hasta=hoy(), resumen=resumen)
            p["trabajo"].append({"estudiante": nuevo, "desde": hoy(), "hasta": None, "resumen": ""})
            p["estudiante"] = nuevo
            flash(f"{p['nombre']} pasó a {nombre_de(nuevo)}. El trabajo anterior quedó archivado.", "ok")
            return redirect(url_for("expediente", pid=pid))
    return render_template("traspaso.html", **comun(), p=p, estudiantes=estudiantes, nombre_de=nombre_de)


@app.route("/pacientes/<int:pid>/consentimiento", methods=["GET", "POST"])
def consentimiento(pid):
    """Consentimiento del paciente con su firma, listo para imprimir."""
    p = paciente(pid)
    if not p:
        return redirect(url_for("pacientes"))
    if request.method == "POST" and quien()[2] == "estudiante":
        firma = request.form.get("firma", "").strip()
        if not firma:
            flash("Falta la firma del paciente.", "error")
        else:
            p["firma"] = firma
            p["firma_fecha"] = hoy()
            flash("Consentimiento firmado. Ya se puede imprimir.", "ok")
        return redirect(url_for("consentimiento", pid=pid))
    return render_template("consentimiento.html", **comun(), p=p, nombre_de=nombre_de)


@app.route("/citas", methods=["GET", "POST"])
def citas():
    cif, _, rol = quien()
    if request.method == "POST" and rol == "estudiante":
        p = paciente(request.form.get("paciente_id", type=int))
        f = {c: request.form.get(c, "").strip() for c in ("fecha", "hora", "sala", "razon")}
        if not (p and f["fecha"] and f["hora"] and f["razon"]):
            flash("Elige paciente, fecha, hora y la razón de la cita.", "error")
        elif f["fecha"] < hoy():
            flash("No se pueden agendar citas en fechas pasadas.", "error")
        elif any(c["sala"] == f["sala"] and c["fecha"] == f["fecha"] and c["hora"] == f["hora"] for c in CITAS if f["sala"]):
            flash("Esa sala ya está ocupada a esa hora.", "error")
        else:
            CITAS.append({"id": next(_id_cita), "paciente_id": p["id"], **f})
            flash("Cita agendada.", "ok")
        return redirect(url_for("citas"))
    mios = {p["id"]: p for p in mis_pacientes()}
    return render_template("citas.html", **comun(), hoy=hoy(), salas=SALAS, pacientes=list(mios.values()),
                           citas=[c for c in CITAS if c["paciente_id"] in mios], mios=mios, nombre_de=nombre_de)


@app.route("/salas", methods=["GET", "POST"])
def salas():
    """Plano de la clínica: cada sala con un check si está disponible o una X si no."""
    if request.method == "POST" and quien()[2] == "admin":
        if request.form.get("accion") == "agregar":
            nombre = request.form.get("nombre", "").strip()
            if not nombre:
                flash("Escriba el nombre de la sala.", "error")
            elif any(s["nombre"].lower() == nombre.lower() for s in SALAS):
                flash("Ya existe una sala con ese nombre.", "error")
            else:
                SALAS.append({"nombre": nombre, "disponible": True})
                flash(f"{nombre} agregada.", "ok")
        else:
            i = request.form.get("sala", type=int)
            if i is not None and 0 <= i < len(SALAS):
                SALAS[i]["disponible"] = not SALAS[i]["disponible"]
        return redirect(url_for("salas"))
    return render_template("salas.html", **comun(), salas=SALAS)


@app.route("/pacientes/<int:pid>/expediente.txt")
def expediente_txt(pid):
    # El estudiante a cargo y el profesor que revisa pueden descargar el expediente
    p = paciente(pid)
    if not p:
        return redirect(url_for("pacientes"))
    trabajo = "\n".join(f"  - {nombre_de(t['estudiante'])}: {t['desde']} a {t['hasta'] or 'hoy'}. "
                        f"{t['resumen'] or 'sin resumen'}" for t in p["trabajo"])
    contenido = (f"Expediente clínico - Clínicas Odontológicas\n\n"
                 f"Nombre: {p['nombre']}\nCédula: {p['cedula']}\nTeléfono: {p['telefono']}\n"
                 f"Razón de la consulta: {p['razon']}\n"
                 f"Estudiante a cargo: {nombre_de(p['estudiante'])}\n"
                 f"Estado: {'Aprobado' if p['aprobado'] else 'Pendiente de aprobación'}\n"
                 f"Consentimiento: {'firmado por ' + p['firma'] if p['firma'] else 'sin firmar'}\n\n"
                 f"Trabajo por estudiante:\n{trabajo}\n")
    return Response(contenido, mimetype="text/plain",
                    headers={"Content-Disposition": f"attachment; filename=expediente_{p['cedula']}.txt"})


@app.route("/salir")
def salir():
    session.clear()
    return redirect(url_for("entrar"))


if __name__ == "__main__":
    print("\n  Prototipo no funcional de Clínicas Odontológicas:  http://localhost:5001")
    print("  Cuentas de ejemplo (CIF ficticios), clave uam2026:")
    for cif, (nombre, rol) in CUENTAS.items():
        print(f"    {cif}  {nombre:20} {ROLES[rol]}")
    print()
    app.run(port=5001)
