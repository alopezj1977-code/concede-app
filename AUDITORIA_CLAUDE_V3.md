# AUDITORÍA TÉCNICA — CONCEDE V3
## Entregable de Claude para Peer, según PROMPT_CLAUDE_V3.md

---

## A. DICTAMEN

# 🔴 BLOQUEADO

No por mala ingeniería — el manejo de errores (`ConfigError`, cero fallbacks silenciosos, validación de 32 entidades) es sólido y mejor que cualquier versión anterior. Se bloquea porque **el código no implementa lo que los documentos fuente dicen que implementa**, y porque reaparece un bug de la misma familia que ya se corrigió dos veces en V2.

Tres razones concretas:

1. **Los propios documentos de contrato se contradicen entre sí** sobre los pesos de la fórmula principal (35/25/25/15 vs. 35/25/10/30), y el código elige una interpretación sin que quede documentado por qué, dejando la otra fórmula calculada pero sin usar en ningún lado.
2. **La clasificación que todos los documentos presentan como cerrada (AAA/AA/VALIDAR, 80/60) no existe en el código.** El código clasifica con P1–P4 (85/70/50), un esquema que no aparece en ningún documento fuente.
3. **El bug de elegibilidad configurable — el que ya le explicamos a Sergio que estaba resuelto — volvió.** La función que debía permitir cambiar el mínimo de empleados por corrida tiene una comparación invertida que la vuelve inoperante para cualquier valor distinto de 11.

No se puede programar sobre este paquete sin cerrar primero estos tres puntos con el Product Owner.

---

## B. MATRIZ DE HALLAZGOS

| ID | Archivo | Regla | Hallazgo | Severidad | Corrección requerida | ¿Cambia negocio? |
|---|---|---|---|---|---|---|
| H-01 | `source_contract/CONCEDE_V3_Contrato_Matematico_v1.0.md` §3, §18 vs. `PROMPT_CLAUDE_V3.md` §2.5 | Ponderación V3 | El contrato matemático (.md y .json) fija **35/25/25/15** (Geografía 25%, Necesidad 15%) y lo marca `BLOQUEADO`. El prompt que me diste fija **35/25/10/30** (Geografía 10%, Necesidad 30%) y lo marca "NO MODIFICAR". Son dos reglas cerradas que se contradicen. Además, `CONCEDE_V3_FASE1_1_Decisiones.md` lista explícitamente "Uso exacto de Score_Afinidad vs Prioridad_Comercial" como **decisión abierta** — es decir, un documento de la propia fuente dice que esto no estaba cerrado cuando el prompt ya lo presenta como cerrado. | 🔴 Crítica | El Product Owner debe decidir una sola fórmula operativa (o confirmar explícitamente que son dos fórmulas con dos propósitos distintos) antes de tocar código. | Sí — determina quién entra a AAA. |
| H-02 | `engine/core.py` líneas ~150–165 | Separación Score/Prioridad | El motor calcula `Score_Afinidad` (35/25/25/15, hardcodeado en Python como `base_w`, no en JSON) y `Prioridad_Comercial` (35/25/10/30, sí viene de `cfg["priority"]["weights"]`). Solo `Prioridad_Comercial` se usa para clasificar y se muestra en la app. `Score_Afinidad` se calcula, se guarda en la tabla de resultados, y nunca se usa para nada. | 🔴 Crítica | Decidir si `Score_Afinidad` se elimina (si no tiene función de negocio) o se activa con un propósito definido. Si se conserva, sus pesos deben vivir en `concede_v3.json`, no en Python — esto ya viola la regla de "nada hardcodeado" del propio contrato (§17). | Sí |
| H-03 | `config/concede_v3.json` → `priority.bands` vs. `PROMPT_CLAUDE_V3.md` §2.6 y contrato §9 | Clasificación AAA/AA/VALIDAR | Los dos documentos fuente dicen que la clasificación V3 es **AAA (80–100) / AA (60–79.99) / VALIDAR (<60)**. El código y la app implementan **P1 (85–100) / P2 (70–84.99) / P3 (50–69.99) / P4 (0–49.99)** — ni los nombres ni los cortes coinciden con ningún documento. No encontré en ningún archivo de dónde salió el esquema P1–P4; parece provenir de la config sin estar respaldado por ninguno de los tres documentos de contrato. | 🔴 Crítica | Si P1–P4 es una decisión real del Product Owner, debe quedar escrita en el contrato (hoy no existe en ningún lado). Si fue un error de transcripción al programar, se corrige a AAA/AA/VALIDAR 80/60 como dicen los documentos. | Sí — cambia el lenguaje comercial completo (AAA ya se le mostró a Julio en Wasper). |
| H-04 | `engine/core.py`, función `eligible()` | Elegibilidad configurable por corrida | `return b not in {"0-5","6-10"} and minimum <= 11` — compara el **parámetro `minimum`** contra la constante 11, no compara el tamaño real de la empresa contra `minimum`. Resultado: si alguien configura `employee_minimum` a, por ejemplo, 50 (exactamente lo que Sergio pidió poder hacer), la condición `50 <= 11` es `False` y **absolutamente ningún registro es elegible**, sin importar su tamaño real. Si se deja en 11 (el default), el motor funciona por coincidencia, no porque la lógica sea correcta. | 🔴 Crítica | Reescribir como comparación real contra el estrato de la empresa, con prueba de regresión que varíe el mínimo (11, 20, 50, 100, 300) y confirme que el universo elegible cambia de forma monotónica. | Sí — esta es exactamente la queja original de Sergio ("por qué no es sensible al número de empleados"), reaparecida en una forma distinta. |
| H-05 | `source_contract/.../Contrato_Matematico` §5 vs. `config/concede_v3.json` → `size.scores` | Tabla de tamaño | El contrato marca la tabla de tamaño como `bloqueado_como_referencia_inicial`: `{0-5:0, 6-10:40, 11-30:65, 31-50:85, 51-100:100, 101-250:90, 251+:75}`. La config real tiene valores distintos: `{0-5:0, 6-10:0, 11-30:50, 31-50:70, 51-100:100, 101-250:90, 251+:70}`. Se modificó una tabla marcada como bloqueada sin que quede registrado dónde se autorizó el cambio. | 🟠 Alta | Confirmar con el Product Owner si el cambio fue intencional; si sí, documentarlo y des-marcar `bloqueado`; si no, revertir a la tabla del contrato. | Sí — afecta el Score_Tamano de cada empresa. |
| H-06 | `tests/test_v3.py` | Regresión V2 obligatoria | `HANDOFF.md`, `PROMPT_CLAUDE_V3.md` y el contrato matemático exigen, los tres, una prueba de regresión que reproduzca 296,441 → 18,410 → 1,711 → \$119,085,600. El archivo de pruebas entregado **no contiene esa prueba** — solo 4 pruebas (catálogo de 32 entidades, que el multiselect no cambie el conteo de filas, necesidad en cero, y que un estrato desconocido truene). Ninguna prueba toca `eligible()`, ninguna calcula pipeline/ticket, ninguna compara contra el baseline V2. | 🔴 Crítica | Agregar la prueba de regresión obligatoria antes de aprobar cualquier otro cambio — ver sección D. | No directamente, pero sin ella no se puede verificar ningún otro hallazgo de esta tabla. |
| H-07 | `engine/core.py` (ausente) | Pipeline / Valor Potencial | El contrato (§11.C) y la config (`pipeline.ticket_required_for_pipeline: true`) exigen `Valor_Potencial = N_AAA × Ticket`. `ticket_promedio_mxn` existe en el JSON del **contrato** (69,600) pero no existe en `config/concede_v3.json`, y `run()` no calcula ningún valor potencial ni pipeline en ninguna parte. La métrica que más le importó a Sergio y a Julio en la presentación del viernes (\$119,085,600) **no se puede reproducir con este código tal cual está**. | 🔴 Crítica | Agregar `ticket_promedio_mxn` a `concede_v3.json` y calcular `Valor_Potencial` en `run()`, separado del score (tal como exige el contrato §1 y §11). | Sí — es el número que ya vio el cliente. |
| H-08 | `config/geografia_32_entidades.json` | Catálogo geográfico único | Existen **dos** archivos con el catálogo de 32 entidades: `config/geografia_32_entidades.json` (clave `entidades_federativas`) y `config/concede_v3.json` → `geography.entities`. El código solo lee el segundo; el primero no se importa en ningún archivo `.py`. Archivo huérfano que puede confundir a quien edite el catálogo más adelante (si alguien edita el archivo "equivocado", el cambio no tiene efecto). | 🟡 Media | Eliminar el archivo huérfano o, si se prefiere esa separación, hacer que `concede_v3.json` lo referencie en vez de duplicar la lista. | No |
| H-09 | `config/concede_v3.json` → `capacity_own.states` vs. contrato §10 | P0.4 Capacidad propia | El contrato describe la señal como binaria: "Sí/No". La config implementa 6 estados (`CAP-00` a `CAP-05`) sin que ningún documento defina esa taxonomía ni quién la aprobó. El motor además solo asigna `"CAP-00 DESCONOCIDA"` a todo registro — los otros 5 estados existen en la config pero no se calculan en ningún lado. | 🟡 Media | Confirmar con el Product Owner si la taxonomía de 6 estados es una decisión real (y documentarla) o si se reduce al Sí/No del contrato. Mientras tanto, es código muerto. | No todavía (no se usa) |
| H-10 | Transversal | Nomenclatura de severidad previa | Esta auditoría reutiliza y confirma hallazgos que ya se habían corregido antes en V2 (filtro de empleados vivo pero inútil, restaurantes mal clasificados — este último SÍ está corregido correctamente en `sector.direct_excluders`, buen trabajo ahí). El patrón de "bug de slider/filtro muerto" ya es la tercera vez que aparece en este proyecto (V2 primera corrida, V2 segunda corrida con "11-300" hardcodeado, ahora H-04 en V3). Vale la pena que el equipo agregue una prueba genérica "cambiar cualquier parámetro de corrida debe cambiar el resultado" como regla de ingeniería permanente, no solo para empleados. | 🟡 Media (proceso) | Ver prueba sugerida en sección D, caso 6. | No directamente |

---

## C. ESPECIFICACIÓN PARA PEER (orden de implementación)

**No implementar nada de esto hasta que el Product Owner resuelva H-01, H-02 y H-03** — son decisiones de negocio, no de código, y programar antes de cerrarlas garantiza rehacer el trabajo.

Una vez cerradas esas tres decisiones:

1. **Corregir H-04 primero y solo.** Es el bug más severo y el más aislado — un cambio de una línea en `eligible()`. Agregar la prueba de monotonía (sección D, caso 1) antes de tocar nada más.
2. **Implementar la decisión de H-01/H-02 tal como la cierre el Product Owner:**
   - Si se queda una sola fórmula: eliminar la que no se use (`Score_Afinidad` o `Prioridad_Comercial`) de `engine/core.py` y de la tabla de resultados en `app_v3.py`.
   - Si se quedan dos fórmulas con propósitos distintos: mover `base_w` de `engine/core.py` a `concede_v3.json` (nueva clave `"score"` paralela a `"priority"`), documentar en `README_BASE.md` para qué sirve cada una y por qué un usuario vería ambas.
3. **Implementar la decisión de H-03** (bandas de clasificación) en `concede_v3.json` → `priority.bands`, actualizando también los textos de `app_v3.py` (hoy dice "P1 85–100 · P2 70–84.99..." como caption fijo).
4. **H-05:** una vez confirmada la tabla de tamaño correcta, actualizar `size.scores` y quitar el status `PROVISIONAL_CONFIGURABLE` si ya quedó cerrada, o mantenerlo si sigue abierta.
5. **H-07:** agregar `"ticket_promedio_mxn": 69600` a `concede_v3.json` (sección `pipeline`) y calcular `Valor_Potencial` en `run()`, como columna/métrica separada de `Score` y `Prioridad` (no mezclar, tal como exige el contrato §1).
6. **H-08:** eliminar `config/geografia_32_entidades.json` o documentar por qué coexiste con la lista dentro de `concede_v3.json`.
7. **H-09:** reducir `capacity_own.states` a Sí/No hasta que exista una decisión comercial documentada para los 6 estados, o completar el cálculo real de los 6 si ya están aprobados.
8. **Todo lo anterior pasa la regresión V2 (sección D) antes de considerarse terminado.**

---

## D. PRUEBAS

### Regresión V2 obligatoria (ausente hoy — agregar primero)
```python
def test_regresion_v2_baseline():
    """Debe reproducir exactamente el baseline congelado de V2."""
    df = pd.read_csv("denue_inegi_11_.csv", encoding="latin1")  # o utf-8, según archivo real
    cfg_v2_compat = load_config("config/concede_v2_compat.json")  # perfil COMPAT_V2, pesos 35/25/25/15, AAA=80
    result, metrics = run(df, cfg_v2_compat, ["GUANAJUATO"], "REGRESION-V2")
    assert metrics["raw"] == 296441
    assert metrics["eligible"] == 18410
    # el nombre de la metrica AAA depende de como quede resuelto H-03
    assert metrics["aaa"] == 1711  # o el campo que corresponda tras cerrar H-03
    # valor potencial, una vez implementado H-07
    assert round(metrics["valor_potencial"]) == 119085600
```

### Caso 1 — Elegibilidad debe responder al parámetro (cubre H-04)
```python
def test_elegibilidad_responde_al_minimo():
    df = sample()  # usar la fixture existente de test_v3.py
    _, m_11 = run(df, CFG, ["QUERÉTARO","NUEVO LEÓN","TAMAULIPAS"], "MIN-11", employee_minimum=11)
    _, m_50 = run(df, CFG, ["QUERÉTARO","NUEVO LEÓN","TAMAULIPAS"], "MIN-50", employee_minimum=50)
    _, m_300 = run(df, CFG, ["QUERÉTARO","NUEVO LEÓN","TAMAULIPAS"], "MIN-300", employee_minimum=300)
    # el universo elegible debe reducirse o mantenerse igual al subir el minimo, nunca aumentar
    assert m_11["eligible"] >= m_50["eligible"] >= m_300["eligible"]
    # con un minimo absurdamente alto, el universo elegible debe poder llegar a 0
    _, m_9999 = run(df, CFG, ["QUERÉTARO","NUEVO LEÓN","TAMAULIPAS"], "MIN-9999", employee_minimum=9999)
    assert m_9999["eligible"] == 0
```

### Caso 2 — Score_Afinidad y Prioridad_Comercial no deben ser el mismo número por casualidad
```python
def test_score_afinidad_y_prioridad_son_distintos_cuando_los_pesos_lo_son():
    df = sample()
    r, _ = run(df, CFG, ["QUERÉTARO"], "DIST-001")
    # si tras cerrar H-01/H-02 los pesos siguen siendo distintos, los valores deben poder diferir
    # (no exigir que sean iguales ni distintos a ciegas -- exigir que el test documente la decision tomada)
    assert "Score_Afinidad" in r.columns
    assert "Prioridad_Comercial" in r.columns
```

### Caso 3 — Clasificación debe coincidir con lo documentado (cubre H-03)
```python
def test_bandas_de_clasificacion_coinciden_con_el_contrato():
    # Este test debe escribirse DESPUES de que el Product Owner cierre H-03.
    # Ejemplo si se confirma AAA/AA/VALIDAR 80/60:
    assert priority_band(85, CFG["priority"]["bands"]) == "AAA"
    assert priority_band(70, CFG["priority"]["bands"]) == "AA"
    assert priority_band(40, CFG["priority"]["bands"]) == "VALIDAR"
```

### Caso 4 — Pipeline separado del score (cubre H-07)
```python
def test_valor_potencial_no_se_mezcla_con_score():
    df = sample()
    r, m = run(df, CFG, ["QUERÉTARO"], "PIPE-001")
    assert "valor_potencial" in m
    assert m["valor_potencial"] == m["p1"] * CFG["pipeline"]["ticket_promedio_mxn"]
    # el valor potencial no debe aparecer como columna que influya Score_Afinidad o Prioridad
    assert "Valor_Potencial" not in ["Score_Sector","Score_Tamano","Score_Geografia","Score_Necesidad"]
```

### Caso 5 — Tabla de tamaño coincide con la fuente autorizada (cubre H-05)
```python
def test_tabla_tamano_coincide_con_fuente_autorizada(tabla_autorizada):
    assert CFG["size"]["scores"] == tabla_autorizada  # tabla_autorizada la define el Product Owner
```

### Caso 6 — Regla general de proceso (previene futuras recurrencias del mismo bug)
```python
def test_todo_parametro_de_corrida_cambia_el_resultado():
    """Prueba de humo: cualquier parametro configurable debe demostrar que mover su
    valor cambia el resultado. Si no lo cambia, o esta mal implementado o no deberia
    ser configurable."""
    df = sample()
    base, m_base = run(df, CFG, ["QUERÉTARO"], "BASE")
    _, m_emp = run(df, CFG, ["QUERÉTARO"], "EMP", employee_minimum=200)
    assert m_emp != m_base  # empleados
    # repetir el mismo patron para cada parametro configurable que se agregue a futuro
```

---

## E. PROMPT DE IMPLEMENTACIÓN PARA PEER

```
Actúa como implementador de CONCEDE V3. NO tomes decisiones de negocio — todas las
decisiones de negocio para este paquete ya fueron resueltas por el Product Owner y
te las paso resueltas abajo. Si encuentras una decisión de negocio sin resolver que
no esté en esta lista, DETENTE y repórtala; no la inventes ni elijas la opción que
te parezca más razonable.

DECISIONES YA CERRADAS QUE DEBES IMPLEMENTAR TAL CUAL (se llenan antes de pasarte
este prompt, con lo que resuelva el Product Owner sobre H-01/H-02/H-03):
- Fórmula(s) de score a usar: [PENDIENTE DE LLENAR POR PRODUCT OWNER]
- Esquema de clasificación (nombres y cortes): [PENDIENTE DE LLENAR POR PRODUCT OWNER]
- Tabla de tamaño definitiva: [PENDIENTE DE LLENAR POR PRODUCT OWNER]

CAMBIOS DE CÓDIGO A REALIZAR, EN ESTE ORDEN:
1. engine/core.py, función eligible(): corrige la comparación para que compare el
   tamaño real de la empresa contra el parámetro `minimum`, no `minimum` contra una
   constante fija. Agrega test_elegibilidad_responde_al_minimo (ver auditoría,
   sección D, Caso 1) y confirma que pasa con minimum=11, 50, 300 y 9999.
2. Implementa la fórmula de score que te indicó el Product Owner arriba. Si sobra
   una fórmula (Score_Afinidad o Prioridad_Comercial), elimínala de core.py y de
   app_v3.py. Si se quedan ambas, sus pesos deben vivir en concede_v3.json, nunca
   hardcodeados en Python.
3. Implementa el esquema de clasificación que te indicó el Product Owner, en
   concede_v3.json -> priority.bands, y actualiza el caption fijo en app_v3.py que
   hoy describe P1-P4 a mano.
4. Agrega ticket_promedio_mxn a concede_v3.json y calcula Valor_Potencial en run()
   como salida separada de Score y Prioridad (no la mezcles en la misma fórmula).
5. Elimina config/geografia_32_entidades.json (archivo huérfano, no se usa en
   ningún .py) o documenta explícitamente por qué coexiste con geography.entities.
6. Reduce capacity_own.states a Sí/No, o implementa el cálculo real de los 6
   estados si el Product Owner confirma que esa taxonomía es una decisión cerrada.

PRUEBAS OBLIGATORIAS ANTES DE ENTREGAR:
- Las 4 pruebas ya existentes en tests/test_v3.py deben seguir pasando.
- Agrega y pasa los 6 casos de la sección D de la auditoría de Claude (archivo
  AUDITORIA_CLAUDE_V3.md), incluyendo la prueba de regresión V2
  (296,441 / 18,410 / 1,711 / $119,085,600) usando el perfil COMPAT_V2.

NO HAGAS:
- No agregues sectores, palabras clave o estados nuevos sin evidencia aprobada.
- No reintroduzcas ningún `.get(clave, valor_default)` para parámetros obligatorios
  (ticket, pesos, umbrales) -- si falta, el motor debe detenerse con ConfigError.
- No toques el tratamiento de Necesidad (ya está correcto: 0 sin evidencia).
- No toques la lista de exclusión de sector (direct_excluders) -- ya está correcta
  y verificada contra el bug de restaurantes de V2.

AL TERMINAR:
Entrega un diff por archivo, el resultado de las pruebas, y el run_id de la
corrida de regresión V2 que usaste para confirmar los 4 números del baseline.
```