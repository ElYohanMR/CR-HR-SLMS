# Guía de operación

## Solicitudes de corte de candado · 1.12

Abre **Cortes de candado** en la barra izquierda. Recepción o HR registra
la comunicación que recibió del supervisor; el programa no lee Teams ni correo.

1. **Nueva solicitud:** selecciona empleado y casillero. Al elegir el empleado
   se propone su casillero asignado, pero puedes cambiarlo si el incidente corresponde
   a otro. Escribe nombre del supervisor, medio de comunicación y motivo libre.
   Guarda y espera la confirmación del servidor. Estado: **Solicitada**.
2. Abre la solicitud y usa **Asignar encargado**. Escribe quién realizará el
   corte. Al confirmarse, pasa a **En proceso**. Cambiar de encargado exige motivo.
3. Convoca al empleado conforme al procedimiento interno y adjunta las tres fotos:
   empleado con su tarjeta Samtec ID en la mano frente al casillero; candado antes;
   candado después. Adjunta una imagen por paso y espera su sincronización.
   Se admiten JPG/PNG de hasta 6 MB y 24 megapíxeles; se conserva el archivo original.
4. **Finalizar:** registra fecha/hora real del corte, detalle del resultado y
   confirma presencia del empleado y verificación de su ID. Se exigen las tres
   evidencias confirmadas y un encargado. Estado: **Finalizada**.

**Cancelar solicitud** exige motivo y conserva el expediente. Los datos iniciales
se editan mientras está Solicitada. Empleado/casillero identifican el expediente:
si se eligieron incorrectamente, cancela y crea uno nuevo. En proceso puedes
sustituir una fotografía indicando el motivo; las anteriores siguen consultables.
Las solicitudes Finalizadas o Canceladas no se reabren ni se borran.

El historial distingue al empleado, supervisor y encargado del corte de la cuenta
de Recepción/HR que registró cada cambio. Se conservan datos de identificación del
momento de creación, fechas, responsables y valores anteriores/posteriores.
**Ver historial de la solicitud** consulta el expediente completo con conexión.
Las fotografías requieren una sesión de Operación o Administración y conexión.
La cuenta de Consulta puede ver el seguimiento, pero no las fotos.

La lista permite buscar, filtrar por estado, ordenar por columnas, marcar filas
y abrir expedientes con doble clic o clic derecho. No permite dos solicitudes
abiertas simultáneas para el mismo casillero. Un corte no modifica su asignación.
Los casilleros con expedientes no se pueden eliminar definitivamente.

Sin conexión se conserva el paso que guardaste, con su foto cifrada localmente
cuando corresponde. Espera la confirmación antes del siguiente paso. Los errores
y conflictos aparecen en **Solicitudes**, donde puedes revisar el resultado y
abrir el expediente actualizado. Las fotos confirmadas forman parte del respaldo
de la base de datos; las todavía pendientes solo están en el equipo que las guardó.

La primera apertura del servidor 1.12 aplica la migración 0006, que añade tablas
sin cambiar el inventario. Si sigue ejecutándose un servidor anterior, guarda tu
trabajo, reinicia Windows y abre el acceso directo actualizado. Un servidor remoto
también debe actualizarse antes de utilizar este apartado.

## Ventana de opciones · 1.11

El botón **Opciones** abre una ventana con categorías a la izquierda. El menú
anterior se conserva en **Acciones**. Las preferencias pertenecen a la cuenta
que inició sesión y a este equipo; no modifican datos existentes ni se envían
como solicitudes al servidor.

- **Apariencia:** tamaño del texto y controles: 90%, 100%, 110%, 125% o 150%.
  Si el contenido no cabe, puedes desplazarte con las barras de la ventana.
  Los bloques mantienen su tamaño respecto al mapa.
- **Mapa:** imagen satelital o solo contornos y bloques. Conserva coordenadas,
  proporciones, zoom, movimientos pendientes y Deshacer/Rehacer.
- **Bloques y filas:** edificio, lado, interior/exterior, filas, columnas,
  rotación, prefijo y cantidad de bloques de una fila. Valores iniciales: 4×3
  casilleros y 10° de rotación. El plano y posición provienen del mapa actual.
- **Empleados:** departamento, turno, estado activo y notas iniciales. El ID,
  nombre, apellidos y correo se completan individualmente.

Los predeterminados son sugerencias editables: con 10° configurados puedes
crear un bloque o una fila con 12° sin cambiar la preferencia. Editar un registro
existente muestra sus datos guardados. La importación de Excel conserva los
valores del archivo.

**Aplicar** guarda y aplica sin cerrar. **Aceptar** guarda y cierra. **Cancelar**
descarta lo modificado desde el último Aplicar. **Restaurar valores iniciales**
rellena la ventana con los originales; debes Aplicar o Aceptar para guardarlos.

## Marcar varias filas

Todas las tablas tienen casillas junto al primer dato de cada fila. Puedes marcar varias sin mantener pulsado Ctrl. Clic derecho permite **Marcar todas las filas visibles**, **Desmarcar todas las filas visibles** y **Copiar filas marcadas**. Las marcas se conservan al ordenar o sincronizar por identificador; una fila que desaparece por un filtro queda desmarcada. La fila resaltada y las casillas son selecciones independientes: las acciones individuales siguen usando la fila pulsada.

En **Inventario → Más acciones → Elementos eliminados / restaurar**, marca los bloques o casilleros y pulsa **Restaurar marcados**. Revisa la lista y escribe un motivo. El servidor aplica todo el lote o ninguno. Marcar un bloque y sus casilleros no duplica la restauración. Los casilleros que se eliminaron antes que el bloque solo se recuperan si también los marcas. Los restaurados quedan pendientes de verificación física.

## Eliminar inventario definitivamente

Solo la cuenta administradora inicial ve **Eliminar definitivamente marcados** en Elementos eliminados. Esta identidad se guarda al crear la instalación y no depende del nombre de usuario ni de que otra cuenta tenga rol Administrador. El servidor vuelve a comprobar el permiso en cada solicitud. Otras cuentas no pueden modificar la cuenta inicial.

Marca bloques/casilleros que ya estén eliminados, revisa la lista y el número de casilleros incluidos, escribe un motivo y confirma escribiendo **ELIMINAR**. Un bloque incluye todos sus casilleros, incluso los eliminados por separado. Cuando el servidor confirma, los registros desaparecen definitivamente y sus códigos pueden reutilizarse. No se pueden restaurar desde la aplicación; se conserva la auditoría de la operación.

Para conservar el historial de uso, no se permite eliminar definitivamente casilleros con asignaciones, presentes o pasadas, ni incluidos en revisiones físicas. Un conflicto, cambio de versión o elemento protegido cancela todo el lote. La función sirve para retirar inventario creado por error o para pruebas que todavía no tenga ese historial; no borra empleados ni el historial general.

Abre la aplicación actualizada para cargar su servicio local. Si sigue activo un servidor anterior, reinicia Windows y vuelve a abrirla. Las nuevas acciones por lote requieren que el servidor anuncie esta función.

## Crear una fila de bloques

En **Mapa → Opciones del mapa → Crear fila de bloques**, marca el primer y el último punto de la pared. También puedes hacer clic derecho en el inicio y elegir **Crear fila desde aquí**. Clic derecho cancela la selección. Guarda primero cualquier posición o contorno que hayas modificado.

Indica edificio, lado, cantidad, prefijo, inicio del nombre y primer número de casillero. Por ejemplo, 40 bloques, prefijo E e inicio 01 producen E01 a E40, distribuidos uniformemente entre los extremos. Las dimensiones predeterminadas son 4 filas y 3 columnas, editables. La numeración conserva ceros iniciales y avanza de derecha a izquierda y de arriba hacia abajo.

Revisa la vista previa y la tabla antes de pulsar **Crear fila**. Puedes volver a editar o cancelar sin crear nada. El servidor confirma toda la fila en una operación; un número duplicado o conflicto cancela todo el lote. Los casilleros nuevos quedan pendientes de verificación. Las etiquetas mantienen el mismo tamaño relativo al mapa.

Si ya existen E01–E05 y quieres una fila E01–E40, la herramienta reubica los cinco existentes y crea los restantes. Deben coincidir plano, dimensiones y numeración física. La vista previa distingue **Reubicar** de **Crear** y muestra el lado de cada bloque. Los existentes conservan su lado registrado; el elegido en el formulario se aplica a los nuevos. Conserva los identificadores, asignaciones e historial.

Si los eliminaste, ve primero a **Inventario → Más acciones → Elementos eliminados / restaurar**, restáuralos y sincroniza; luego crea la fila completa. La eliminación es reversible y mantiene reservados los códigos. Vaciar el historial no libera esos códigos y no es necesario para este procedimiento. Si eliminaste casilleros individualmente antes de eliminar su bloque, restáuralos también.

## Revisiones físicas

Abre **Inventario → Más acciones → Revisiones físicas**. Crea una revisión con nombre y filtros de edificio, lado o bloque. El recorrido conserva la lista de casilleros seleccionados. Después de sincronizar puedes retomarlo desde otro equipo.

Selecciona un casillero y registra el resultado con doble clic, clic derecho o **Registrar resultado**:

- **Vacío y utilizable**: habilita su asignación si no tiene una persona registrada.
- **Ocupación coincide con la asignación**: confirma la observación sin cambiar la asignación.
- **Ocupado sin identificar**, **No coincide con el sistema** o **No se encontró físicamente**: registra una discrepancia y deja el casillero pendiente.
- **Dañado / necesita mantenimiento**: registra el daño y la condición de mantenimiento.

Las discrepancias requieren observaciones. Ningún resultado libera automáticamente una asignación. Resuelve las devoluciones o cambios desde las acciones habituales del empleado/casillero. Se conserva responsable, hora de confirmación y hora local declarada de la observación.

Puedes filtrar por pendientes o discrepancias y exportar la vista a CSV. Sin conexión, las observaciones quedan **Por sincronizar**; no representan resultados confirmados. Para cerrar la revisión, todos los casilleros deben estar revisados y confirmados. Cerrar conserva las discrepancias; no las resuelve. Una revisión cerrada ya no acepta cambios. Para otro recorrido, crea una nueva.

## Resolver conflictos

En **Solicitudes**, haz clic derecho sobre un conflicto o rechazo y elige **Resolver conflicto…**. Verás la solicitud original junto a la última información recibida y su fecha. Usa **Sincronizar información** antes de decidir.

**Preparar corrección** abre un formulario con el estado actual para asignaciones, devoluciones, edición de empleados, bloques y casilleros, eliminaciones y observaciones físicas. Revisa y guarda explícitamente. Se crea una solicitud distinta, relacionada con la original; el resultado original se conserva. Mientras una corrección esté pendiente o confirmada, el asistente evita preparar otra desde ese conflicto.

Los lotes de inventario y otras operaciones se preparan nuevamente desde su sección correspondiente. El asistente lo indica; no vuelve a enviar un lote ni fuerza versiones antiguas.

## Clic derecho y pantallas simplificadas

Haz clic derecho sobre cualquier fila: el menú selecciona esa fila y muestra sus acciones. En Inventario puedes abrir, asignar o liberar el casillero, consultar o editar su bloque y eliminar el casillero o el bloque completo. En Empleados puedes editar, asignar, liberar o dar de baja. En Solicitudes puedes consultar el detalle, reintentar un error temporal o iniciar sesión cuando corresponde. Las cuentas, historial, notificaciones y listas de consulta también tienen menú contextual. Todas las filas permiten consultar sus datos y copiar un valor o la fila.

Las acciones se habilitan según el estado y los permisos de tu cuenta. Eliminar sigue solicitando un motivo y no permite quitar casilleros ocupados. Las importaciones, exportaciones y plantillas están agrupadas en **Más acciones**; las herramientas del mapa están en **Opciones del mapa**. El menú **Opciones** de la cabecera conserva los accesos generales.

En el mapa, haz clic derecho sobre un bloque para consultar, editar, verificar o eliminar. Haz clic derecho sobre un lugar vacío del plano y elige **Nuevo bloque aquí**: se abre el formulario con las coordenadas del clic y el plano actual, incluso después de acercar o desplazar la vista. Confirma edificio, lado y numeración antes de guardar.

## Orden físico de los casilleros

Las etiquetas del mapa mantienen un tamaño fijo respecto al plano. Se amplían o reducen junto con la imagen al usar el zoom; añadir o acercar otros bloques ya no cambia su tamaño. Si dos etiquetas se superponen, separa sus posiciones en Editar mapa.

La vista del bloque se lee de frente: el primer casillero está arriba a la derecha y la secuencia avanza hacia la izquierda, luego continúa en la siguiente fila hacia abajo. Por ejemplo, un bloque de 4 × 3 que empieza en 1105 muestra:

| Izquierda | Centro | Derecha |
| --- | --- | --- |
| 1107 | 1106 | 1105 |
| 1110 | 1109 | 1108 |
| 1113 | 1112 | 1111 |
| 1116 | 1115 | 1114 |

En Inventario y archivos de importación/exportación, **columna 1 significa la derecha**, columna 2 la siguiente hacia la izquierda, etc. Fila 1 es la superior. Los números, identificadores, asignaciones e historial existentes se conservan; se corrige la representación visual del bloque.

## Ordenar las tablas

Haz clic en cualquier encabezado de columna para ordenar sus filas. El primer clic ordena de menor a mayor o de A a Z (▲); otro clic invierte el orden (▼). Funciona en Empleados, Inventario, Solicitudes, Historial, Administración y las listas de consulta e importación.

Los números, códigos y fechas se ordenan por su valor: 2 aparece antes de 10 y N2 antes de N10. Los ID conservan sus ceros iniciales. El orden y la selección se conservan al sincronizar o filtrar mientras el registro seleccionado siga visible. Al cerrar y volver a abrir el programa se recupera el orden inicial de cada lista.

## Cuentas

El botón **Opciones**, en la cabecera, reúne conexión y solicitudes, mapa, inventario, empleados, administración, respaldos, historial y ayuda. Las acciones que tu cuenta no puede realizar aparecen deshabilitadas.

Si la sesión vence, las solicitudes pasan a **Requiere sesión** y aparece **Iniciar sesión para enviar solicitudes pendientes**. Al abrir la aplicación con una sesión vencida se solicita nuevamente el acceso. Inicia sesión con la cuenta que creó las solicitudes: se enviarán automáticamente conservando sus identificadores. No vuelvas a pulsar Eliminar para la misma solicitud pendiente; la aplicación evita duplicarla. Si una versión anterior guardó dos eliminaciones del mismo elemento, el servidor confirma que ya estaba eliminado sin repetir el cambio.

**Opciones → Conexión y solicitudes** permite sincronizar, abrir la cola, reintentar pendientes o consultar el estado. Una solicitud pendiente o que requiere sesión todavía no confirma una eliminación. Los conflictos deben revisarse antes de generar otra solicitud.

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

Los bloques nuevos proponen **4 filas × 3 columnas (12 casilleros)**. Puedes cambiar ambos valores antes de crearlos. Los bloques ya registrados conservan sus dimensiones.

En el mapa escribe el **código completo del bloque o número de casillero** y presiona **Enter**. También puedes usar el código completo de ubicación. La búsqueda incluye todos los planos y permite elegir si un código corresponde a varios bloques. El mapa centra el resultado y muestra un halo azul exterior que sube y baja de intensidad, un segundo por transición. Los colores de disponibilidad se mantienen; seleccionar un bloque apaga la animación. Las etiquetas miden una quinta parte de su ancho y alto anteriores a igual acercamiento.

En **Inventario** están **Eliminar casillero seleccionado**, **Eliminar bloque…** y **Elementos eliminados**. También puedes eliminar desde la ficha del casillero o la cuadrícula del bloque. Solo Administración puede hacerlo; indica un motivo. Eliminar un bloque quita también sus casilleros. Primero deben liberarse todas sus asignaciones activas. Los cambios se confirman en Solicitudes y una versión desactualizada produce un conflicto sin eliminación parcial.

La eliminación conserva historial, responsable y fecha, pero oculta el elemento del mapa y del inventario. Sus códigos permanecen reservados. **Elementos eliminados → Restaurar seleccionado** permite recuperarlo; restaura primero su bloque si también fue eliminado. Los casilleros restaurados quedan pendientes de verificación y no recuperan antiguas asignaciones. Restaurar un bloque no restaura casilleros eliminados individualmente antes de eliminar ese bloque.

Confirma los edificios antes de registrar bloques. Para interiores, crea un plano por edificio y nivel. En Nuevo bloque indica filas y columnas según la disposición física. Los números individuales se escriben separados por comas, por filas de derecha a izquierda y de arriba hacia abajo. También puedes generar una secuencia desde un primer número.

Los números físicos deben ser únicos en esta instalación. Si se repiten entre edificios, establece primero una convención que los distinga.

En Editar mapa arrastra bloques o puntos rojos de los contornos. Guarda y espera la confirmación antes de volver a editar. Abrir un bloque permite ver su cuadrícula. La verificación por bloque afecta únicamente los casilleros pendientes; confirma esta acción solo después de comprobar físicamente que todos esos casilleros están vacíos y utilizables.

En **Consultar**, un clic en la etiqueta abre el detalle con disponibles/asignados y **Ver asignaciones del bloque** (casillero, ID, nombre y apellidos). Verde significa que hay casilleros verificados disponibles; rojo significa que todos están asignados; ámbar significa que no hay disponibles pero no todos están asignados (por verificar, mantenimiento o retirados). Los colores reflejan la última sincronización confirmada, no solicitudes pendientes.

Las etiquetas muestran únicamente el código y conservan un tamaño fijo respecto al mapa, incluso en filas de 40 bloques. Acerca con la rueda para leerlas y arrastra el fondo para recorrer la pared; Ajustar vista vuelve al plano completo. Los bloques colocados exactamente en la misma posición deben separarse en Editar mapa. La imagen conserva su proporción; X e Y continúan expresándose de 0 a 1000 respecto al ancho y alto.

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
## Mapa: selección precisa y movimientos reversibles · 1.10

Los clics y el clic derecho corresponden al cuadrado visible del bloque, incluida
su rotación. El halo azul de búsqueda no captura clics destinados al bloque vecino.
El tamaño de las etiquetas respecto al plano se conserva al acercar o alejar.

En **Editar mapa**, cada arrastre de un bloque o de un punto del contorno puede
deshacerse desde **Opciones del mapa → Deshacer** o desde el menú de clic derecho.
Con el foco en el mapa, **Ctrl+Z** deshace y **Ctrl+Y** rehace. Se conservan hasta
100 movimientos de la sesión de edición. Volver a la posición original quita ese
bloque de los cambios pendientes de guardar.

Estas acciones afectan solamente movimientos sin guardar. Guardar posiciones,
salir de edición, recargar/cambiar el plano o iniciar una fila termina ese historial
local. No deshacen solicitudes enviadas, asignaciones ni eliminaciones.
