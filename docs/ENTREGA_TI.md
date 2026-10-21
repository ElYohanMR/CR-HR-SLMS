# Revisión y aceptación de entrega

Versión de referencia: 1.14.1. Documento preparado el 20 de octubre de 2026.
Marcar únicamente lo que haya sido verificado por el responsable correspondiente.

## Material disponible

- [ ] Repositorio privado accesible a los revisores invitados.
- [ ] Release con ejecutable, código de la etiqueta, WI, presentación y SHA-256.
- [ ] Guías de despliegue, operación, Microsoft y propuestas futuras revisadas.
- [ ] Datos operativos transferidos separadamente, cuando se autorice su carga.

## Responsabilidades a completar por TI y RH

| Asunto | Responsable / valor acordado |
| --- | --- |
| Propietario del repositorio y acceso de equipo | Por definir |
| Custodia del administrador inicial de SLMS | Por definir |
| Alojamiento, cuenta Windows y URL HTTPS | Por definir |
| Base PostgreSQL y gestión de secretos | Por definir |
| Soporte, actualizaciones y recuperación | Por definir |
| Respaldos y retención de evidencia | Por definir |
| Aprobación funcional de RH y Recepción | Por definir |
| Código, revisión y aprobación del WI | Por definir |

## Prueba de aceptación en entorno separado

- [ ] Inicio del servidor después de reiniciar Windows y sin sesión interactiva.
- [ ] HTTPS válido desde el cliente SLMS, no solo desde navegador.
- [ ] Tres puestos usan la misma instalación y ven cambios confirmados.
- [ ] Dos intentos sobre el mismo casillero no crean dos asignaciones activas.
- [ ] Pérdida de red: pendientes visibles, recuperación y conflicto explicado.
- [ ] Reintentar una solicitud confirmada no duplica sus efectos.
- [ ] Roles de consulta, operación y administración comprobados.
- [ ] Eliminación definitiva limitada al administrador inicial y a datos elegibles.
- [ ] Importación/exportación, ceros iniciales y numeración física comprobados.
- [ ] Devolución y baja dejan la condición física correcta.
- [ ] Corte sin fotografías se finaliza con los datos y confirmaciones requeridos.
- [ ] Correo manual editado y enviado desde el cliente de correo; no simular entrega.
- [ ] Restauración real en base separada y verificación de inventario y evidencias.
- [ ] RH/Recepción revisaron el WI y la capacitación y registraron observaciones.

## Estado y límites

El acceso con Microsoft y el envío automático siguen pendientes de implementación.
Android, iOS, consola de TI y ajustes ampliados son propuestas del roadmap.
Las pruebas anteriores no acreditan por sí solas aceptación de la infraestructura
corporativa ni de los procedimientos internos.

Formato de observación: flujo, pasos, resultado esperado, resultado observado,
prioridad, responsable y evidencia con datos ficticios o debidamente protegidos.
Usar las plantillas de Issues del repositorio para el seguimiento.
