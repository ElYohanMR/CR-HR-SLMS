# SLMS 1.14.5

Versión para evaluación de RH, Recepción y TI. Preparación de la entrega: 27 de octubre de 2026.

## Cambios desde 1.14.1

- Icono de SLMS en la barra de tareas de Windows.
- Mantenimiento automático mientras existe un corte de candado abierto. Finalizar
  o cancelar recupera la condición prevista, conserva la asignación y no cambia
  automáticamente el atributo Tiene candado.
- Detalle de auditoría con Antes y Después y campos modificados resaltados.
- Historial por fechas Desde/Hasta, con paginación y días completos de Costa Rica.
- Recuadro de detalle del mapa fijo durante arrastre, desplazamiento y zoom.
- Sincronización configurable de 5 a 300 segundos, inicialmente 10, por cuenta y equipo.
- Actualización visual que evita reconstruir tablas y elementos del mapa sin cambios.
- Guías de entrega revisadas y plantilla CSV vacía incluida en el código.

## Actualización

1. Respaldar la base y comprobar la recuperación en un entorno separado.
2. Resolver solicitudes pendientes y detener el servidor antes de reemplazar archivos.
3. Distribuir el paquete completo, con su carpeta `_internal`, conservando la
   identidad de Windows y la carpeta de datos configuradas.
4. El arranque aplica las migraciones pendientes. `0008_cut_maintenance` añade
   la condición posterior al corte y ajusta solicitudes abiertas existentes.
5. Validar acceso, cortes, historial, sincronización y respaldos antes de habilitar usuarios.

Volver al ejecutable anterior no revierte la migración. El plan de recuperación
debe conservar una combinación compatible de programa y base.

## Distribución y límites

El repositorio es público. Los WI, presentaciones, inventario y contornos se
entregan por el canal interno de Samtec. No incluir bases, credenciales, empleados
ni evidencias en GitHub. El ZIP automático de código no es el programa compilado.

Microsoft, correo automático, Android e iOS siguen pendientes de desarrollo e
integración. Las pruebas locales no equivalen a aprobación de producción.
Consultar [Validación](VALIDACION.md) y [Despliegue TI](DESPLIEGUE_TI.md).
