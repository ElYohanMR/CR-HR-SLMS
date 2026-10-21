# Despliegue y recuperación

Para la instalación paso a paso, rutas, supervisión del servicio y limitaciones
de certificados del cliente actual, consultar [DESPLIEGUE_TI.md](DESPLIEGUE_TI.md).
Las mejoras propuestas están en [ROADMAP.md](ROADMAP.md).

## Actualización 1.14.0

No requiere migración de esquema. El servidor debe reiniciarse con la nueva
versión para generar las nuevas plantillas; los avisos anteriores no se reescriben.
La vista previa guarda borradores locales cifrados y abre mailto, sin enviar
automáticamente. Consulte MICROSOFT.md (Integracion-Microsoft-TI.md en el paquete)
para el alcance pendiente de identidad y envío. Los botones previstos no activan
una integración real; hace falta implementar y validar los conectores con TI.

## Actualización 1.13.0

La migración 0007 añade lockers.has_padlock (boolean nullable). Los registros
anteriores quedan NULL (Sin registrar); nuevos casilleros usan False. No se
modifican asignaciones. locker.update incluye el campo con control de versión,
auditoría y cola existente; los clientes anteriores pueden omitirlo sin borrarlo.

Las fotografías de cortes son opcionales. Permanecen las comprobaciones de
encargado, estado, identidad, fecha y resultado. Las capacidades del snapshot
optional_cut_photos y locker_padlock indican soporte. Actualiza y reinicia el
servicio junto con los clientes; respalda la base antes de actualizar.

## Topología y requisitos

Un servicio central FastAPI con PostgreSQL y de una a tres aplicaciones Windows conectadas por HTTPS. Los clientes no reciben credenciales de PostgreSQL. El servidor de esta entrega se ejecuta en Windows bajo la cuenta que configuró su secreto DPAPI.

En desarrollo escucha en 127.0.0.1:8765. El lanzador lo inicia si hace falta y lo deja activo. No se modifican firewall ni puertos externos automáticamente.

## Instalación corporativa

1. Proveer una base PostgreSQL dedicada y una cuenta propietaria para migraciones. TI puede separar posteriormente el rol de migraciones del operativo.
2. Ejecutar el asistente bajo la cuenta Windows que alojará el servicio. Configurar la base y crear el primer administrador.
3. Supervisar **SamtecLockers.exe --server** o **python -m slms --server** mediante el mecanismo aprobado por TI.
4. Colocar un proxy HTTPS delante del servicio local y validar que su certificado sea reconocido por el cliente SLMS. Una CA corporativa instalada en Windows no basta en esta versión; consultar DESPLIEGUE_TI.md. Mantener loopback si ambos están en el mismo equipo. Limitar peticiones a 9 MB y a las redes autorizadas.
5. Instalar la distribución completa en los clientes, elegir Conectar a servidor de TI e indicar la dirección HTTPS.
6. Crear cuentas de administración, operación y consulta.

Desde código puede ajustarse escucha/puerto ejecutando scripts/server-settings.py desde un entorno que incluya la raíz del proyecto en PYTHONPATH. Reiniciar el servicio. Se recomienda conservar loopback y usar el proxy corporativo.

Detén el servicio anterior antes de cambiar a una base diferente. La configuración privada está ligada al usuario Windows: copiarla a otro perfil no permite descifrarla. No utilices cambios de conexión como sustituto de una migración planificada.

## Respaldo y restauración PostgreSQL

El respaldo utiliza pg_dump en formato custom. Busca el ejecutable en PATH o en la ubicación estándar de PostgreSQL 18. Una copia queda en la subcarpeta backups de los datos del servidor, además de la descarga. TI debe definir retención y copia externa.

Para restaurar sin sobrescribir la base operativa:

1. Detener el servicio o impedir escrituras.
2. Crear una base nueva y vacía con el propietario correcto.
3. En pgAdmin seleccionar esa base → Restore y elegir el archivo .dump. Restaurar sin propietarios anteriores si cambian los roles.
4. Verificar empleados, casilleros, asignaciones, cuentas e historial; comparar cantidades.
5. Configurar el servicio hacia esa base, comprobar acceso y una operación controlada y reabrir el servicio.
6. Reconciliar operaciones posteriores al respaldo. No reenviar automáticamente solicitudes antiguas ya confirmadas. Conservar la base previa hasta cerrar la recuperación.

tests/run_postgres.py ejecuta una restauración real en una base temporal independiente. También se comprueban respaldos SQLite. Esto no sustituye la prueba periódica del ambiente corporativo.

Para SQLite de demostración se utiliza su API de backup consistente. Restaurar con el servicio detenido y conservar la base anterior.

## Identidad y seguridad

PBKDF2-SHA256, sal aleatoria individual y 600000 iteraciones. Tokens aleatorios, almacenados como hash en el servidor, con vigencia de 12 horas. Los cambios de contraseña revocan sesiones. Cada petición comprueba cuenta activa y rol. El login limita intentos por dirección/usuario; complementar en el proxy según la política corporativa.

Los cambios de negocio y su auditoría se guardan juntos. UUID de solicitud, comprobaciones de versión y restricciones únicas impiden efectos duplicados y asignaciones incompatibles. En PostgreSQL se serializan las transacciones cortas de escritura mediante un bloqueo asesor, apropiado para los tres puestos previstos.

La API no permite editar ni borrar auditoría. Esto no hace el registro inmutable frente al administrador de la base de datos.

## Correo y futuras integraciones

La notificación simulada se crea dentro de la transacción de asignación. Para envío real se necesitan registro de aplicación, permisos, remitente y política de entrega/reintentos de Microsoft Graph. No hay envío real habilitado ni SSO de Entra ID en esta entrega.

Desde 1.2 las bajas (`employee.deactivate`) cierran la asignación y desactivan al empleado en una única transacción. La devolución y la baja dejan el locker pendiente de revisión salvo confirmación física explícita. La baja conserva su tipo y motivo en `employees.extra.departure`, además de la auditoría y del cierre de asignación. El motivo interno nunca se incluye en los correos nuevos.

La migración 0002 agrega `mail_settings` y el campo JSON `notifications.cc`, sin modificar destinatarios ni auditorías anteriores. El correo de HR y la copia opcional de devoluciones se configuran desde Administración. Cada operación mantiene una única notificación por UUID, con destinatario principal y lista de copias, dentro de la transacción. Los estados `simulado`, `simulado_sin_hr` y `sin_destinatario` nunca indican entrega real. Una futura integración debe manejar envío, reintentos y fallos separadamente, sin revertir la baja ya confirmada ni prometer entrega exactamente una vez mediante SMTP.

## Operación

Monitorear /health, espacio libre, proceso y PostgreSQL. application.log rota a 2 MB con tres copias previas. Gestionar también logs del proceso y copias de seguridad desde TI.

Definir con HR conservación de notas, historial y exportaciones. El ejecutable de desarrollo no tiene firma corporativa; TI puede firmarlo al distribuirlo. Revisar las licencias incluidas y la procedencia de la imagen antes de una redistribución externa. Se conserva la atribución de la imagen aportada.

## Cortes de candado · actualización 1.12

La migración 0006 agrega `cut_requests` y `cut_evidence`. Las fotografías
originales se almacenan como binarios en la misma base de datos, con tipo,
tamaño, SHA-256, responsable y fecha de carga. Por tanto, forman parte del
respaldo PostgreSQL/SQLite; no requieren copiar una carpeta de fotos del servidor.
No se incluyen sus bytes en el snapshot ni en los eventos de auditoría.

Las operaciones `cut.*` usan la misma cola y transacción idempotente del resto
de la aplicación. Las fotos pendientes se conservan cifradas mediante DPAPI en
`queue_photos` del equipo emisor y se incorporan al comando al transmitirlo.
No están en el respaldo central hasta que el servidor confirme la carga.

`GET /cuts/evidence/{id}` exige sesión y rol operator/admin; no admite
enlaces públicos. `GET /cuts/{id}/history` devuelve el historial completo del
expediente para una cuenta autenticada. La cuenta viewer consulta seguimiento,
sin modificar casos ni descargar fotos. Los límites por foto son 6 MB, 24
megapíxeles y formato JPG/PNG con decodificación validada.

La recepción del mensaje de Teams/correo y la verificación presencial son tareas
humanas. La aplicación registra quién las procesó; no conecta con Microsoft ni
valida automáticamente el contenido o la identidad mostrada en una foto.
Los expedientes cerrados y evidencias sustituidas se conservan. Cualquier política
corporativa de retención o eliminación requerirá definir el procedimiento con TI.
