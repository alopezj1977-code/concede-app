# 4MSFTS–CONCEDE MOTOR V3
## PASO 4 — Contrato Matemático V3 v1.0

**Fecha:** 2026-10-01  
**Estatus:** Diseño previo a implementación  
**Regla rectora:** V2 se congela; V3 se diseña sobre evidencia auditada.

---

## 1. Arquitectura matemática

El motor V3 separa tres capas:

1. **SCORE** — mide afinidad respecto al ICP.
2. **PRIORIDAD** — convierte el score en una categoría operativa.
3. **VALOR COMERCIAL** — calcula valor potencial y, únicamente cuando existe una oportunidad validada, pipeline comercial.

No se deben mezclar estas tres capas.

---

## 2. Universo y elegibilidad

### Regla V3 propuesta
Una unidad económica entra al universo elegible cuando:

`Empleados >= 11`

Estratos incluidos:
- 11–30
- 31–50
- 51–100
- 101–250
- 251+

Estratos fuera:
- 0–5
- 6–10
- dato de empleados inválido/no interpretable

Esta regla reproduce el universo de 18,410 utilizado para la reconciliación de V2.

---

## 3. Componentes del Score

Cada componente se normaliza a una escala 0–100.

### Fórmula general

`Score_Total = 0.35*S_sector + 0.25*S_tamano + 0.25*S_geografia + 0.15*S_necesidad`

Pesos V3 propuestos:
- Sector: 35%
- Tamaño: 25%
- Geografía/Rutas: 25%
- Necesidad: 15%

Suma de pesos = 100%.

---

## 4. Sector

### Base auditada
El perfil recuperado de V2 clasifica actividades DENUE en:
- Agroindustria
- CPG / Consumo
- Retail / Mayoristas
- Logística
- además de categorías auxiliares y `Otro`.

V2 utilizó:
- 100 cuando existe coincidencia con un sector afín.
- 30 cuando no existe coincidencia, en la ejecución que reproduce 1,711.

### Regla V3
Los valores deben quedar parametrizados en JSON, no codificados en Python.

**Estado:** PROPUESTO.

No se agregan nuevos sectores ni palabras clave sin evidencia comercial o aprobación de CONCEDE.

---

## 5. Tamaño

Se conserva inicialmente la escala auditada:

| Estrato | Score |
|---|---:|
| 0–5 | 0 |
| 6–10 | 40 |
| 11–30 | 65 |
| 31–50 | 85 |
| 51–100 | 100 |
| 101–250 | 90 |
| 251+ | 75 |

En V3 la lectura del estrato será normalizada y exacta; se elimina la posibilidad de errores por coincidencia de substrings.

**Estado:** BLOQUEADO como referencia inicial; parametrizado para evolución.

---

## 6. Geografía

La geografía no elimina registros por sí misma.

### Modo neutral
Si se selecciona `TODAS LAS ENTIDADES` o `GEO_NEUTRAL`:

`S_geografia = 100`

### Modo dirigido
Si existen estados objetivo:
- coincidencia: score alto parametrizado
- no coincidencia: score bajo parametrizado
- dato faltante: score específico parametrizado

**Estado:** PROPUESTO/PENDIENTE de definición comercial de rutas.

La presentación indica que la expansión posterior puede considerar zonas prioritarias y rutas clave, por lo que V3 debe permitir configurarlas sin modificar código.

---

## 7. Necesidad

### Principio
DENUE no demuestra por sí solo la necesidad real de compra.

La propia presentación establece el principio:
**“Buscar primero. Validar después.”**

Por ello, en la fase de prospección:
- `S_necesidad = 0` cuando no existe evidencia directa.
- La necesidad se captura en la etapa de validación comercial.

La versión auditada de V2 utilizó exactamente este tratamiento para no sumar afinidad artificial.

### Evidencia disponible para la validación
El módulo de diagnóstico de V2 pregunta por:
- infraestructura de almacenamiento
- flota propia/mixta/tercerizada
- WMS/TMS/ERP
- urgencia/estacionalidad

Estas variables pueden convertirse en un `S_necesidad` V3 cuando CONCEDE valide su ponderación.

**Estado:** BLOQUEADO en 0 para compatibilidad; DISEÑO V3 PENDIENTE.

---

## 8. Consecuencia crítica del umbral AAA=80

Si `S_necesidad = 0`, aun con sector y geografía perfectos, el máximo teórico por tamaño es:

| Estrato | Score máximo con necesidad=0 |
|---|---:|
| 11–30 | 76.25 |
| 31–50 | 81.25 |
| 51–100 | 85.00 |
| 101–250 | 82.50 |
| 251+ | 78.75 |

Esto significa que un AAA=80 privilegia, por construcción matemática, determinados estratos.

**Decisión requerida antes de cerrar V3:** confirmar que este efecto es comercialmente deseado o modificar la política de tratamiento de necesidad desconocida.

No se debe “corregir” esta consecuencia escondiéndola con un fallback.

---

## 9. Prioridad

### Parámetros V3 propuestos
- AAA: `Score_Total >= 80`
- AA: `60 <= Score_Total < 80`
- VALIDAR: `Score_Total < 60`

Los umbrales son parámetros, no constantes del código.

**Importante:** AAA=80 y AA=60 son diseño V3 propuesto. No describen cómo se obtuvo el baseline V2 de 1,711.

---

## 10. Capacidad propia probable — P0.4

La lógica auditada de V2 genera una señal:

`Señal: Capacidad propia probable = Sí/No`

No elimina registros.

### Regla V3 provisional
La señal será informativa y trazable, pero no modificará el score ni excluirá cuentas hasta que CONCEDE defina explícitamente una de estas políticas:

1. Excluir.
2. Penalizar score.
3. Modificar prioridad.
4. Sólo informar.

**Estado:** PENDIENTE DE DECISIÓN COMERCIAL.

---

## 11. Score vs Prioridad vs Pipeline

### A. Score
Mide afinidad:

`0 <= Score_Total <= 100`

### B. Prioridad
Se determina por umbrales:

`AAA / AA / VALIDAR`

### C. Valor potencial de prospección

`Valor_Potencial = N_AAA * Ticket`

Con ticket de referencia:

`Ticket = $69,600 MXN`

Esto NO es venta realizada.

### D. Pipeline comercial
Sólo existe cuando una cuenta ha sido validada y existe una oportunidad comercial registrada.

V3 deberá distinguir:
- Valor potencial de prospección.
- Pipeline bruto.
- Pipeline ponderado.
- Venta cerrada.

---

## 12. Funnel comercial

El funnel no forma parte del score.

La secuencia presentada fue:

`1,989 → 1,591 → 557 → 139 → 56 → 42 → 8`

Las conversiones implícitas son aproximadamente:
- 80.0%
- 35.0%
- 25.0%
- 40.3%
- 75.0%
- 19.0%

La secuencia es matemáticamente reproducible con redondeo.

En V3 cada etapa debe tener:
- población inicial
- tasa observada o supuesta
- fuente
- periodo
- población
- resultado calculado

Las tasas no deben mezclarse con el motor de scoring.

---

## 13. Modelo de escenarios

Conservador / Realista / Optimista sólo se permitirán cuando cada supuesto esté explícito.

Cada escenario deberá declarar:

`N_base`
`Tasa_decisor`
`Tasa_conexión`
`Tasa_respuesta`
`Tasa_cita`
`Tasa_reunión`
`Tasa_cierre`
`Ticket`

Resultado:

`Cierres = N_base × Π(tasas)`

y:

`Ingreso = Cierres × Ticket`

Los escenarios de la presentación que parten de 1,989 deben mantenerse separados del baseline V2 de 1,711 hasta que esa diferencia sea reconciliada.

---

## 14. Trazabilidad obligatoria

Cada corrida V3 debe generar:

- `Run_ID`
- versión del motor
- versión del JSON
- fecha/hora
- archivo/dataset
- hash del dataset
- registros crudos
- registros elegibles
- pesos
- umbrales
- ticket
- reglas activas
- resultado AAA
- resultado AA
- valor potencial
- conteo por regla
- cambios V2→V3

### Waterfall obligatorio

`RAW → ELEGIBLE → V2 COMPAT → CAMBIOS V3 → AAA V3`

---

## 15. Lineage por empresa

Cada registro deberá conservar:

`ID_DENUE`
`Score_Sector`
`Score_Tamano`
`Score_Geografia`
`Score_Necesidad`
`Score_Total`
`Categoria`
`Capacidad_Propia`
`Regla_Activada`
`Motivo_Cambio`
`V2_Score`
`V3_Score`
`V2_AAA`
`V3_AAA`

Esto permite explicar por qué una cuenta entró, salió o cambió de prioridad.

---

## 16. Compatibilidad V2

V3 tendrá dos perfiles:

### COMPAT_V2
Debe reproducir:

`296,441 RAW`
`18,410 elegibles`
`1,711 AAA`
`$119,085,600 valor potencial`

bajo las reglas recuperadas y congeladas de V2.

### V3
Aplicará las nuevas reglas propuestas.

La prueba de regresión será obligatoria antes de aceptar cualquier cambio.

---

## 17. Reglas de ingeniería

Prohibido:

`config.get("ticket_promedio", 69600)`

`config.get("umbrales", {"AAA":75,"AA":55})`

`pesos.get("sector",35)`

Cualquier parámetro obligatorio ausente o inválido debe detener la ejecución:

**CONFIGURACIÓN INVÁLIDA — CORRIDA ABORTADA**

---

## 18. Decisiones que quedan para cerrar antes del código V3

### BLOQUEADO
- identidad del motor
- separación Score/Prioridad/Pipeline
- validación obligatoria
- Run ID
- regresión V2
- no fallbacks silenciosos
- elegibilidad base 11+
- pesos 35/25/25/15 como diseño inicial

### PROPUESTO
- AAA=80
- AA=60
- ticket=$69,600
- geografía configurable
- sector parametrizado
- P0.4 como señal informativa inicial

### PENDIENTE
1. Tratamiento V3 de `S_necesidad`.
2. Política definitiva de capacidad propia.
3. Valores exactos de geografía dirigida.
4. Taxonomía definitiva de prioridad.
5. Lista definitiva de sectores afines.
6. Modelo comercial de escenarios.
7. Reconciliación de 1,989 vs 1,711.

---

## 19. Regla de oro V3

**El motor no debe fabricar certeza que los datos no contienen.**

Su trabajo es:
1. encontrar,
2. priorizar,
3. explicar por qué,
4. entregar trazabilidad,
5. pasar la cuenta a validación comercial.

La venta se demuestra después.
