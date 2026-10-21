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
- **SLMS_Inventario_Inicial_2026-10-20.xlsx:** 118 bloques y 1.416 casilleros, sin empleados.
- **SLMS_Contornos_2026-10-20.json:** contornos del mapa actual; cargar antes del inventario.
- **SLMS_Plantilla_Empleados.xlsx / .csv:** plantilla vacía y guía de campos obligatorios/opcionales.
- **00_LEER_PRIMERO.txt:** orden de instalación y carga.
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
GitHub no aloja el servicio operativo. La Release incluye únicamente la distribución
inicial del inventario y los contornos, sin empleados ni asignaciones. La base completa
y sus credenciales no se incluyen. Seguir docs/CARGA_INICIAL.md antes de importar.

## Validación

Se comprobó integridad de los archivos de entrega y correspondencia del código
funcional con el paquete 1.14.1 anterior. Esta entrega cambia documentación y
configuración del repositorio y añade una utilidad de contornos. Se probó la carga
completa en una base SQLite temporal mediante la API: 118 bloques, 1.416 casilleros,
numeración y geometría conservadas, sin empleados ni asignaciones. No sustituye
las pruebas anteriores ni la aceptación sobre PostgreSQL y la red de TI. Consultar docs/VALIDACION.md y
completar docs/ENTREGA_TI.md en el piloto.
