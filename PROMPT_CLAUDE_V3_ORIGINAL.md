# PROMPT MASTER — REVISIÓN TÉCNICA CONCEDE V3

Actúa como **arquitecto senior de software, auditor de reglas y revisor de motores de scoring B2B**.

Tu misión es revisar el paquete técnico adjunto de **4MSFTS-CONCEDE V3** y entregar una especificación de implementación limpia para que **Peer programe el motor V3**.

## 1. OBJETIVO

No diseñes otro producto. No cambies el alcance. No inventes reglas.

Debes revisar que la implementación propuesta respete el contrato y las decisiones cerradas por el Product Owner.

Flujo de trabajo:

**Contrato → revisión Claude → implementación Peer → prueba → aprobación del Product Owner.**

## 2. DECISIONES CERRADAS — NO MODIFICAR

1. **Motor único.** No crear motores separados por estado.
2. **Catálogo geográfico:** las 32 entidades federativas permanecen en un catálogo único.
3. **P0.2:** es exclusivamente el filtro de cobertura geográfica de la corrida. Permite una, varias o todas las entidades.
4. **Elegibilidad por tamaño:** es configurable por corrida; no debe quedar hardcodeada a 11+. El perfil 11+ se conserva únicamente para compatibilidad V2.
5. **Ponderación V3:**
   - Sector = 35%
   - Tamaño = 25%
   - Geografía = 10%
   - Necesidad = 30%
6. **Clasificación V3:**
   - AAA = 80–100
   - AA = 60–79.99
   - VALIDAR = 0–59.99
7. **Necesidad:** sin evidencia directa, no se infiere desde DENUE. Valor inicial = 0.
8. **P0.4 / Capacidad propia:** únicamente informativa. No elimina registros, no modifica score y no modifica prioridad.
9. **Sin fallbacks silenciosos.** Si falta un parámetro obligatorio o existe una inconsistencia crítica, el motor debe detenerse y reportarla.
10. **Trazabilidad:** toda corrida debe conservar Run_ID, versión de reglas, fuente, parámetros y resultado.
11. **Compatibilidad V2:** debe existir una prueba de regresión capaz de reproducir:
    - raw = 296,441
    - elegible = 18,410
    - AAA V2 = 1,711
    - potencial = $119,085,600
12. El baseline V2 anterior se conserva como referencia histórica; **no debe mezclarse con las reglas V3**.

## 3. SEPARACIONES OBLIGATORIAS

Mantén separadas estas capas:

- **SCORE / clasificación**
- **PRIORIDAD COMERCIAL**
- **POTENCIAL / PIPELINE**
- **FUNNEL COMERCIAL**
- **EVIDENCIA / TRAZABILIDAD**

No conviertas una métrica comercial en una regla de scoring sin evidencia.

## 4. LO QUE DEBES REVISAR

Revisa código, configuración y pruebas buscando:

- reglas hardcodeadas que contradigan la configuración;
- inconsistencias entre JSON y Python;
- columnas obligatorias y validación de fuente;
- cálculo de tamaño;
- P0.2 y las 32 entidades;
- pesos 35/25/10/30;
- clasificación AAA/AA/VALIDAR;
- necesidad basada exclusivamente en evidencia;
- tratamiento informativo de P0.4;
- trazabilidad y Run_ID;
- ausencia de fallbacks silenciosos;
- compatibilidad V2;
- pruebas de regresión;
- riesgos de doble conteo o mezcla entre score y prioridad.

## 5. PENDIENTES DEL CONTRATO — NO LOS RESUELVAS POR TU CUENTA

Si alguno de estos puntos sigue sin estar definido en los documentos fuente, **NO inventes una solución**. Señálalo como `PENDIENTE` y especifica exactamente qué decisión falta.

- tratamiento definitivo del modelo de Necesidad cuando exista evidencia comercial;
- valores definitivos de geografía dirigida, si se requiere un score geográfico distinto al filtro P0.2;
- taxonomía definitiva de afinidad sectorial si requiere ampliación respecto de la configuración entregada;
- nomenclatura/modelado definitivo de potencial vs pipeline comercial;
- reconciliación histórica de 1,989 vs 1,711;
- cualquier otro punto que el contrato fuente marque expresamente como pendiente.

**No conviertas un pendiente en una regla nueva.**

## 6. ENTREGABLE DE CLAUDE

Entrega exactamente estas 5 piezas:

### A. DICTAMEN
Máximo 1 página:
- APROBADO
- APROBADO CON CAMBIOS
- BLOQUEADO

### B. MATRIZ DE HALLAZGOS
Columnas:
`ID | Archivo | Regla | Hallazgo | Severidad | Corrección requerida | ¿Cambia negocio?`

### C. ESPECIFICACIÓN PARA PEER
Lista exacta de cambios de código/configuración, en orden de implementación.

### D. PRUEBAS
Casos mínimos de regresión y casos nuevos para V3.

### E. PROMPT DE IMPLEMENTACIÓN PARA PEER
Un prompt listo para copiar/pegar que indique a Peer qué debe programar, qué no debe tocar y qué pruebas debe ejecutar.

## 7. REGLA DE ORO

**Fuente → evidencia → decisión → cierre.**

Si la fuente no lo establece, no lo inventes.
Si una regla está cerrada por el Product Owner, no la reabras.
Si existe contradicción entre código y contrato, reporta la contradicción y corrige hacia el contrato cerrado.

El objetivo final es dejar **CONCEDE V3 listo para programación**, no generar una nueva auditoría interminable.
