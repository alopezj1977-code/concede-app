# PROMPT FINAL DE IMPLEMENTACIÓN — PEER — CONCEDE V3

Actúa como implementador de software de CONCEDE V3. No tomes decisiones de negocio: implementa exactamente las reglas cerradas en este prompt.

## CONTRATO CERRADO
1. Motor único.
2. Catálogo único de 32 entidades federativas.
3. P0.2 = cobertura geográfica por corrida: una, varias o todas.
4. Elegibilidad configurable por corrida: mínimo y máximo; máximo nulo significa sin límite superior. 11+ es solo compatibilidad histórica V2.
5. Score V3 = 35% Sector + 25% Tamaño + 10% Geografía + 30% Necesidad.
6. Clasificación: AAA 80–100 / AA 60–79.99 / VALIDAR <60.
7. Necesidad: sin evidencia = 0; no inferir necesidad desde DENUE.
8. P0.4 Capacidad Propia: informativa; no modifica Score, Prioridad ni elegibilidad.
9. Sin fallbacks silenciosos. Parámetro obligatorio ausente/inválido = ConfigError.
10. Score, Prioridad y Valor Potencial son salidas separadas.
11. Ticket promedio = $69,600 MXN, configurable y obligatorio.
12. Valor Potencial = N_AAA × Ticket; no interviene en Score.
13. Tabla Score_Tamaño DEFINITIVA: 0-5=0; 6-10=40; 11-30=65; 31-50=85; 51-100=100; 101-250=90; 251+=75.
14. Run_ID y Rule_Version deben acompañar cada corrida/salida.

## COMPATIBILIDAD V2
Mantén un perfil V2 aislado que reproduzca exactamente:
296,441 raw → 18,410 elegibles → 1,711 AAA → $119,085,600.
Esto es regresión histórica y no sustituye la clasificación V3 de AAA>=80.

## IMPLEMENTACIÓN
- Corrige cualquier parámetro configurable que no afecte realmente el resultado.
- employee_minimum y employee_maximum deben compararse contra el tamaño real/estrato real.
- No hardcodees pesos, umbrales, ticket ni catálogo.
- Mantén trazabilidad de fuente y configuración.
- Conserva la exclusión sectorial ya verificada; no agregues sectores, palabras clave ni estados sin fuente aprobada.
- Elimina archivos de configuración duplicados/huérfanos si no tienen función; debe existir una sola fuente efectiva del catálogo de 32 entidades.

## PRUEBAS OBLIGATORIAS
1. Suite V3 completa.
2. Elegibilidad monotónica con mínimos 11, 50, 300 y 9999.
3. Clasificación 80/60.
4. Pesos 35/25/10/30.
5. Necesidad sin evidencia = 0.
6. Valor Potencial separado del Score.
7. Regresión V2 exacta: 296441/18410/1711/$119085600.
8. Cambiar un parámetro configurable debe demostrar efecto en la salida o estar justificado como parámetro de control.

## ENTREGA FINAL DE PEER
Devuelve:
- diff por archivo;
- archivos modificados;
- resultado completo de pytest;
- run_id de regresión V2;
- evidencia de los cuatro números del baseline;
- confirmación de que no existen pendientes de negocio.

NO inventes reglas.
