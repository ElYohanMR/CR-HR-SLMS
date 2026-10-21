# SLMS 1.14.1 — Evaluación de RH, Recepción y TI

Entrega para revisión funcional, técnica y preparación de un piloto controlado.
Programa Windows 1.14.1; documentación de entrega actualizada el 20 de octubre de 2026.
No representa aprobación de producción. No se modificó el código funcional del
ejecutable para esta actualización documental.

## Archivos

- **Samtec-Lockers-Windows.zip:** extraer completo y ejecutar SamtecLockers.exe.
  Mantener _internal junto al EXE. Los puestos remotos no requieren Python ni PostgreSQL.
- **Samtec-Lockers-Codigo.zip:** código y documentación del commit de entrega.
- **SLMS_Instruccion_de_trabajo.docx:** procedimientos de uso y permisos.
- **SLMS_Capacitacion_RH_Recepcion.pptx:** capacitación con notas de exposición.
- **SHA256.json / PROCEDENCIA.txt:** integridad y relación con la versión fuente.

Los documentos editables quedan sujetos a revisión y control documental de Samtec.
La documentación más reciente de despliegue está en docs/DESPLIEGUE_TI.md del
repositorio y del ZIP fuente. El ZIP Windows conserva su documentación empaquetada
original; consultar las precisiones de TLS y despliegue añadidas al repositorio.

## Alcance

Inventario, mapa, empleados, asignaciones y movimientos, revisiones físicas,
cortes de candado, historial, permisos, cola local y borradores editables de correo.
Incluye ocho órdenes configurables de numeración y el encabezado actualizado.

El acceso con Microsoft y el envío automático requieren implementación con TI.
Android, iOS, consola administrativa ampliada y nuevos ajustes son propuestas
documentadas en docs/ROADMAP.md. No están incluidos como funciones actuales.

## Instalación y datos

Configurar un único servidor central y conectar los puestos a su URL HTTPS.
La versión actual requiere validar la confianza del certificado en el cliente
HTTPX/certifi; no basta instalar una CA corporativa en Windows. Ver guía de TI.
GitHub no aloja el servicio operativo. La base de datos y el inventario mapeado
deben transferirse separadamente: no están dentro de estos descargables.

## Validación

Se comprobó integridad de los archivos de entrega y correspondencia del código
funcional con el paquete 1.14.1 anterior. Esta entrega cambia documentación y
configuración del repositorio; no repite ni sustituye las pruebas funcionales
anteriores ni la aceptación en la red de TI. Consultar docs/VALIDACION.md y
completar docs/ENTREGA_TI.md en el piloto.
