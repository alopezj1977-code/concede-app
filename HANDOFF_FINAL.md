# CONCEDE V3 — HANDOFF FINAL

## Estado
**READY FOR PEER IMPLEMENTATION — FINAL**

## Reglas cerradas
- Motor único.
- 32 entidades federativas; P0.2 = cobertura por corrida.
- Elegibilidad configurable por mínimo/máximo de empleados.
- Score V3 = 35% Sector + 25% Tamaño + 10% Geografía + 30% Necesidad.
- AAA = 80–100; AA = 60–79.99; VALIDAR <60.
- Necesidad: evidencia únicamente; sin evidencia = 0.
- P0.4 capacidad propia: informativa; no altera Score, Prioridad ni elegibilidad.
- Sin fallbacks silenciosos.
- Score, Prioridad y Valor Potencial separados.
- Ticket = $69,600 MXN.
- Valor Potencial = N_AAA × Ticket.
- Run_ID y Rule_Version obligatorios.
- Tabla Score_Tamaño cerrada conforme al contrato V3 §5: 0-5=0; 6-10=40; 11-30=65; 31-50=85; 51-100=100; 101-250=90; 251+=75.

## Compatibilidad V2
Perfil histórico aislado. Debe reproducir exactamente:
296,441 raw → 18,410 elegibles → 1,711 AAA → $119,085,600.

El baseline V2 no redefine las reglas V3.

## Estado de pendientes
**NINGUNO.**
