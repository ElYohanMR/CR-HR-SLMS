# Microsoft y correo · entrega para TI
Versión 1.14.0 · 14 de octubre de 2026

## Funciona en esta entrega
- Inicio local con usuario y contraseña existente.
- Vista previa editable de Para, CC, Asunto y Mensaje, con copia por campo.
- Borradores cifrados con DPAPI por cuenta, aviso e instalación en LocalStore.
  Se guardan solo en esa computadora, sin alterar el aviso original ni la auditoría.
- Apertura mediante mailto en la aplicación predeterminada del sistema. Si esa
  aplicación es Outlook, abre un borrador allí. El usuario revisa y pulsa Enviar.
  No instala ni configura Outlook; no selecciona automáticamente la cuenta remitente.
- Plantillas de asignación, traslado, devolución y baja con fecha de confirmación
  en Costa Rica, persona que registró y contacto HR cuando está configurado.
  Las bajas se dirigen a HR y no incorporan motivos internos ni notas privadas.
- Botón Microsoft y opciones de envío directo/automático visibles y deshabilitados.

## Lo que todavía no está implementado
No hay conector MSAL, validación de tokens Microsoft, envío Graph ni confirmación
de entrega. No basta con cambiar un indicador o rellenar los IDs del ejemplo.
El archivo config/microsoft.example.json (Microsoft-configuracion-ejemplo.json
en el paquete) documenta los valores a acordar; no es
leído por esta versión. TI o el equipo de desarrollo debe implementar y validar
los conectores descritos a continuación antes de habilitar los botones.

## Identidad
1. Registrar aplicación de escritorio y API de SLMS en el tenant de Samtec.
2. Usar MSAL con navegador del sistema y authorization code + PKCE. Aplicación
   pública: ningún client_secret en escritorio, ejecutable o repositorio.
3. El cliente obtiene un access token destinado a la API de SLMS. No reutilizar
   un token de Graph ni aceptar un ID token como autorización de operaciones.
4. Añadir un endpoint de intercambio que valide firma con JWKS, issuer, audience,
   tenant, expiración y scope. Vincular (tid, oid) a una cuenta local y permisos
   explícitos. No conceder acceso por el sufijo @samtec.com ni por coincidencia
   de correo. No crear administradores automáticamente.
5. Emitir la sesión propia de SLMS para reutilizar su autorización por rol,
   revocación y cola. Mantener la cuenta local de recuperación controlada por TI.
6. Definir comportamiento de cierre, cambio de cuenta, bloqueo y operaciones
   pendientes cuando se revoca la identidad. Guardar caché MSAL protegida.
Puntos de conexión: slms/setup.py (login_form/login), slms/microsoft_ui.py,
slms/api.py (login, actor y sesiones), slms/sync.py (sesión y reintentos).
La autenticación actual continúa intacta; no existe una ruta alternativa abierta.

## Correo manual y automático
- slms/notifications.py genera el aviso dentro de la transacción confirmada.
  Notification.command_id único impide duplicar el aviso por reintento del comando.
- slms/mail_preview.py maneja borradores locales y mailto. El resultado de
  QDesktopServices.openUrl significa solicitud de apertura, nunca envío.
- Acordar remitente: cuenta del operador para envío delegado, o buzón de servicio
  para envío automático desde el servidor. Inicio de sesión y permiso Mail.Send
  son autorizaciones distintas.
- Para envío automático: proceso servidor, permiso mínimo y acceso limitado al
  buzón autorizado conforme al mecanismo elegido por TI. Certificado/secreto
  solo en el almacenamiento de secretos del servidor. No ejecutar Outlook COM
  en los puestos ni depender de que el cliente permanezca abierto.
- Implementar una bandeja de salida con estados pendiente, en proceso, aceptado
  por Microsoft, fallido y resultado incierto. La respuesta HTTP 202 de Graph
  acredita aceptación para procesamiento, no entrega al destinatario.
- Una respuesta perdida no debe provocar reenvíos ciegos: reconciliar el resultado
  o solicitar revisión. Manejar límites, Retry-After, expiración y permisos revocados.
- Decidir cómo se autoriza y versiona un borrador editado que se envía por Graph.
  El envío automático debe tomar un contenido confirmado del servidor, no leer
  silenciosamente borradores locales de otro usuario.
- Activar automática por evento de forma explícita. Registrar remitente,
  destinatarios, contenido aprobado, usuario, fecha y resultado.
- No cambiar la asignación/baja ya confirmada si falla el correo.
- La tabla actual mantiene estados históricos simulado/sin_destinatario; presentar
  borradores como Sin envío desde SLMS y nunca convertir los históricos a enviados.

## Verificación antes de habilitar
Probar tenant incorrecto, token vencido, audiencia/scope incorrectos, cuenta sin
rol, cambio/revocación de cuenta y aislamiento de borradores. Para correo probar
buzón autorizado, envío a direcciones ficticias controladas por TI, fallo de red,
respuesta perdida, límites Graph y prevención de duplicados. Habilitar producción
solo después de revisar permisos, remitente y procedimiento de soporte.

## Referencias oficiales
- Identidad: https://learn.microsoft.com/en-us/entra/identity-platform/app-sign-in-flow
- Marca y botón: https://learn.microsoft.com/en-us/entra/identity-platform/howto-add-branding-in-apps
- Graph sendMail: https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0
