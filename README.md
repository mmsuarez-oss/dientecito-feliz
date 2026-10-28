# Clínicas Odontológicas

Sistema de gestión para la **Clínica Odontológica UAM**. Es una aplicación web en Python (Flask + SQLite) que funciona en computadora y en teléfonos Android e iOS.

## Interfaces por rol
| Rol | Qué puede hacer |
|---|---|
| **Estudiante** | Registrar a sus pacientes, **la razón por la que vienen** y su historia clínica. Llenar el odontograma: **primero la foto del odontograma presencial**, después el digital, y enviarlo al docente. Tomar el consentimiento con firma e imprimirlo. Llevar tratamientos y cobros. Agendar sus citas (cada una con su razón) y enviar recordatorios. Reportar salas. **Cada estudiante ve únicamente sus pacientes y sus citas.** |
| **Profesor** | **Solo revisa.** Ve a todos los pacientes, revisa cada odontograma comparando la foto presencial con el digital y lo aprueba o pide corrección, aprueba pacientes y consulta el historial de qué le hizo cada estudiante a cada paciente. No registra pacientes, citas, tratamientos ni firmas, y no administra cuentas. |
| **Facultad** | Crea y desactiva las cuentas, lleva el tarifario y el inventario, administra las salas, archiva y restaura expedientes y **cambia un paciente de estudiante archivando el trabajo del anterior**. |
| **Servicios generales** | Recibir los **avisos de salas** que necesitan reparación o limpieza y marcarlos como atendidos o resueltos. Administrar salas e inventario. |

Cuentas de ejemplo que se crean la primera vez (el CIF es el identificador de acceso), **dos por cada rol y una de la Facultad**, todas con datos ficticios y la clave `uam2026` (se puede cambiar con la variable de entorno `DIENTECITO_CLAVE`):

| CIF | Nombre | Rol |
|---|---|---|
| `00000001` | Dra. Grace Mendoza | Profesor |
| `00000004` | Dr. Gustavo Rivas | Profesor |
| `00000002` | Grace Alvarado | Estudiante |
| `00000005` | Gabriel Espinoza | Estudiante |
| `00000003` | Gloria Téllez | Servicios generales |
| `00000006` | Germán Ortiz | Servicios generales |
| `00000007` | Gina Saavedra | Facultad |

La Facultad crea las demás cuentas en la pestaña *Usuarios*. El nombre de la persona que entró aparece en la cabecera de todas las pantallas.

## Cambio de estudiante y trabajo por paciente
Cuando un paciente pasa a otro estudiante, la Facultad debe escribir **qué se le hizo al paciente y qué trabajó** el estudiante anterior. Ese trabajo queda archivado con su fecha de cierre y ya no se puede cambiar; el nuevo estudiante empieza su propio periodo. El expediente tiene la pestaña *Trabajo por estudiante* con los dos historiales: los periodos de cada estudiante con su resumen, y la lista de todo lo que cada uno le hizo al paciente.

## Salas
La pestaña *Salas* muestra un **plano sencillo de la clínica**: cada sala con un ✓ si está disponible o una ✗ si tiene un reporte de limpieza o reparación pendiente.

## Consentimiento informado
El consentimiento se firma en pantalla (con el dedo o el mouse) y se **imprime con la firma del paciente** desde el botón *Imprimir consentimiento* del expediente, en una hoja con el logo de la UAM, los datos del paciente, la razón de la consulta y el espacio para la firma del docente.

## Recordatorios de cita por correo

El paciente puede confirmar o cancelar su cita desde un enlace propio, sin necesidad de cuenta (botón **Correo**, además del de WhatsApp que ya existía). Para que el botón envíe correos de verdad, configure estas variables de entorno con los datos de su proveedor SMTP:

```
DIENTECITO_SMTP_HOST=smtp.ejemplo.com
DIENTECITO_SMTP_USUARIO=correo@ejemplo.com
DIENTECITO_SMTP_CLAVE=clave-o-token-de-app
DIENTECITO_SMTP_PUERTO=587          # opcional, 587 por defecto
DIENTECITO_SMTP_DESDE=correo@ejemplo.com   # opcional, usa el usuario si no se indica
```

Sin estas variables, el botón avisa que el correo no está configurado (el enlace de WhatsApp sigue funcionando igual que antes).

## Protección de los datos
- Los expedientes **no se borran**: la Facultad los archiva indicando un motivo, y puede restaurarlos.
- Una **bitácora** registra quién hizo qué y cuándo, incluidos el valor anterior y el nuevo de cada edición.
- Se hace una **copia diaria automática** de la base de datos (se conservan 14), y la Facultad puede descargar un `.zip` con la base y todas las fotos.

## Áreas de trabajo
Cada área está en su propia carpeta y se trabaja por separado:

| Carpeta | Qué contiene | Cómo se usa |
|---|---|---|
| [`sistema/`](sistema) | **El sistema**: `app.py`, las pantallas (`templates/`, `static/`), el despliegue (`desplegar.py`) y la base en la nube (`neon.py`) | `python sistema/app.py` |
| [`prototipo-no-funcional/`](prototipo-no-funcional) | El **prototipo no funcional** de la defensa: las mismas pantallas y el mismo flujo, pero en memoria (sin base de datos) y sin JavaScript | `python prototipo.py` dentro de la carpeta (`http://localhost:5001`) |
| [`pruebas/`](pruebas) | El [plan de pruebas](pruebas/plan-de-pruebas.md) y las pruebas automáticas del sistema | `python pruebas.py` dentro de la carpeta (36 casos, base de datos temporal) |
| [`documentos/`](documentos) | El [diccionario de datos](documentos/diccionario-de-datos.md), el [manual de usuario](documentos/manual-de-usuario.md) y los documentos de requerimientos | Documentación de la carrera |
| [`muestras/`](muestras) | Muestras y versiones de ejemplo, como `muestra_escritorio.py` (la vista de escritorio en Tkinter) | `python muestras/muestra_escritorio.py` |
| `respaldos/` | Las copias diarias de la base de datos (no se suben al repositorio) | Las crea el sistema solo |

El prototipo tiene sus propias pruebas: `python pruebas.py` dentro de `prototipo-no-funcional/` (22 comprobaciones).

## Ejecutar en tu computadora
```bash
pip install -r sistema/requirements.txt
python sistema/app.py
```
Abre `http://localhost:5000`.
Los teléfonos conectados a la misma red Wi-Fi pueden entrar con la dirección que aparece en la consola.

## Base de datos en la nube (Neon)
Por defecto el sistema guarda todo en el archivo `sistema/dientecito.db` (SQLite). Si quieres la base **en línea**, con PostgreSQL en [Neon](https://neon.tech):

1. Crea la cuenta y el proyecto en Neon y copia la cadena de conexión (`postgresql://usuario:clave@ep-….neon.tech/neondb?sslmode=require`).
2. Guárdala en la variable de entorno `NEON_URL` o en un archivo `.neon_url` dentro de `sistema/` (git lo ignora).
3. `pip install "psycopg[binary]"`
4. `python sistema/neon.py` crea las tablas y las cuentas de ejemplo en Neon.

Otras opciones: `--probar` solo prueba la conexión y lista las tablas, `--sql` imprime el SQL para pegarlo en el editor de Neon, y `--importar` copia a Neon lo que ya haya en `dientecito.db`.

## Publicar en PythonAnywhere
1. En PythonAnywhere ve a *Account → API token* y crea un token. Guárdalo en un archivo `.pa_token` en la raíz del proyecto o en `sistema/` (git lo ignora).
2. Ejecuta `python sistema/desplegar.py TU_USUARIO`. Si tu cuenta es de la región europea, agrega `--eu`.

Ese mismo comando sirve para publicar cada actualización. La base de datos del servidor no se toca, así que los datos se conservan.

> La base de datos (`sistema/dientecito.db`), las fotos (`sistema/fotos/`) y los respaldos (`respaldos/`) nunca se suben al repositorio.

Proyecto de curso · Equipo: Andrés Castillo, Camilo Cruz, Reynaldo Mondragón, Roberto Silva, Miguel Suárez.
