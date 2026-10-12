# Validación de la entrega

## Versión 1.12.0 · 12 de octubre de 2026

- Solicitudes de corte: Solicitada, En proceso, Finalizada y Cancelada; identificación
  del empleado y casillero al crear, supervisor, canal, motivo, encargado, fecha real,
  resultado y cuenta que registra cada paso. Las operaciones no cambian asignaciones.
- Tres evidencias obligatorias y distintas para el cierre: identidad frente al
  casillero, antes y después del corte. JPG/PNG limitados a 6 MB y 24 megapíxeles.
  Conservación de originales, huella SHA-256 y fotografías sustituidas con motivo.
  La aplicación muestra la orientación de la cámara sin reescribir el archivo.
- Consulta de fotografías autenticada y restringida a Operación/Administración.
  Los listados e historial no transportan los archivos; la cola local guarda las
  fotos cifradas aparte de sus metadatos y las incorpora solo al enviar el paso.
- Una solicitud abierta por casillero, control de versiones entre computadoras,
  reenvío idempotente después de una respuesta perdida y cierre condicionado a
  evidencia confirmada, encargado, fecha válida e identidad verificada.
- Historial completo por expediente; los casos cerrados no se modifican.
  El inventario con historial de cortes no se puede eliminar definitivamente.
- Migración 0006 agrega dos tablas. Actualización desde 0005 y ejecución repetida
  verificadas sin cambios en las tablas preexistentes.
- Suite general: 147 pruebas aprobadas y una expectativa antigua de cantidad de
  tablas actualizada para incluir Cortes de candado. Revalidación focalizada:
  11 pruebas aprobadas; otras 3 aprobadas tras ajustar el indicador de pendientes.
  Total cubierto: 148 casos. Revisión estática sin errores.
- PostgreSQL: 16 pruebas aprobadas en clúster temporal, incluidas concurrencia,
  permisos, fotografías inválidas, pérdida de respuesta, migración y restauración
  de fotografías y solicitudes desde un respaldo.
- Revisión visual con datos y tarjetas de color ficticios. No se crearon solicitudes
  de prueba ni fotografías en la base del usuario.
- Ejecutable 1.12 verificado en perfil temporal independiente: pantallas, creación,
  asignación, evidencias PNG y cierre. Servidor del ejecutable probado sin interfaz:
  JPEG original, recuperación autenticada, historial, cancelación y flujos previos
  de baja y aviso simulado. No se enviaron correos reales.
- Respaldo previo de la base local: samtec-20261012-161048-349691.dump. El servidor
  real sigue en 1.10.0; al reiniciar Windows y abrir el nuevo acceso directo, el
  servidor 1.12 aplica la migración. La interfaz comprueba esta capacidad antes
  de habilitar la creación de solicitudes de corte.

## Versión 1.9.0 · 9 de octubre de 2026

- Casillas en todas las tablas; marcar/desmarcar filas visibles y copiar las marcadas mediante clic derecho. Persistencia por ID al ordenar/refrescar y limpieza al filtrar fuera una fila.
- Restauración múltiple atómica con deduplicación de bloques e hijos; incluye casilleros eliminados anteriormente si se marcan explícitamente.
- Eliminación definitiva de inventario archivado sin asignaciones ni revisiones asociadas. Libera códigos, conserva auditoría y exige motivo, confirmación escrita y cuenta inicial. Una versión antigua o elemento protegido cancela todo el lote.
- Migración 0005 identifica y persiste la cuenta inicial, sin depender del nombre o rol. Instalaciones heredadas ambiguas no reciben este permiso automáticamente. Ninguna petición puede crear o modificar la marca de cuenta inicial; otros administradores tampoco pueden cambiar esa cuenta.
- PostgreSQL: 15 pruebas aprobadas en clúster temporal, incluyendo concurrencia, reenvíos, migración, restauración, conservación de históricos y respaldo/restauración.
- Revisión visual de las casillas, selección de dos bloques y formulario de eliminación definitiva con datos ficticios. Revisión estática sin errores.
- Suite completa SQLite/Qt: 101 pruebas aprobadas. Ejecutable 1.9.0 verificado en perfil temporal: interfaz, pantallas nuevas, migraciones, servidor, autenticación y operaciones habituales correctas.
- Base local migrada a 0005 tras un respaldo. Los campos anteriores y archivos de configuración permanecen íntegros; se reconoció una sola cuenta inicial. No se ejecutaron eliminaciones/restauraciones sobre el inventario real.
- El inicio del servicio local fue bloqueado por la revisión automática de aprobación. La aplicación inicia normalmente su servicio al abrirse; el ejecutable y su servidor se comprobaron en un perfil temporal independiente.

## Versión 1.8.1 · 8 de octubre de 2026

- Crear fila permite combinar bloques existentes con nuevos. Los existentes conservan identificadores, casilleros y asignaciones; solo cambia su ubicación/nombre/rotación mediante la operación de inventario existente.
- Los eliminados muestran instrucciones de restauración, sin confundir el historial con la reserva de códigos. Se comprueban plano, dimensiones y numeración antes de reubicar; el lado registrado se conserva y se muestra en la vista previa.
- Vista previa distingue Crear/Reubicar y conserva los colores de ocupación de los bloques existentes. La solicitud incorpora sus versiones para rechazar cambios concurrentes.
- 16 pruebas aprobadas: eliminación/restauración de E01–E05 y ampliación hasta E08 sin perder identidades ni auditoría; rechazo atómico de versiones antiguas, numeración o dimensiones incompatibles; envío desde la vista previa, revisiones físicas y tamaño del mapa. Revisión estática sin errores.
- No hay cambios de esquema ni eliminación de datos del usuario.
- Ejecutable 1.8.1 verificado en perfil temporal independiente; vista previa, interfaz, servidor y autenticación correctos. Tres pruebas adicionales tras ajustar la conservación del lado registrado también aprobadas.

## Versión 1.8.0 · 8 de octubre de 2026

- Creación de filas de hasta 200 bloques con extremos normalizados, vista previa, dimensiones editables y numeración de derecha a izquierda. Verificada una fila de 40 bloques / 480 casilleros y el rechazo atómico de una colisión surgida después de la vista previa.
- Revisiones físicas persistentes: resultados por casillero, responsable, horas local/servidor, discrepancias, cierre y exportación. Ningún resultado termina asignaciones. Las observaciones concurrentes o antiguas generan conflicto; se puede retomar el recorrido tras sincronizar.
- Asistente de conflictos con comparación legible y formularios de corrección. Una corrección crea otro identificador y conserva la solicitud original; no fuerza versiones ni repite lotes.
- Migración 0004: dos tablas nuevas; actualización desde 0003 e invocación repetida verificadas conservando inventario.
- Suite SQLite/Qt: 86 pruebas aprobadas, más 2 casos posteriores de concurrencia/permisos y actualización de esquema. PostgreSQL: 25 pruebas aprobadas en un clúster temporal, incluidas las 10 nuevas de estos flujos, concurrencia de asignaciones, eliminación de inventario y respaldo/restauración.
- Revisión estática sin errores. Pantallas de vista previa, revisión y conflictos comprobadas con datos ficticios.
- Ejecutable 1.8.0 comprobado en un perfil temporal independiente: pantallas nuevas, migraciones, servidor, autenticación, baja atómica y aviso simulado único correctos.
- Base local actualizada a 0004 después de crear un respaldo. Comparación íntegra de las tablas preexistentes y archivos de configuración: sin cambios; se conservan 17 bloques, 204 casilleros y 51 empleados.
- El reinicio del servidor en ejecución fue bloqueado por la revisión automática de aprobación. El servidor anterior sigue activo; reiniciar Windows y abrir la aplicación carga el servidor actualizado. La pantalla de revisiones comprueba que el servidor anuncie esta función antes de habilitarla.
- Los correos continúan simulados. Una revisión cerrada conserva discrepancias pendientes de resolución; no sustituye el trámite de devolución o baja.

## Versión 1.7.1 · 8 de octubre de 2026

- Corrección de etiquetas que se encogían al crear o acercar bloques: el tamaño se recalculaba según la distancia al vecino más próximo en cada actualización. Se sustituyó por el tamaño base fijo de 2,8 unidades del mapa, conservando la reducción solicitada previamente.
- El zoom escala conjuntamente mapa y etiquetas. Crear, mover, eliminar vecinos o sincronizar no modifica el tamaño relativo ni la escala del texto. No se alteran las coordenadas ni datos del inventario.
- 16 pruebas de mapa y menús contextuales aprobadas; incluyen creación cercana, eventos de rueda en ambos sentidos, actualizaciones, movimiento, coincidencia de posiciones, eliminación del vecino, 40 bloques alineados, búsqueda y clic derecho. Revisión estática sin errores.
- Ejecutable 1.7.1 comprobado en un perfil temporal: interfaz, mapa, servidor, autenticación, baja atómica y aviso simulado único correctos.

## Versión 1.7 · 8 de octubre de 2026

- Menú contextual en todas las tablas: acciones según registro y rol, consulta y copia de datos. Importaciones, exportaciones y configuración agrupadas en menús para reducir botones.
- Clic derecho en mapa: consultar, editar, verificar o eliminar un bloque; crear uno en las coordenadas pulsadas en un espacio vacío. Coordenadas comprobadas después de zoom y desplazamiento.
- La selección se toma de la fila pulsada y se vuelve a resolver por ID al ejecutar la acción. Una actualización o cambio de orden no cambia el registro destinatario; una fila que desaparece no ejecuta acciones sobre otra.
- Vista física de derecha a izquierda y de arriba hacia abajo; columna 1 a la derecha. Comprobación en bloques de 3 y 4 columnas, conservando los números e identificadores. La plantilla explica esta convención.
- Suite general: 75 pruebas aprobadas en SQLite/Qt. Comprobación final específica: 10 pruebas aprobadas de menús, evento real de clic derecho, permisos, coordenadas y distribución (incluye las 8 que ya estaban en la suite general y 2 casos adicionales).
- Revisión estática sin errores. Revisión visual del inventario simplificado, menú de fila y bloque numerado de derecha a izquierda. Sin cambios de esquema ni modificación de los registros del usuario.
- Ejecutable 1.7 verificado en perfil temporal: interfaz y menú contextual, ordenación y selección, distribución física, servidor, autenticación, baja atómica y aviso simulado único.

## Versión 1.6 · 7 de octubre de 2026

- Orden por cualquier columna en todas las tablas, incluyendo consultas e importaciones. Clic ascendente/descendente y flecha visible en el encabezado.
- Comparación numérica sin perder ceros iniciales ni precisión en ID largos, códigos con orden natural, nombres en español y fechas en orden cronológico.
- La actualización completa cada fila antes de ordenar; conserva el orden elegido y la selección por identificador. Si un filtro elimina la fila seleccionada, se limpia la selección para evitar acciones sobre otro registro.
- 67 pruebas pasan en SQLite e interfaz Qt, incluyendo 8 nuevas pruebas de ordenación, clics en encabezados, actualización y selección. Revisión estática sin errores y revisión visual del inventario ordenado.
- Ejecutable independiente verificado en un perfil temporal: ordenación ascendente/descendente, selección tras refrescar, flecha visible, servidor, autenticación, baja atómica y aviso simulado único.
- Esta versión cambia la presentación de las tablas; no modifica el esquema ni las operaciones de la base de datos.

## Versión 1.5 · 7 de octubre de 2026

- Diagnóstico: la sesión local guardada recibía HTTP 401 y las dos eliminaciones seguían con cero intentos. El servidor estaba disponible; no era un fallo de eliminación ni de PostgreSQL.
- Las solicitudes pendientes se marcan Requiere sesión cuando el servidor rechaza la sesión. La interfaz muestra un botón de acceso y el arranque valida la sesión guardada. El trabajo sin conexión conserva la cola local.
- Una eliminación pendiente del mismo elemento reutiliza su solicitud local. Solicitudes duplicadas de versiones anteriores confirman el estado eliminado sin repetir cambios ni auditoría; una eliminación antigua no puede volver a eliminar un elemento restaurado.
- Menú Opciones con mapa, inventario, empleados, conexión, solicitudes, administración, respaldos, historial y ayuda; acciones restringidas por rol.
- 59 pruebas pasan en SQLite; 9 pruebas de regresión de sincronización/eliminación pasan en un clúster PostgreSQL temporal. Incluyen sesión vencida → inicio de sesión → confirmación de la solicitud original, duplicados y recuperación de inventario.
- No se omitió la autenticación ni se modificaron contraseñas. Las eliminaciones guardadas requieren que su responsable inicie sesión localmente.

## Versión 1.4 · 7 de octubre de 2026

- 55 pruebas pasan en un clúster PostgreSQL temporal independiente, incluyendo respaldo/restauración y la migración 0003. En SQLite pasan las pruebas anteriores y las nuevas de eliminación, restauración y búsqueda; una prueba adicional verifica búsqueda entre planos, códigos ambiguos y resultados ausentes.
- Eliminar inventario requiere Administración y un motivo. Se rechazan elementos ocupados y versiones antiguas. La eliminación de un bloque es atómica y conserva empleados, asignaciones históricas y auditoría.
- Restaurar un bloque recupera solo los casilleros eliminados junto a él; los casilleros restaurados quedan pendientes de revisión. Los códigos eliminados permanecen reservados. Excel puede exportar/reimportar bloques a los que se quitaron casilleros.
- Creación: 4 filas y 3 columnas predeterminadas, editables. No se alteran dimensiones existentes.
- Etiquetas con un quinto del ancho y alto anteriores. Búsqueda con Enter por bloque, número físico o código completo; selección ante códigos ambiguos y cambio de plano automático.
- Halo azul exterior con transición de un segundo para aparecer y otro para atenuarse; conserva colores de estado y continúa tras sincronizar. Se apaga al seleccionar un bloque.
- Respaldo PostgreSQL previo a actualizar la base configurada. Se verificaron los recuentos de bloques, casilleros, empleados y asignaciones antes y después; no se eliminó inventario real durante el desarrollo.

## Versión 1.3 · 6 de octubre de 2026

- 51 pruebas pasan con SQLite. En PostgreSQL, 50 pasan en esquemas temporales; la prueba restante de respaldo/restauración pasa en un clúster temporal independiente. La cuenta de aplicación no tiene permiso para crear bases, por lo que esa prueba se trasladó al clúster de pruebas sin elevar sus permisos.
- Excel y CSV: creación de bloques 3 × 4, lectura/escritura preservando ceros iniciales, exportación/reimportación sin cambios, edición de posiciones y nombres conservando casilleros y asignaciones.
- Rechazo de filas incompletas, duplicadas, inconsistentes, coordenadas no finitas, dimensiones fraccionarias, numeración modificada, versiones antiguas y fórmulas de Excel.
- Importación atómica: un conflicto revierte todos los bloques y su auditoría; los reintentos no duplican bloques. Importación restringida a Administración.
- Interfaz: fila de 40 bloques sin solapamiento en la disposición probada, consulta con un clic, acceso a la lista de asignaciones vigentes, códigos de color verde/rojo/ámbar y movimiento conservando coordenadas normalizadas.
- Imagen 3956 × 2478 conservando proporciones. Realineación del plano existente mediante 1738 correspondencias visuales entre imágenes; respaldo cifrado local previo de contornos y posiciones. No se añadieron bloques ficticios al inventario real.
- Revisión visual con 40 bloques ficticios: textos escalados sin perder dígitos; vista de consulta e inventario sin recortes. Las etiquetas cercanas requieren acercar el mapa para leerlas.
- Ejecutable verificado en un perfil aislado: interfaz, servidor, autenticación, importación Excel, actualización de posiciones, idempotencia y avisos simulados.

No cambió el esquema de base de datos. El plano existente se actualizó con auditoría, conservando empleados, casilleros y asignaciones. Los demás datos de pruebas se mantuvieron en entornos temporales.

## Versión 1.2 · 6 de octubre de 2026

- 36 pruebas verificadas en SQLite y PostgreSQL, utilizando bases temporales.
- Baja por despido, renuncia, fin de contrato u otra causa, con cierre atómico de asignación e historial.
- Baja sin casillero, datos desactualizados, operaciones simultáneas y reintento tras pérdida de respuesta.
- Devolución voluntaria manteniendo al empleado activo; disponibilidad condicionada a revisión física.
- Avisos simulados a HR y al empleado, copias opcionales, correos ausentes y destinatarios repetidos.
- Los motivos internos no aparecen en los avisos; solo Administración puede cambiar el destinatario de HR.
- Migración desde el esquema anterior conservando empleados, asignaciones y notificaciones.
- Revisión visual de los formularios de baja, devolución y configuración de avisos.
- Ejecutable independiente verificado: interfaz, servidor, autenticación, baja atómica y aviso simulado único a HR incluso al repetir la solicitud.

Validación realizada en Windows 11 Pro de 64 bits, Python 3.13.15 y PostgreSQL 18.

## Resultados

- 20 pruebas pasaron con SQLite y la interfaz Qt.
- Las mismas 20 pruebas pasaron contra PostgreSQL en un clúster temporal independiente.
- Revisión estática de slms, migraciones y tests: sin errores.
- Prueba del ejecutable independiente: interfaz, migraciones, configuración cifrada, servidor HTTP, autenticación e inventario correctos.
- Revisión visual de las pantallas de resumen, mapa e inventario del ejecutable.

## Casos cubiertos

- Dos solicitudes concurrentes para el mismo casillero o empleado: una única asignación vigente.
- Pérdida de respuesta después de confirmar: reenvío con el mismo UUID sin duplicar efectos.
- Reutilización de UUID con otro contenido: rechazada.
- Reasignación fallida: conserva la asignación original completa.
- Liberación, bajas con asignaciones activas y versiones desactualizadas.
- Casilleros pendientes de verificar: no disponibles para asignación.
- Verificación por bloque: todos los cambios o ninguno.
- Permisos de consulta y rechazo de peticiones sin autenticar.
- Persistencia cifrada de cola y configuración, sesiones vencidas y dependencias de solicitudes.
- Separación de colas por responsable e instalación.
- Coordenadas y contornos: persistencia y rechazo de geometría inválida.
- 2000 casilleros: carga de inventario, mapa y filtrado de disponibilidad.
- Respaldos y restauración comprobada en SQLite y PostgreSQL.
- Protección de las exportaciones CSV frente a fórmulas en campos de texto.
- El asistente no sobrescribe administradores existentes.

Las pruebas utilizaron información ficticia. No se conectaron mediante credenciales extraídas de pgAdmin ni modificaron la base de desarrollo del usuario. Esa conexión se configura localmente en el asistente.

La dependencia Starlette emite una advertencia de deprecación sobre su cliente HTTP de pruebas; no afecta estos resultados. Las versiones quedan fijadas en requirements.txt.

La distribución inicial tuvo una incompatibilidad de DLL detectada durante la prueba. Se corrigió excluyendo del entorno de empaquetado bibliotecas ajenas procedentes del runtime de herramientas. Se reconstruyó y se volvió a verificar el ejecutable corregido.

## Actualización visual 1.1 · 30 de septiembre de 2026

- Tema compartido inspirado en samtec.com, con fuente y logotipo incluidos localmente.
- Paleta explícita para evitar texto blanco sobre fondos claros cuando Windows usa modo oscuro.
- Secciones de conexión y cuenta en el asistente; desplazamiento vertical en pantallas pequeñas.
- Revisión visual del asistente, acceso, resumen, mapa e inventario.
- Prueba de regresión con paleta oscura y cambio entre los tres tipos de conexión.
- Las 21 pruebas de la suite local pasan. Las 20 pruebas de PostgreSQL de la versión inicial se conservan; esta actualización no cambia el esquema ni la lógica de asignaciones.

## Actualización 1.10 · 11 de octubre de 2026

- Suite completa: **126 pruebas** superadas con SQLite y Qt. Revisión estática sin errores.
- Regresión reproducida antes de corregir: el borde cosmético del bloque extendía
  su área invisible y capturaba clics del vecino. Pruebas de rotaciones 0°, 10°,
  11°, 45°, 90° y −10°, tres niveles de zoom, bordes, fondo y halo de búsqueda.
- Comprobación adicional con la geometría del inventario facilitado por el usuario:
  118 bloques y 1.416 casilleros, 3.186 posiciones y 6.372 clics de consulta/contexto
  correctos. El Excel se leyó sin modificaciones y no se importó a la base de datos.
- Deshacer/rehacer probado con arrastres reales de bloques y contornos, atajo de
  teclado, vuelta a la posición inicial, nueva rama de movimientos, refresco y
  guardado. Cada arrastre corresponde a una sola acción; no genera solicitudes
  hasta pulsar Guardar posiciones.
- No cambia el esquema de datos ni la lógica del servidor. No se repitieron las
  pruebas PostgreSQL de la entrega anterior para esta modificación de interfaz.
- Ejecutable 1.10 compilado y comprobado en un perfil temporal independiente:
  selección de etiquetas próximas, deshacer/rehacer, pantallas, inicio del
  servidor, autenticación y baja atómica con aviso simulado sin duplicados.
  Capturas del mapa y su menú revisadas visualmente. La aplicación abierta del
  usuario y su servicio no se detuvieron; se entregó una carpeta de versión nueva.

## Actualización 1.11 · 12 de octubre de 2026

- 133 pruebas completas superadas con SQLite y Qt; revisión estática sin errores.
- Preferencias independientes por cuenta y equipo: Aplicar, Aceptar, Cancelar,
  restauración sin guardar, persistencia, valores inválidos y fallo de escritura.
- Autocompletado de bloques y filas con 10°, modificación individual a 12°,
  cantidades superiores a 12 bloques por fila y edificios ya no disponibles.
- Empleados: valores iniciales editables y conservación de fichas existentes;
  no se rellenan identificadores, nombres ni correos a partir de las preferencias.
- Vista satelital/contornos y escala 90–150% conservan geometría, zoom, posiciones
  pendientes e historial local de Deshacer/Rehacer. Ninguna preferencia crea una
  solicitud ni modifica los datos del servidor.
- Revisión visual de categorías de opciones, ampliación al 125% y mapa de
  contornos con datos ficticios. Sin cambios en el esquema de PostgreSQL.
- Ejecutable 1.11 validado en un perfil aislado: ventana de opciones, persistencia,
  restauración, mapa, autenticación, servidor y avisos simulados sin duplicados.
