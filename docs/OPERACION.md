# Guía de operación

## Cuentas

Cada responsable usa su cuenta individual. Administración gestiona cuentas, edificios, planos, inventario y respaldos. Operación gestiona empleados, verifica casilleros y realiza asignaciones. Consulta permite ver/exportar información; el servicio rechaza las modificaciones.

## Bajas y devoluciones

En Empleados selecciona una persona y utiliza **Dar de baja y liberar** para registrar un despido, renuncia, fin de contrato u otra baja. Selecciona el tipo y escribe un motivo interno. Al confirmar el servidor, la persona queda inactiva y su asignación termina en la misma operación; se conservan su historial, fecha y responsable. También funciona si la persona no tenía casillero.

Para una devolución voluntaria usa **Liberar casillero**. El empleado permanece activo. Puedes seleccionar Solicitud del empleado, Ya no necesita casillero u Otra devolución, y añadir observaciones internas.

En ambos casos el casillero queda **pendiente de verificar**. Marca Confirmé que está vacío y utilizable solamente si ya realizaste esa revisión física. Si hay pertenencias, daño o una ocupación dudosa, déjalo pendiente y resuelve la situación antes de volver a asignarlo.

La lista muestra empleados activos por defecto. Cambia el filtro a **Empleados inactivos** o **Todos los empleados** para consultar bajas. Para un reingreso puedes editar al empleado inactivo y marcar Activo; esto conserva el historial y no recupera automáticamente un casillero anterior.

## Avisos a HR

En **Administración → Configurar avisos a HR** indica el correo designado y si deseas copiar a HR en las devoluciones. Solo Administración puede modificar esta configuración. Los avisos de baja se dirigen únicamente a HR; los de devolución al empleado, con la copia elegida. Si el empleado no tiene correo y corresponde copiar a HR, HR será el destinatario principal.

Los avisos siguen en **modo simulado** hasta habilitar la integración corporativa con TI. Se registran automáticamente al confirmar la operación, sin incluir motivos internos ni detalles del despido. Consulta **Historial → Ver notificaciones de correo** para ver Para, Copia a, contenido y estado.

Si falta un correo se registra Falta destinatario o Simulado · falta correo HR; la operación de baja/devolución no se pierde. Cambiar la configuración afecta avisos futuros: no envía ni modifica retroactivamente los anteriores. Una solicitud pendiente por falta de conexión tampoco genera aviso hasta que el servidor la confirme. Los reintentos del mismo identificador no duplican el registro de notificación.

## Inventario y mapa

Confirma los edificios antes de registrar bloques. Para interiores, crea un plano por edificio y nivel. En Nuevo bloque indica filas y columnas según la disposición física. Los números individuales se escriben separados por comas, por filas de izquierda a derecha. También puedes generar una secuencia desde un primer número.

Los números físicos deben ser únicos en esta instalación. Si se repiten entre edificios, establece primero una convención que los distinga.

En Editar mapa arrastra bloques o puntos rojos de los contornos. Guarda y espera la confirmación antes de volver a editar. Abrir un bloque permite ver su cuadrícula. La verificación por bloque afecta únicamente los casilleros pendientes; confirma esta acción solo después de comprobar físicamente que todos esos casilleros están vacíos y utilizables.

En **Consultar**, un clic en la etiqueta abre el detalle con disponibles/asignados y **Ver asignaciones del bloque** (casillero, ID, nombre y apellidos). Verde significa que hay casilleros verificados disponibles; rojo significa que todos están asignados; ámbar significa que no hay disponibles pero no todos están asignados (por verificar, mantenimiento o retirados). Los colores reflejan la última sincronización confirmada, no solicitudes pendientes.

Las etiquetas muestran únicamente el código y se reducen cuando hay bloques próximos, incluso en filas de 40 bloques. Acerca con la rueda para leerlas y arrastra el fondo para recorrer la pared; Ajustar vista vuelve al plano completo. Los bloques colocados exactamente en la misma posición deben separarse en Editar mapa. La imagen conserva su proporción; X e Y continúan expresándose de 0 a 1000 respecto al ancho y alto.

En **Inventario → Exportar bloques y ubicaciones** puedes guardar Excel (.xlsx) o CSV: una fila por casillero, con plano, edificio, bloque, lado, ubicación, dimensiones, X/Y, rotación y numeración. Esta exportación no incluye personas. **Plantilla de inventario** crea los encabezados y, en Excel, una hoja de instrucciones. Mantén los números como texto para conservar ceros iniciales.

Para crear bloques, deja id_bloque/version_bloque vacíos, usa un plano y edificio existentes, y completa todas las posiciones (fila/columna comienzan en 1). Para actualizar, exporta primero y conserva los IDs y versiones: solo se modifican nombre, X/Y y rotación. Repite los mismos datos del bloque en todas sus filas. Importar no cambia dimensiones, números, condiciones ni asignaciones existentes. Los casilleros nuevos quedan pendientes de verificación física.

**Importar bloques Excel / CSV** valida el archivo completo y muestra una vista previa antes de confirmar. Se admite hasta 20 000 casilleros y 2000 bloques por archivo. Se guarda una sola solicitud en la cola local; el servidor aplica todo en una transacción o rechaza todo si existe un conflicto. Una exportación sin cambios no genera solicitudes. Si otro equipo actualizó un bloque, exporta nuevamente y revisa los cambios antes de reintentar.

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
