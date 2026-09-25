# Dientecito Feliz

Sistema de gestión para la **Clínica Odontológica UAM**. Es una aplicación web en Python (Flask + SQLite) que funciona en computadora y en teléfonos Android e iOS.

## Interfaces por rol
| Rol | Qué puede hacer |
|---|---|
| **Estudiante** | Registrar a sus pacientes y llevar su historia clínica. Llenar el odontograma: **primero la foto del odontograma presencial**, después el odontograma digital, y enviarlo al docente. Tomar el consentimiento con firma. Llevar tratamientos y cobros. Agendar citas y enviar recordatorios por WhatsApp. Reportar salas. |
| **Profesor** | Ver a todos los pacientes. **Revisar cada odontograma comparando la foto presencial con el digital** y aprobarlo o pedir corrección. Tiene acceso a todas las fotos. Aprobar pacientes. Administrar usuarios, tarifario e inventario. |
| **Servicios** | Recibir los **avisos de salas** que necesitan reparación o limpieza y marcarlos como atendidos o resueltos. Administrar salas e inventario. |

Cuentas de ejemplo que se crean la primera vez: `estudiante`, `profesor` y `servicios`, todas con la clave `uam2026` (se puede cambiar con la variable de entorno `DIENTECITO_CLAVE`). El profesor crea las demás cuentas en la pestaña *Usuarios*.

## Protección de los datos
- Los expedientes **no se borran**: el profesor los archiva indicando un motivo, y puede restaurarlos.
- Una **bitácora** registra quién hizo qué y cuándo, incluidos el valor anterior y el nuevo de cada edición.
- Se hace una **copia diaria automática** de la base de datos (se conservan 14), y el profesor puede descargar un `.zip` con la base y todas las fotos.

## Documentación
- [Diccionario de datos](docs/diccionario-de-datos.md)
- [Manual de usuario](docs/manual-de-usuario.md)
- [Plan de pruebas](docs/plan-de-pruebas.md). Para ejecutar las pruebas: `python pruebas.py` (31 casos, usa una base de datos temporal).

## Ejecutar en tu computadora
```bash
pip install -r requirements.txt
python app.py
```
Abre `http://localhost:5000`.
Los teléfonos conectados a la misma red Wi-Fi pueden entrar con la dirección que aparece en la consola.

## Publicar en PythonAnywhere
1. En PythonAnywhere ve a *Account → API token* y crea un token. Guárdalo en un archivo `.pa_token` en esta carpeta (git lo ignora).
2. Ejecuta `python desplegar.py TU_USUARIO`. Si tu cuenta es de la región europea, agrega `--eu`.

Ese mismo comando sirve para publicar cada actualización. La base de datos del servidor no se toca, así que los datos se conservan.

> La base de datos (`dientecito.db`), las fotos (`fotos/`) y los respaldos (`respaldos/`) nunca se suben al repositorio.

Proyecto de curso · Equipo: Andrés Castillo, Camilo Cruz, Reynaldo Mondragón, Roberto Silva, Miguel Suárez.
