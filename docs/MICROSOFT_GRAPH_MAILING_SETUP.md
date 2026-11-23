# CONCEDE Motor V3 — Mailing Microsoft 365

El módulo de Mailing se incorpora como pestaña independiente. No altera `core.py`, `concede_v3.json` ni el contrato matemático de Score V3.

## Configuración ya preparada

La aplicación usa `DATABASE_URL` y la sección `[mailing]` de Streamlit Secrets. El remitente está restringido a `C@4msfts.com`. Redirect URI Web: `https://concede-motor-v3.streamlit.app/`.

Permisos delegados Microsoft Graph: `User.Read` y `Mail.Send`. No se requieren permisos de aplicación.

## Guardrails

- Contactos aptos requieren correo válido, fuente y autorización afirmativa.
- Contactos y borradores se aíslan por workspace en tablas `mailing_contacts` y `mailing_campaigns`.
- Identidad del buzón se valida al conectar y antes de cada envío.
- Envío BCC, límite de 500 destinatarios, aprobación humana explícita.
- No hay lectura de bandeja, envíos automáticos ni campañas programadas.
- HTTP 202 significa aceptación de Graph, no confirmación de entrega.
- Los tokens OAuth permanecen en sesión y los secretos fuera del repositorio.
