# CONCEDE V3 — Modelo de Necesidad v1.0
## PASO 5.3 — Reglas operativas parametrizadas

**Estado:** PROPUESTA V3 — lista para revisión y simulación.

### Fórmula
`Score_Necesidad = 0.25*A + 0.25*F + 0.25*T + 0.25*U`

A = Almacenamiento · F = Flota · T = Tecnología · U = Urgencia/Estacionalidad.

Todas las variables usan escala 0/25/50/75/100 y peso 25%.

## NEC-A-01 — Almacenamiento
**Pregunta:** ¿Cómo está resuelta actualmente la operación de almacenamiento de la empresa?

| Código | Respuesta | Score |
|---|---|---:|
| NO_APLICA | No requiere almacenamiento / no aplica | 0 |
| SIMPLE | Almacenamiento simple, sin complejidad identificada | 25 |
| REGULAR | Requiere operación regular de almacenamiento | 50 |
| MULTIPLE_COMPLEJO | Varias instalaciones o mayor complejidad operativa | 75 |
| CRITICO_COMPLEJO | Almacenamiento crítico / operación altamente compleja | 100 |

**Evidencia:** respuesta documentada del prospecto durante validación.

## NEC-F-01 — Flota
**Pregunta:** ¿Cómo opera actualmente el transporte de mercancías?

| Código | Respuesta | Score |
|---|---|---:|
| NO_APLICA | No utiliza transporte relevante / no aplica | 0 |
| TERCERIZADO_SIMPLE | Operación tercerizada sencilla | 25 |
| MIXTA | Esquema mixto propio + terceros | 50 |
| PROPIA_RELEVANTE | Flota propia relevante | 75 |
| COMPLEJA | Flota compleja / múltiples operaciones o modalidades | 100 |

**Control:** esta variable NO sustituye la regla de capacidad propia P0.4.

## NEC-T-01 — Tecnología
**Pregunta:** ¿Qué sistemas utiliza actualmente para administrar su operación?

| Código | Respuesta | Score |
|---|---|---:|
| SIN_SISTEMA | No se identifica sistema | 0 |
| AISLADAS_MANUAL | Herramientas aisladas / procesos manuales | 25 |
| ERP | ERP | 50 |
| ERP_WMS_O_TMS | ERP + WMS o TMS | 75 |
| ERP_WMS_TMS_INTEGRADO | ERP + WMS + TMS / ecosistema integrado | 100 |

**Evidencia:** sistema(s) declarado(s) por el prospecto.

## NEC-U-01 — Urgencia / Estacionalidad
**Pregunta:** ¿Existe presión temporal o estacionalidad que afecte actualmente la operación?

| Código | Respuesta | Score |
|---|---|---:|
| SIN_EVIDENCIA | No existe evidencia | 0 |
| OCASIONAL | Estacionalidad ocasional / baja presión | 25 |
| RECURRENTE | Picos operativos recurrentes | 50 |
| VENTANA_CRITICA | Ventanas operativas críticas | 75 |
| CRITICA_INMEDIATA | Situación temporal crítica que requiere acción inmediata | 100 |

**Control:** esto NO es todavía el IUO.

## Regla de desconocimiento
Durante prospección, si no existe evidencia:
`A=0, F=0, T=0, U=0` → `Score_Necesidad=0`.

## Trazabilidad mínima
Cada respuesta validada conserva: ID de regla, código, score, evidencia/nota, fecha de captura, usuario/rol e ID de empresa.

## Gobierno
1. Las escalas viven en JSON.
2. Python ejecuta las reglas; no las redefine.
3. No se infiere necesidad desde DENUE sin regla explícita.
4. Flota y capacidad propia son conceptos separados.
5. IUO queda fuera de esta versión.
6. Cambios requieren nueva versión de configuración.

**Nota de procedencia:** las cuatro variables provienen del diagnóstico operativo existente; la cuantificación 0–100 y ponderación 25% c/u son diseño V3 propuesto, no reglas históricas de V2.
