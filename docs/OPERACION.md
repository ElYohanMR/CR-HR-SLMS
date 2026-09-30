# Guía de operación

## Cuentas

Cada responsable usa su cuenta individual. Administración gestiona cuentas, edificios, planos, inventario y respaldos. Operación gestiona empleados, verifica casilleros y realiza asignaciones. Consulta permite ver/exportar información; el servicio rechaza las modificaciones.

## Inventario y mapa

Confirma los edificios antes de registrar bloques. Para interiores, crea un plano por edificio y nivel. En Nuevo bloque indica filas y columnas según la disposición física. Los números individuales se escriben separados por comas, por filas de izquierda a derecha. También puedes generar una secuencia desde un primer número.

Los números físicos deben ser únicos en esta instalación. Si se repiten entre edificios, establece primero una convención que los distinga.

En Editar mapa arrastra bloques o puntos rojos de los contornos. Guarda y espera la confirmación antes de volver a editar. Abrir un bloque permite ver su cuadrícula. La verificación por bloque afecta únicamente los casilleros pendientes; confirma esta acción solo después de comprobar físicamente que todos esos casilleros están vacíos y utilizables.

## Asignaciones

Abre un casillero disponible, selecciona una persona activa e indica el motivo. Puedes escribir en la lista para buscar; elige una sugerencia. Si la persona tiene otro casillero, se propone una reasignación que cierra la anterior y crea la nueva en una sola transacción.

Liberar exige un motivo y confirmación del servidor. Para desactivar un empleado, libera antes su casillero. Su historial permanece disponible.

## Solicitudes

- Pendiente: guardada localmente, todavía no constituye asignación.
- Confirmada: aplicada por el servidor.
- Conflicto: los datos cambiaron o ya existe un identificador/número. Revisa y crea una nueva solicitud correcta.
- Rechazada: incumple una regla o permiso.
- Requiere sesión: inicia sesión con la cuenta que creó la solicitud.
- Error temporal: tras varios intentos, revisa la conexión y usa Reintentar.

Cerrar la aplicación no borra pendientes. El reintento conserva su identificador, evitando aplicar dos veces una operación. El reloj local es informativo; prevalece el estado confirmado por el servidor.

## CSV

Descarga Plantilla CSV desde Empleados. Conserva los encabezados. ID, nombre y primer apellido son obligatorios. La importación acepta hasta 1000 empleados nuevos por archivo y muestra una vista previa. Cada alta tiene un resultado separado en Solicitudes; revisa todos los resultados.

Las exportaciones contienen información de personal y deben guardarse en ubicaciones de trabajo autorizadas. Inventario exporta también ubicación, condición y persona asignada.

## Copias

Administración → Crear copia de seguridad permite guardar un respaldo consistente. Haz copias antes de importaciones importantes y con la periodicidad acordada con TI. Prueba su restauración.

Las copias centrales no incluyen solicitudes que permanecen solo en equipos desconectados. Conserva el perfil Windows y los datos locales de esos equipos hasta resolverlas.

## Correo

Historial → Ver notificaciones muestra los avisos simulados para empleados con correo. No se envía ningún correo real. TI deberá suministrar la integración corporativa y confirmar el remitente.
