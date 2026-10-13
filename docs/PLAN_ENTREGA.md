# Propuesta para cerrar la primera entrega
Fecha: 13 de octubre de 2026

Este documento propone trabajo futuro. No declara implementadas las mejoras.
La versión 1.13.1 únicamente reorganiza Cortes de candado debajo de Inventario.

## Situación verificada
Existen inventario, mapa, empleados, asignaciones, bajas, cortes, fotografías
opcionales, historial, cola sin conexión, revisiones físicas, importación,
exportación, permisos por rol, respaldos manuales y preferencias locales.
El correo está simulado y no hay inicio de sesión corporativo Microsoft.
Las opciones actuales incluyen Apariencia, Mapa, Bloques y filas y Empleados.

## Prioridad para la puesta en uso
1. Piloto con Recepción y HR en dos o tres equipos: asignación simultánea del mismo
   casillero, corte sin fotos, devolución, baja, desconexión y reconexión.
   Aceptación: una sola asignación vigente, pendientes visibles y conflictos
   resueltos sin perder historial. Validar también importación y restauración.
2. Con TI: alojamiento central, HTTPS, inicio automático del servicio, respaldo
   programado con copia fuera del equipo, restauración comprobada y responsable
   de soporte. Definir tiempos aceptables de recuperación y pérdida de datos.
3. Correo: integrar envío real si forma parte del alcance de entrega; en caso
   contrario, documentar el aviso manual. Diferenciar pendiente, enviado y fallido.
4. Acceso: recuperación de cuenta, reemplazo del administrador inicial, bloqueo
   por inactividad y permisos de exportación y consulta de fotografías.
5. Cierre funcional: lista priorizada de observaciones del piloto y criterios de
   aceptación de HR/TI. Después preparar WI y presentación con la versión estable.

## Mejoras de uso propuestas
- Recordar ancho y orden de columnas, filtros y última vista por usuario.
- Renombrar Solicitudes como Sincronización para distinguirla de Cortes de candado.
  Debe seguir accesible a operadores que necesitan resolver sus propios envíos.
- Folio legible de corte, fecha objetivo y alertas de solicitudes atrasadas.
  Permitir rectificaciones documentadas de expedientes cerrados sin sobrescribir
  los valores originales.
- Informe de ocupación por edificio y bloque, cortes y pendientes por período.
- Alertas basadas en revisiones existentes: ocupado sin identificar, candado sin
  asignación o diferencias con el inventario. Una alerta no libera automáticamente
  un casillero ni considera verificado su estado físico.

## Organización de ajustes propuesta
| Categoría | Alcance |
| --- | --- |
| Apariencia y listas | Personal: escala, columnas, filtros y vista inicial |
| Mapa | Personal: fondo, vista inicial y tamaño legible de etiquetas |
| Valores predeterminados | Personal: bloques, empleados y Tiene candado |
| Operación | Empresa: turnos, departamentos, responsables y motivos frecuentes con texto libre |
| Conexión y notificaciones | Empresa/TI: estado del servicio, correo y prueba de conexión |
| Seguridad y mantenimiento | Administración/TI: acceso, respaldos, recuperación y diagnóstico |

Mostrar quién puede cambiar cada ajuste y si afecta solo al equipo o a todos.
Mantener Aplicar, Aceptar y Cancelar; añadir restauración por categoría.
No ofrecer cambios de política corporativa como preferencias locales.

## Integraciones posteriores
- Microsoft Entra ID para inicio de sesión corporativo, sin copiar la contraseña
  del correo a la aplicación. Requiere registro y configuración por TI.
  Referencia: https://learn.microsoft.com/en-us/entra/identity-platform/app-sign-in-flow
- Fuente autorizada de HR para conciliación por ID. Microsoft Graph expone datos
  de identidad, pero no debe presumirse que una cuenta deshabilitada equivale a
  despido ni que los atributos laborales estén disponibles o actualizados.
  Referencia: https://learn.microsoft.com/en-us/graph/api/resources/user?view=graph-rest-1.0
- QR con identificador estable y vista autenticada; futuras consultas móviles.
- SharePoint para WI y documentación aprobada, sin presuponer que sustituye la
  base operativa. Informes gerenciales y nuevas sedes según necesidad confirmada.

## Preparación técnica futura
Mantener identificadores internos estables separados de números visibles;
versionar cambios de esquema; documentar la API y permisos; separar envío de
avisos de las operaciones; proporcionar un ambiente de práctica independiente.
Las actualizaciones deben poder instalarse y recuperarse mediante un procedimiento
de TI sin depender del equipo personal del desarrollador.
