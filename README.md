# Clínicas Odontológicas

Sistema de gestión para la **Clínica Odontológica UAM**. Es una aplicación web en Python (Flask + SQLite) que funciona en computadora y en teléfonos Android e iOS.

## Interfaces por rol
| Rol | Qué puede hacer |
|---|---|
| **Estudiante** | Registrar a sus pacientes, **la razón por la que vienen** y su historia clínica. Llenar el odontograma: **primero la foto del odontograma presencial**, después el digital, y enviarlo al docente. Tomar el consentimiento con firma e imprimirlo. Llevar tratamientos y cobros. Agendar sus citas (cada una con su razón) y enviar recordatorios. Reportar salas. **Cada estudiante ve únicamente sus pacientes y sus citas.** |
| **Profesor** | **Solo revisa.** Ve a todos los pacientes, revisa cada odontograma comparando la foto presencial con el digital y lo aprueba o pide corrección, aprueba pacientes y consulta el historial de qué le hizo cada estudiante a cada paciente. No registra pacientes, citas, tratamientos ni firmas, y no administra cuentas. |
| **Administración** | Crea y desactiva las cuentas, lleva el tarifario y el inventario, administra las salas, archiva y restaura expedientes y **cambia un paciente de estudiante archivando el trabajo del anterior**. |
| **Servicios** | Recibir los **avisos de salas** que necesitan reparación o limpieza y marcarlos como atendidos o resueltos. Administrar salas e inventario. |

Cuentas de ejemplo que se crean la primera vez (el CIF es el identificador de acceso), **dos por cada rol y una de administración**, todas con datos ficticios y la clave `uam2026` (se puede cambiar con la variable de entorno `DIENTECITO_CLAVE`):

| CIF | Nombre | Rol |
|---|---|---|
| `00000001` | Dra. Grace Mendoza | Profesor |
| `00000004` | Dr. Gustavo Rivas | Profesor |
| `00000002` | Grace Alvarado | Estudiante |
| `00000005` | Gabriel Espinoza | Estudiante |
| `00000003` | Gloria Téllez | Servicios |
| `00000006` | Germán Ortiz | Servicios |
| `00000007` | Gina Saavedra | Administración |

La administración crea las demás cuentas en la pestaña *Usuarios*. El nombre de la persona que entró aparece en la cabecera de todas las pantallas.

## Cambio de estudiante y trabajo por paciente
Cuando un paciente pasa a otro estudiante, la administración debe escribir **qué se le hizo al paciente y qué trabajó** el estudiante anterior. Ese trabajo queda archivado con su fecha de cierre y ya no se puede cambiar; el nuevo estudiante empieza su propio periodo. El expediente tiene la pestaña *Trabajo por estudiante* con los dos historiales: los periodos de cada estudiante con su resumen, y la lista de todo lo que cada uno le hizo al paciente.

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
- Los expedientes **no se borran**: la administración los archiva indicando un motivo, y puede restaurarlos.
- Una **bitácora** registra quién hizo qué y cuándo, incluidos el valor anterior y el nuevo de cada edición.
- Se hace una **copia diaria automática** de la base de datos (se conservan 14), y la administración puede descargar un `.zip` con la base y todas las fotos.

## Documentación
- [Diccionario de datos](docs/diccionario-de-datos.md)
- [Manual de usuario](docs/manual-de-usuario.md)
- [Plan de pruebas](docs/plan-de-pruebas.md). Para ejecutar las pruebas: `python pruebas.py` (36 casos, usa una base de datos temporal).

## Prototipo no funcional
La carpeta [`prototipo-no-funcional/`](prototipo-no-funcional) tiene el **prototipo no funcional** que se presenta en la defensa: las mismas pantallas y el mismo flujo de trabajo, pero sin base de datos (todo en memoria, se pierde al reiniciar) y sin JavaScript. Se ejecuta aparte con `python prototipo.py` y abre en `http://localhost:5001`; sus propias pruebas se corren con `python pruebas.py` dentro de esa carpeta.

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
