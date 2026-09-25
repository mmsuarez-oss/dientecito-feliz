# Manual de usuario — Dientecito Feliz

Sistema de gestión de la Clínica Odontológica UAM. Corresponde a la actividad 5.5 del cronograma.

## 1. Acceso

1. Abra el navegador (Chrome, Safari, Edge o Firefox) en la computadora o el teléfono y entre a la dirección del sistema.
2. Escriba su **usuario** y su **clave**, y presione **Entrar**.
3. Arriba a la derecha aparecen su nombre, **Mi cuenta** (para cambiar la clave) y **Salir**.

Las cuentas las crea un profesor. Si olvida su clave, pídale a un profesor que la restablezca.

**Usarlo como aplicación en el teléfono**
- iPhone: en Safari toque *Compartir → Agregar a pantalla de inicio*.
- Android: en Chrome toque el menú ⋮ → *Agregar a pantalla principal*.

---

## 2. Estudiante

Pestañas: **Inicio · Mis pacientes · Citas · Salas**

### Inicio
Muestra:
- Sus citas de hoy.
- Las citas de los próximos 3 días que aún no están confirmadas.
- Los registros de odontograma que el profesor todavía no aprueba o que le pidió **corregir**, con su observación.
- El estado de las salas.

### Registrar un paciente
1. En **Mis pacientes**, presione **Nuevo paciente**.
2. Llene los datos personales y la historia clínica. Solo el nombre y la cédula son obligatorios.
3. Si el paciente tiene **alergias**, escríbalas: aparecerán como alerta en todo su expediente.
4. Presione **Guardar**.

El paciente queda **pendiente de aprobación** hasta que un profesor lo apruebe.

### Expediente del paciente
Tiene cinco secciones:

| Sección | Para qué sirve |
|---|---|
| Historia clínica | Consultar los datos. Con **Completar historia clínica** se editan |
| Odontograma | Registrar las prácticas realizadas, con su foto |
| Tratamientos y cobros | Plan de tratamiento, pagos y saldo |
| Consentimiento | Firma del paciente en la pantalla |
| Citas | Historial de citas del paciente |

### Registrar una práctica en el odontograma
1. En la sección **Odontograma**, **toque el diente** trabajado. Queda marcado con un recuadro.
2. Elija el **estado** en que quedó el diente (caries, obturado, corona, endodoncia, extraído o sano).
3. Escriba una breve **descripción** del procedimiento.
4. En **Foto**, adjunte la foto de la práctica. En el teléfono puede tomarla con la cámara en ese momento.
5. Presione **Guardar registro**.

La foto es **obligatoria**: sin ella el registro no se guarda. Queda **pendiente** hasta que el profesor la revise. Si el profesor pide corregir, verá su observación en *Inicio* y deberá registrar la práctica de nuevo con una foto adecuada.

### Consentimiento informado
1. Lea el texto al paciente.
2. Pídale que firme con el dedo (o el mouse) dentro del recuadro. **Borrar** limpia el recuadro.
3. Presione **Guardar firma**.

### Tratamientos y cobros
- **Agregar tratamiento:** escriba el procedimiento. Si está en el tarifario, el costo se llena solo.
- **Registrar pago:** escriba el monto en la fila del tratamiento y presione **Pagar**. El sistema no permite pagar más que el saldo.
- Arriba se muestran el total, lo pagado y el saldo.
- Un tratamiento que ya tiene pagos solo puede eliminarlo un profesor.

### Citas
1. En **Citas**, elija el paciente, la fecha, la hora, la sala (opcional) y el motivo, y presione **Agendar**.
2. El sistema **no permite**:
   - citas en fechas pasadas;
   - dos citas del mismo paciente el mismo día;
   - dos citas suyas a la misma hora;
   - una sala ocupada a esa hora.
3. Si la sala tiene un reporte pendiente, el sistema le avisa.
4. **Recordar por WhatsApp** abre WhatsApp con el mensaje de recordatorio ya escrito. Cuando el paciente responda, cambie el estado de la cita a **Confirmada**.
5. Después de la cita, marque **Atendida** o **No asistió**.

### Reportar una sala
En **Salas**, elija la sala y el problema (**necesita reparación** o **está sucia**), agregue un detalle y presione **Enviar aviso**. Servicios lo recibe de inmediato, y usted puede seguir el estado del reporte en la misma pantalla.

---

## 3. Profesor

Pestañas: **Inicio · Pacientes · Citas · Salas · Tarifario · Usuarios · Bitácora**

El número junto a *Inicio* indica cuántos pendientes tiene.

### Revisar odontogramas
En **Inicio → Odontogramas por revisar** aparece cada práctica con su foto. Toque la foto para verla en grande.
- **Aprobar** confirma la práctica.
- **Corregir** la devuelve al estudiante. Escriba en *Observación* lo que debe corregir.

### Aprobar pacientes
- En **Inicio → Pacientes por aprobar**, presione **Aprobar**.
- También puede hacerlo desde el expediente, con **Aprobar paciente** o **Retirar aprobación**.

### Pacientes
- Ve a los pacientes de todos los estudiantes y puede filtrarlos por estudiante.
- Al registrar o editar un paciente puede asignarle el estudiante responsable.

### Archivar un paciente (en lugar de borrarlo)
Los expedientes **no se borran**. Al final del expediente:
1. Escriba el **motivo** (alta, abandono, registro duplicado…).
2. Presione **Archivar paciente**.

El paciente deja de aparecer en las listas y en la agenda, pero conserva todo su historial. Para verlo, marque **Ver archivados** en *Pacientes*. Dentro del expediente, **Restaurar** lo devuelve a las listas.

### Historial de cambios
En el expediente, la sección **Historial de cambios** muestra todo lo que se ha hecho con ese paciente: quién, qué y cuándo. En las ediciones incluye el valor anterior y el nuevo.

### Tarifario
Registre cada procedimiento con su precio. Si guarda un procedimiento que ya existe, se actualiza su precio.

### Usuarios
- **Nuevo usuario:** nombre, usuario (sin espacios ni tildes), rol y clave inicial de al menos 6 caracteres.
- **Restablecer clave:** escriba la clave nueva en la fila del usuario y presione **Cambiar**.
- **Desactivar:** la persona ya no puede entrar, pero su historial se conserva. Las cuentas no se borran.

### Bitácora y copias de seguridad
- La **bitácora** registra todas las acciones del sistema, incluidos los inicios de sesión y los intentos fallidos. Puede buscar por texto o filtrar por usuario.
- **Descargar copia:** baja un archivo `.zip` con la base de datos y todas las fotos. Guárdelo fuera del servidor (computadora o Drive) **al menos una vez por semana**.
- El servidor además guarda una copia automática diaria de la base de datos y conserva las últimas 14.

**Restaurar una copia:** detenga el sistema, reemplace `dientecito.db` y la carpeta `fotos/` por las del `.zip`, y vuelva a iniciarlo.

---

## 4. Servicios

Pestañas: **Avisos · Salas · Inventario**

### Avisos
Lista los reportes de salas que necesitan **reparación** o **limpieza**. El número junto a *Avisos* indica cuántos hay pendientes. La página se actualiza sola cada minuto.
1. Presione **Atender** cuando empiece a trabajar en el reporte. El estado pasa a *En proceso*.
2. Presione **Marcar resuelto** al terminar.

Quien hizo el reporte verá el cambio de estado en la pestaña *Salas*.

### Salas
- Muestra el estado de cada sala: *Disponible*, *Necesita reparación* o *Necesita limpieza*.
- Permite agregar o eliminar salas.

### Inventario
- **Agregar o actualizar material:** nombre, unidad, cantidad actual y mínimo.
- Los botones **−** y **+** ajustan la cantidad de uno en uno.
- Cuando la cantidad llega al mínimo, el material aparece como **Reponer** y se muestra primero en la lista.

---

## 5. Preguntas frecuentes

**La foto no se sube.** Revise la conexión. Las fotos grandes se reducen automáticamente antes de enviarse. El límite es de 15 MB.

**No veo a un paciente.** Los estudiantes solo ven a sus propios pacientes. También es posible que esté archivado; pregunte a un profesor.

**Me equivoqué en un registro del odontograma.** Registre de nuevo la práctica con el estado correcto. El historial conserva ambos registros y el profesor revisará el último.
