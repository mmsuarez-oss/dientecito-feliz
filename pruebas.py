"""Pruebas automaticas de Clínicas Odontológicas (plan de pruebas, fase 6).

Ejecutar:   python pruebas.py
Usa una base de datos temporal: no toca dientecito.db ni las fotos reales.
Cada caso tiene un codigo (CP-xx) que coincide con docs/plan-de-pruebas.md.
"""
import io
import re
import sqlite3
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

import app as m

TEMPORAL = Path(tempfile.mkdtemp())
m.DB, m.FOTOS, m.RESPALDOS = TEMPORAL / "prueba.db", TEMPORAL / "fotos", TEMPORAL / "respaldos"
fallos = []

@contextmanager
def caso(codigo, descripcion):
    try:
        yield
        print(f"  OK     {codigo}  {descripcion}")
    except Exception as e:  # noqa: BLE001 - se reporta cualquier fallo del caso
        fallos.append(codigo)
        print(f"  FALLO  {codigo}  {descripcion}\n         {type(e).__name__}: {e}")

def cliente(usuario, clave="uam2026"):
    c = m.app.test_client()
    r = c.post("/entrar", data={"usuario": usuario, "clave": clave})
    assert r.status_code == 302 and not r.location.endswith("/entrar"), f"no pudo entrar {usuario}"
    return c

def ok(r, *textos):
    assert r.status_code == 200, f"{r.request.path} respondió {r.status_code}"
    html = r.get_data(as_text=True)
    for t in textos:
        assert t in html, f"no aparece «{t}» en {r.request.path}"
    return html

def sql(consulta, args=()):
    con = sqlite3.connect(m.DB)
    fila = con.execute(consulta, args).fetchone()
    con.close()
    return fila[0] if fila else None

JPG = b"\xff\xd8\xff\xe0" + b"0" * 300

def foto():
    return io.BytesIO(JPG), "practica.jpg"

print("Clínicas Odontológicas - pruebas automáticas\n")
print("Migración")
with caso("CP-01", "Una base de versiones anteriores se actualiza sin perder datos"):
    viejo = sqlite3.connect(m.DB)
    viejo.executescript("""
        CREATE TABLE pacientes(id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, cedula TEXT UNIQUE NOT NULL,
                               telefono TEXT, nacimiento TEXT, alergias TEXT);
        CREATE TABLE citas(id INTEGER PRIMARY KEY, paciente_id INTEGER NOT NULL, fecha TEXT NOT NULL,
                           hora TEXT NOT NULL, motivo TEXT, estudiante TEXT);
        CREATE TABLE odontograma(paciente_id INTEGER, diente INTEGER, estado TEXT, PRIMARY KEY(paciente_id, diente));
        INSERT INTO pacientes(nombre, cedula) VALUES ('Paciente antiguo', 'V-1');
        INSERT INTO odontograma VALUES (1, 16, 'Caries');
        CREATE TABLE odonto_registros(id INTEGER PRIMARY KEY, paciente_id INTEGER NOT NULL, diente INTEGER NOT NULL,
            estado TEXT NOT NULL, descripcion TEXT, foto TEXT NOT NULL, fecha TEXT NOT NULL, usuario_id INTEGER,
            revision TEXT DEFAULT 'Pendiente', observacion TEXT, revisado_por INTEGER);
        INSERT INTO odonto_registros(paciente_id, diente, estado, foto, fecha, revision)
            VALUES (1, 16, 'Caries', 'antigua.jpg', '2026-09-20 10:00', 'Aprobado');""")
    viejo.commit()
    viejo.close()
    m.iniciar_db()
    assert sql("SELECT nombre FROM pacientes WHERE cedula = 'V-1'") == "Paciente antiguo"
    assert sql("SELECT estado FROM odontograma WHERE diente = 16") == "Caries"
    assert sql("SELECT COUNT(*) FROM usuarios") == 7 and sql("SELECT COUNT(*) FROM salas") == 3
    assert sql("SELECT estudiante_id FROM pacientes WHERE cedula = 'V-1'") is not None
    assert sql("SELECT COUNT(*) FROM asignaciones WHERE paciente_id = 1") == 1
    assert sql("SELECT estado || ' ' || foto FROM odonto_sesiones") == "Aprobado antigua.jpg"
    assert sql("SELECT sesion_id FROM odonto_registros") == sql("SELECT id FROM odonto_sesiones")

print("Acceso y permisos")
anonimo = m.app.test_client()
with caso("CP-02", "Sin sesión, toda página redirige a la pantalla de entrada"):
    for ruta in ("/", "/pacientes", "/citas", "/avisos", "/bitacora"):
        assert anonimo.get(ruta).location.endswith("/entrar"), ruta
with caso("CP-03", "Clave incorrecta es rechazada y queda en la bitácora"):
    ok(anonimo.post("/entrar", data={"usuario": "00000001", "clave": "mala"}, follow_redirects=True), "incorrectos")
    assert sql("SELECT COUNT(*) FROM bitacora WHERE accion = 'Intento de acceso fallido'") == 1
prof, est, serv, admin = cliente("00000001"), cliente("00000002"), cliente("00000003"), cliente("00000007")
prof2, est2, serv2 = cliente("00000004"), cliente("00000005"), cliente("00000006")
with caso("CP-04", "Cada rol ve solo sus pestañas (403 en las ajenas)"):
    for c, prohibidas in [(est, ["/usuarios", "/tarifario", "/inventario", "/avisos", "/bitacora", "/respaldo"]),
                          (serv, ["/pacientes", "/citas", "/usuarios", "/bitacora"]),
                          (prof, ["/avisos", "/usuarios", "/tarifario", "/inventario", "/respaldo",
                                  "/pacientes/nuevo"]),
                          (admin, ["/avisos", "/pacientes/nuevo"])]:
        for ruta in prohibidas:
            assert c.get(ruta).status_code == 403, ruta
    for c, permitidas in [(est, ["/", "/pacientes", "/citas", "/salas", "/cuenta"]),
                          (prof, ["/", "/pacientes", "/citas", "/salas", "/bitacora"]),
                          (admin, ["/usuarios", "/pacientes", "/citas", "/salas", "/tarifario", "/inventario",
                                   "/bitacora"]),
                          (serv, ["/avisos", "/salas", "/inventario", "/cuenta"])]:
        for ruta in permitidas:
            ok(c.get(ruta))
    assert admin.get("/respaldo").status_code == 200  # devuelve un .zip, no una pagina
with caso("CP-05", "La administración crea usuarios; se validan el CIF y la clave"):
    assert prof.post("/usuarios", data={"nombre": "X", "usuario": "nueva", "rol": "estudiante",
                                        "clave": "abc123"}).status_code == 403
    ok(admin.post("/usuarios", data={"nombre": "Grace Ruiz", "usuario": "Grace.Ruiz", "rol": "estudiante", "clave": "abc123"},
                  follow_redirects=True), "Cuenta grace.ruiz creada")
    ok(admin.post("/usuarios", data={"nombre": "X", "usuario": "a b", "rol": "estudiante", "clave": "abc123"},
                  follow_redirects=True), "sin espacios")
    ok(admin.post("/usuarios", data={"nombre": "X", "usuario": "corto", "rol": "estudiante", "clave": "123"},
                  follow_redirects=True), "al menos 6")
grace = cliente("grace.ruiz", "abc123")
grace_id = sql("SELECT id FROM usuarios WHERE usuario = 'grace.ruiz'")

print("Pacientes y expediente")
with caso("CP-06", "Registrar paciente; nombre y cédula obligatorios; cédula única"):
    ok(est.post("/pacientes/nuevo", data={"nombre": "", "cedula": ""}, follow_redirects=True), "obligatorios")
    ok(est.post("/pacientes/nuevo", data={"nombre": "Luis Pérez", "cedula": "T-100", "telefono": "8888 0000",
                                          "alergias": "Penicilina"}, follow_redirects=True),
       "¿por qué está el paciente?")  # paso 2: la razon de la consulta
    ok(est.post("/pacientes/nuevo", data={"nombre": "Otro", "cedula": "T-100"}, follow_redirects=True), "Ya existe")
pid = sql("SELECT id FROM pacientes WHERE cedula = 'T-100'")
with caso("CP-06b", "La razón de la consulta es obligatoria y sale al lado del nombre"):
    ok(est.post(f"/pacientes/{pid}/razon", data={"motivo_consulta": ""}, follow_redirects=True), "Escriba la razón")
    ok(est.post(f"/pacientes/{pid}/razon", data={"motivo_consulta": "Dolor en la muela 36"}, follow_redirects=True),
       "ALERGIAS: Penicilina", "Dolor en la muela 36")
    ok(est.get("/pacientes"), "Dolor en la muela 36")  # tambien en la lista, al lado del nombre
    assert sql("SELECT COUNT(*) FROM asignaciones WHERE paciente_id = ?", (pid,)) == 1
with caso("CP-07", "Un estudiante no ve ni abre pacientes de otro estudiante"):
    assert grace.get(f"/pacientes/{pid}").status_code == 404
    assert "Luis Pérez" not in grace.get("/pacientes").get_data(as_text=True)
    assert "Luis Pérez" not in est2.get("/pacientes").get_data(as_text=True)
    assert "Luis Pérez" not in est2.get("/citas").get_data(as_text=True)
    ok(prof.get("/pacientes"), "Luis Pérez")
with caso("CP-08", "Editar la historia clínica deja el antes y el después en la bitácora"):
    est.post(f"/pacientes/{pid}/editar", data={"nombre": "Luis Pérez", "cedula": "T-100", "telefono": "8888 0000",
                                               "alergias": "Penicilina, látex",
                                               "motivo_consulta": "Dolor en la muela 36"})
    detalle = sql("SELECT detalle FROM bitacora WHERE accion = 'Modificó datos del paciente' AND paciente_id = ?", (pid,))
    assert "«Penicilina» → «Penicilina, látex»" in detalle, detalle
with caso("CP-09", "Consentimiento: se guarda la firma dibujada"):
    ok(est.post(f"/pacientes/{pid}/firma", data={"firma": ""}, follow_redirects=True), "Falta la firma")
    ok(est.post(f"/pacientes/{pid}/firma", data={"firma": "data:image/png;base64,AAAA"}, follow_redirects=True), "Firmado el")
with caso("CP-10", "Solo el profesor aprueba pacientes; el profesor no registra ni edita"):
    assert est.post(f"/pacientes/{pid}/aprobacion", data={"aprobado": "1"}).status_code == 403
    ok(prof.post(f"/pacientes/{pid}/aprobacion", data={"aprobado": "1"}, follow_redirects=True),
       "Aprobado por Dra. Grace Mendoza")
    assert prof.post(f"/pacientes/{pid}/editar", data={"nombre": "X", "cedula": "T-100"}).status_code == 403
    assert prof.post(f"/pacientes/{pid}/tratamientos", data={"procedimiento": "X"}).status_code == 403
    assert prof.post(f"/pacientes/{pid}/firma", data={"firma": "x"}).status_code == 403
    assert prof.post("/citas", data={"paciente_id": pid}).status_code == 403

print("Odontograma: primero la foto presencial, después el digital")
with caso("CP-11", "Sin la foto del odontograma presencial no se puede llenar el digital"):
    html = ok(est.get(f"/pacientes/{pid}"), "1. Foto del odontograma presencial")
    assert "data-bloqueado" in html and "data-url" not in html
    assert est.post("/sesiones/999/diente", json={"diente": 16, "estado": "Caries"}).status_code == 404
    ok(est.post(f"/pacientes/{pid}/sesiones", data={"nota": "sin foto"}, follow_redirects=True), "Suba la foto")
    ok(est.post(f"/pacientes/{pid}/sesiones", data={"foto": (io.BytesIO(b"texto"), "x.jpg")}, follow_redirects=True),
       "Suba la foto")
    assert sql("SELECT COUNT(*) FROM odonto_sesiones WHERE paciente_id = ?", (pid,)) == 0
with caso("CP-12", "Con la foto se habilita el odontograma digital y se guardan los dientes"):
    html = ok(est.post(f"/pacientes/{pid}/sesiones", data={"foto": foto(), "nota": "Práctica de diagnóstico"},
                       follow_redirects=True), "Foto guardada", "data-url")
    sid = sql("SELECT MAX(id) FROM odonto_sesiones")
    archivo_foto = sql("SELECT foto FROM odonto_sesiones WHERE id = ?", (sid,))
    assert est.get(f"/fotos/{archivo_foto}").data == JPG
    for diente, estado in [(16, "Obturado"), (16, "Caries"), (26, "Obturado")]:
        assert est.post(f"/sesiones/{sid}/diente", json={"diente": diente, "estado": estado}).json == {"ok": True}
    assert est.post(f"/sesiones/{sid}/diente", json={"diente": 99, "estado": "Caries"}).status_code == 400
    assert sql("SELECT COUNT(*) FROM odonto_registros WHERE sesion_id = ?", (sid,)) == 2  # un registro por diente
    assert sql("SELECT estado FROM odonto_registros WHERE paciente_id = ? AND diente = 16", (pid,)) == "Caries"
    with m.app.test_request_context():  # el estado de cada diente sale del ultimo registro
        assert m.dientes_de(pid) == {16: "Caries", 26: "Obturado"}
    ok(est.post(f"/pacientes/{pid}/sesiones", data={"foto": foto()}, follow_redirects=True), "Ya hay un odontograma en curso")
with caso("CP-13", "Las fotos solo las ven el estudiante dueño y el docente"):
    assert grace.get(f"/fotos/{archivo_foto}").status_code == 404
    assert serv.get(f"/fotos/{archivo_foto}").status_code == 403
    assert prof.get(f"/fotos/{archivo_foto}").status_code == 200
    assert grace.get(f"/sesiones/{sid}").status_code == 404
with caso("CP-14", "Enviado queda bloqueado; el docente compara foto y digital, pide corrección y luego aprueba"):
    ok(est.post(f"/sesiones/{sid}/enviar", follow_redirects=True), "enviado al docente")
    assert est.post(f"/sesiones/{sid}/diente", json={"diente": 11, "estado": "Corona"}).status_code == 409
    ok(prof.get("/"), "Odontogramas por revisar (1)")
    ok(prof.get(f"/sesiones/{sid}"), "Foto del odontograma presencial", "Odontograma digital", "16: Caries",
       "Revisión del docente")
    assert est.post(f"/sesiones/{sid}/revision", data={"revision": "Aprobado"}).status_code == 403
    ok(prof.post(f"/sesiones/{sid}/revision", data={"revision": "Corregir", "observacion": ""}, follow_redirects=True),
       "Escriba qué debe corregir")
    ok(prof.post(f"/sesiones/{sid}/revision", data={"revision": "Corregir", "observacion": "Falta el 11 con corona"},
                 follow_redirects=True), "Revisión guardada")
    ok(est.get("/"), "Falta el 11 con corona")
    ok(est.get(f"/pacientes/{pid}"), "pidió corregir", "data-url")
    assert est.post(f"/sesiones/{sid}/diente", json={"diente": 11, "estado": "Corona"}).json == {"ok": True}
    est.post(f"/sesiones/{sid}/enviar")
    ok(prof.post(f"/sesiones/{sid}/revision", data={"revision": "Aprobado", "observacion": "Correcto"},
                 follow_redirects=True), "Aprobado")
    assert sql("SELECT estado FROM odonto_sesiones WHERE id = ?", (sid,)) == "Aprobado"
    ok(prof.get("/"), "Odontogramas por revisar (0)")
with caso("CP-15", "Una dirección de regreso externa se ignora (sin redirección abierta)"):
    r = prof.post(f"/sesiones/{sid}/revision", data={"revision": "Aprobado", "volver": "//sitio-malicioso.com"})
    assert r.location.endswith(f"/sesiones/{sid}"), r.location

print("Citas")
manana = (m.hoy() + timedelta(1)).isoformat()
est2_id = sql("SELECT id FROM usuarios WHERE usuario = '00000005'")
grace.post("/pacientes/nuevo", data={"nombre": "Rosa Díaz", "cedula": "T-200"})
pid2 = sql("SELECT id FROM pacientes WHERE cedula = 'T-200'")
grace.post(f"/pacientes/{pid2}/razon", data={"motivo_consulta": "Limpieza"})
with caso("CP-16", "Agendar cita con su razón genera el enlace de recordatorio por WhatsApp"):
    ok(est.post("/citas", data={"paciente_id": pid, "fecha": manana, "hora": "09:00", "sala_id": "1",
                                "motivo": "Obturación del 36"}, follow_redirects=True),
       "Cita agendada", "wa.me/50588880000", "Obturación del 36", "Dolor en la muela 36")
    ok(est.post("/citas", data={"paciente_id": pid, "fecha": manana, "hora": "12:00", "motivo": ""},
                follow_redirects=True), "la razón de la cita")  # la razon es obligatoria
with caso("CP-17", "No se permiten citas pasadas ni dos citas del paciente el mismo día"):
    ok(est.post("/citas", data={"paciente_id": pid, "fecha": "2020-01-01", "hora": "09:00", "motivo": "Control"},
                follow_redirects=True), "fechas pasadas")
    ok(est.post("/citas", data={"paciente_id": pid, "fecha": manana, "hora": "11:00", "motivo": "Control"},
                follow_redirects=True), "ya tiene una cita ese día")
with caso("CP-18", "No se permite la misma sala a la misma hora"):
    ok(grace.post("/citas", data={"paciente_id": pid2, "fecha": manana, "hora": "09:00", "sala_id": "1",
                                  "motivo": "Limpieza"}, follow_redirects=True), "sala ya está ocupada")
with caso("CP-19", "Un estudiante no puede agendar ni cambiar citas de pacientes ajenos"):
    ok(grace.post("/citas", data={"paciente_id": pid, "fecha": manana, "hora": "10:00", "motivo": "Control"},
                  follow_redirects=True), "Elige paciente")
    cid = sql("SELECT MAX(id) FROM citas")
    assert grace.post(f"/citas/{cid}/estado", data={"estado": "Atendida"}).status_code == 404

print("Salas y avisos a Servicios")
with caso("CP-20", "Un reporte de sala aparece como aviso pendiente para Servicios"):
    ok(est.post("/salas", data={"sala_id": "2", "tipo": "Limpieza", "descripcion": "Derrame en el piso"},
                follow_redirects=True), "Servicios ya recibió el aviso")
    ok(serv.get("/avisos"), "Pendientes (1)", "Derrame en el piso", '<span class="contador">1</span>')
with caso("CP-21", "Al agendar en una sala con reporte pendiente se advierte"):
    ok(grace.post("/citas", data={"paciente_id": pid2, "fecha": manana, "hora": "10:00", "sala_id": "2",
                                  "motivo": "Limpieza"}, follow_redirects=True), "la sala tiene un reporte pendiente")
with caso("CP-22", "Servicios atiende y resuelve; el estado se ve en Salas"):
    rep = sql("SELECT MAX(id) FROM reportes")
    serv.post(f"/reportes/{rep}", data={"estado": "En proceso"})
    ok(serv.post(f"/reportes/{rep}", data={"estado": "Resuelto"}, follow_redirects=True), "Pendientes (0)")
    ok(est.get("/salas"), "Resuelto")
with caso("CP-22b", "El plano de las salas marca con un check las disponibles y con una X las ocupadas"):
    est.post("/salas", data={"sala_id": "3", "tipo": "Reparación", "descripcion": "El sillón no reclina"})
    html = ok(admin.get("/salas"), "Plano de la clínica", "Agregar sala")
    plano = html.split('class="plano-salas"')[1].split("plano-pasillo")[0]
    assert plano.count("✓") == 2 and plano.count("✗") == 1, plano

print("Tratamientos y cobros")
ok(admin.post("/tarifario", data={"procedimiento": "Profilaxis", "precio": "300"}, follow_redirects=True), "C$ 300.00")
ok(est.post(f"/pacientes/{pid}/tratamientos", data={"procedimiento": "Profilaxis", "costo": "300"}, follow_redirects=True))
tid = sql("SELECT MAX(id) FROM tratamientos")
with caso("CP-23", "Un pago nunca supera el saldo pendiente"):
    est.post(f"/tratamientos/{tid}", data={"abono": "100"})
    est.post(f"/tratamientos/{tid}", data={"abono": "999"})
    assert sql("SELECT pagado FROM tratamientos WHERE id = ?", (tid,)) == 300
with caso("CP-24", "Un tratamiento con pagos solo lo puede eliminar la administración"):
    ok(est.post(f"/tratamientos/{tid}", data={"eliminar": "1"}, follow_redirects=True), "solo el administrador")
    assert sql("SELECT COUNT(*) FROM tratamientos WHERE id = ?", (tid,)) == 1
    admin.post(f"/tratamientos/{tid}", data={"eliminar": "1"})
    assert sql("SELECT COUNT(*) FROM tratamientos WHERE id = ?", (tid,)) == 0
    assert "pagado C$ 300.00" in sql("SELECT detalle FROM bitacora WHERE accion = 'Eliminó tratamiento'")

print("Protección del expediente")
with caso("CP-25", "Ya no existe la opción de borrar pacientes"):
    assert est.post(f"/pacientes/{pid}/eliminar").status_code in (404, 405)
    assert est.post(f"/pacientes/{pid}/archivo", data={"motivo": "x"}).status_code == 403
    assert prof.post(f"/pacientes/{pid}/archivo", data={"motivo": "x"}).status_code == 403
with caso("CP-26", "La administración archiva con motivo; el paciente desaparece de las listas pero se conserva"):
    ok(admin.post(f"/pacientes/{pid}/archivo", data={"motivo": ""}, follow_redirects=True), "Indique el motivo")
    ok(admin.post(f"/pacientes/{pid}/archivo", data={"motivo": "Alta del tratamiento"}, follow_redirects=True), "fue archivado")
    assert "Luis Pérez" not in prof.get("/pacientes").get_data(as_text=True)
    assert est.get(f"/pacientes/{pid}").status_code == 404
    ok(prof.get("/pacientes?archivados=1"), "Luis Pérez")
    ok(prof.get(f"/pacientes/{pid}"), "Paciente archivado", "Alta del tratamiento")
    assert sql("SELECT COUNT(*) FROM odonto_sesiones WHERE paciente_id = ?", (pid,)) == 1
with caso("CP-27", "La administración puede restaurar un paciente archivado"):
    ok(admin.post(f"/pacientes/{pid}/archivo", data={"restaurar": "1"}, follow_redirects=True), "Paciente restaurado")
    ok(est.get(f"/pacientes/{pid}"), "Luis Pérez")
with caso("CP-28", "El historial del expediente muestra todas las acciones realizadas"):
    html = ok(prof.get(f"/pacientes/{pid}"), "Historial de cambios")
    for accion in ("Registró paciente", "Modificó datos del paciente", "Registró firma", "Aprobó paciente",
                   "Subió foto del odontograma presencial", "Marcó diente en el odontograma digital",
                   "Envió odontograma a revisión", "Revisó odontograma", "Agendó cita", "Registró pago",
                   "Archivó paciente", "Restauró paciente"):
        assert accion in html, accion
with caso("CP-29", "Se crea una copia diaria automática de la base de datos"):
    copias = list(m.RESPALDOS.glob("dientecito-*.db"))
    assert len(copias) == 1 and copias[0].name == f"dientecito-{m.hoy().isoformat()}.db"
with caso("CP-30", "La administración descarga un .zip con la base de datos y las fotos"):
    r = admin.get("/respaldo")
    assert r.status_code == 200 and "attachment" in r.headers["Content-Disposition"]
    with zipfile.ZipFile(io.BytesIO(r.data)) as z:
        nombres = z.namelist()
        assert "dientecito.db" in nombres and f"fotos/{archivo_foto}" in nombres, nombres
        copia = TEMPORAL / "restaurada.db"
        copia.write_bytes(z.read("dientecito.db"))
    assert sqlite3.connect(copia).execute("SELECT COUNT(*) FROM pacientes").fetchone()[0] >= 3
    r.close()

print("Cuentas")
with caso("CP-31", "Cambio de clave propia y desactivación de cuentas"):
    ok(grace.post("/cuenta", data={"actual": "abc123", "nueva": "nueva123", "repetir": "otra"}, follow_redirects=True),
       "no coinciden")
    ok(grace.post("/cuenta", data={"actual": "abc123", "nueva": "nueva123", "repetir": "nueva123"}, follow_redirects=True),
       "Clave actualizada")
    cliente("grace.ruiz", "nueva123")
    admin.post(f"/usuarios/{grace_id}", data={"activo": "0"})
    assert grace.get("/").location.endswith("/entrar")

print("Traspaso de pacientes y consentimiento")
with caso("CP-32", "Al cambiar de estudiante se archiva el trabajo del anterior con lo que se le hizo"):
    assert est.get(f"/pacientes/{pid}/asignar").status_code == 403
    assert prof.get(f"/pacientes/{pid}/asignar").status_code == 403
    ok(admin.post(f"/pacientes/{pid}/asignar", data={"estudiante_id": grace_id, "resumen": ""},
                  follow_redirects=True), "Escriba qué se le hizo")
    ok(admin.post(f"/pacientes/{pid}/asignar",
                  data={"estudiante_id": est2_id, "resumen": "Odontograma y profilaxis; falta endodoncia del 46"},
                  follow_redirects=True), "quedó archivado en el historial")
    assert sql("SELECT estudiante_id FROM pacientes WHERE id = ?", (pid,)) == est2_id
    cerrada = sql("SELECT resumen FROM asignaciones WHERE paciente_id = ? AND hasta IS NOT NULL", (pid,))
    assert cerrada == "Odontograma y profilaxis; falta endodoncia del 46", cerrada
    assert est.get(f"/pacientes/{pid}").status_code == 404  # ya no es su paciente
with caso("CP-33", "El historial muestra qué le hizo cada estudiante al paciente"):
    html = ok(est2.get(f"/pacientes/{pid}"), "Trabajo por estudiante", "Grace Alvarado", "Gabriel Espinoza",
              "falta endodoncia del 46", "Qué le hizo cada estudiante", "Marcó diente en el odontograma digital")
    assert "Lo atiende ahora" in html
with caso("CP-34", "El consentimiento se imprime con la firma del paciente"):
    ok(est2.get(f"/pacientes/{pid}/consentimiento"), "Consentimiento informado", "Firma del paciente",
       "data:image/png;base64,AAAA", "Dolor en la muela 36")
    assert serv.get(f"/pacientes/{pid}/consentimiento").status_code == 403

total = 36
print(f"\n{total - len(fallos)} de {total} casos correctos." + (f" Fallaron: {', '.join(fallos)}" if fallos else ""))
sys.exit(1 if fallos else 0)
