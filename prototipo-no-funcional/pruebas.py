"""Pruebas del prototipo no funcional. Ejecutar:  python pruebas.py"""
import sys

import prototipo as m

fallos = []

def caso(descripcion, condicion):
    print(("  OK     " if condicion else "  FALLO  ") + descripcion)
    if not condicion:
        fallos.append(descripcion)

def cliente(cif):
    c = m.app.test_client()
    c.post("/", data={"accion": "entrar", "cif": cif, "clave": "uam2026"})
    return c

def texto(r):
    return r.get_data(as_text=True)

grace, gabriel, profe, admin = cliente("00000002"), cliente("00000005"), cliente("00000001"), cliente("00000007")

print("Prototipo no funcional - pruebas\n")
caso("Sin sesion la pagina de pacientes manda a la entrada",
     m.app.test_client().get("/pacientes").headers["Location"].endswith("/"))
caso("El nombre del usuario sale en la cabecera, no solo el rol", "Grace Alvarado" in texto(grace.get("/menu")))

grace.post("/pacientes", data={"accion": "registrar", "nombre": "Luis Pérez", "cedula": "T-100", "telefono": "88880000"})
pid = m.PACIENTES[0]["id"]
caso("Al registrar, el paso siguiente pide la razon del paciente",
     "por qué está el paciente" in texto(grace.get(f"/pacientes/{pid}/razon")))
grace.post(f"/pacientes/{pid}/razon", data={"razon": ""})
caso("La razon es obligatoria", m.PACIENTES[0]["razon"] == "")
grace.post(f"/pacientes/{pid}/razon", data={"razon": "Dolor en la muela 36", "fecha": m.hoy(),
                                            "hora": "09:00", "sala": "Sala 1", "razon_cita": "Valoración"})
caso("La razon sale al lado del nombre en la lista", "Dolor en la muela 36" in texto(grace.get("/pacientes")))
caso("La razon de la cita y la del paciente salen en la pagina de citas",
     all(t in texto(grace.get("/citas")) for t in ("Valoración", "Dolor en la muela 36")))

caso("Cada estudiante ve solo sus pacientes", "Luis Pérez" not in texto(gabriel.get("/pacientes")))
caso("Cada estudiante ve solo sus citas", "Luis Pérez" not in texto(gabriel.get("/citas")))
caso("El profesor ve a todos los pacientes", "Luis Pérez" in texto(profe.get("/pacientes")))

caso("El profesor no registra pacientes", "accion\" value=\"registrar" not in texto(profe.get("/pacientes")))
profe.post("/pacientes", data={"accion": "registrar", "nombre": "X", "cedula": "T-999"})
caso("El profesor no puede registrar ni por la fuerza", len(m.PACIENTES) == 1)
caso("El profesor no agenda citas", "Agendar cita" not in texto(profe.get("/citas")))
profe.post("/pacientes", data={"accion": "aprobar", "id": pid, "aprobado": "1"})
caso("El profesor solo revisa: aprueba al paciente", m.PACIENTES[0]["aprobado"] is True)

grace.post(f"/pacientes/{pid}/consentimiento", data={"firma": "Luis Pérez"})
caso("El consentimiento se imprime con la firma del paciente",
     "Luis Pérez" in texto(grace.get(f"/pacientes/{pid}/consentimiento")) and m.PACIENTES[0]["firma"] == "Luis Pérez")

caso("Solo la administracion traspasa pacientes",
     grace.get(f"/pacientes/{pid}/traspaso").status_code == 302)
admin.post(f"/pacientes/{pid}/traspaso", data={"estudiante": "00000005", "resumen": ""})
caso("Al traspasar hay que decir que se le hizo al paciente", m.PACIENTES[0]["estudiante"] == "00000002")
admin.post(f"/pacientes/{pid}/traspaso", data={"estudiante": "00000005", "resumen": "Profilaxis y obturación del 36"})
archivado = [t for t in m.PACIENTES[0]["trabajo"] if t["hasta"]]
caso("Al cambiar de estudiante se archiva el trabajo del anterior con su resumen",
     m.PACIENTES[0]["estudiante"] == "00000005" and len(archivado) == 1
     and archivado[0]["resumen"] == "Profilaxis y obturación del 36")
caso("El historial muestra que le hizo cada estudiante",
     all(t in texto(gabriel.get(f"/pacientes/{pid}")) for t in ("Grace Alvarado", "Gabriel Espinoza",
                                                                "Profilaxis y obturación del 36")))
caso("El paciente ya no le sale al estudiante anterior", "Luis Pérez" not in texto(grace.get("/pacientes")))

plano = texto(admin.get("/salas")).split('class="plano-salas"')[1].split("plano-pasillo")[0]
caso("El plano marca las salas disponibles con un check y las ocupadas con una X",
     plano.count("✓") == 2 and plano.count("✗") == 1)
admin.post("/salas", data={"sala": "0"})
caso("La administracion cambia la disponibilidad de una sala", m.SALAS[0]["disponible"] is False)
caso("El estudiante no administra las salas", "Agregar sala" not in texto(grace.get("/salas")))

print(f"\n{len(sys.argv) and ''}{'Todo correcto.' if not fallos else str(len(fallos)) + ' fallos.'}")
sys.exit(1 if fallos else 0)
