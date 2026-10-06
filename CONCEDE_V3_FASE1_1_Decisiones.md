# CONCEDE V3 — Fase 1.1: Contrato y matriz de decisiones

## Decisión arquitectónica
Un solo motor CONCEDE V3 con catálogo de 32 entidades federativas. P0.2 es una selección múltiple configurable por corrida. Querétaro, Nuevo León, Estado de México y Tamaulipas son solicitudes/pilotos, no arquitecturas distintas.

## Reglas cerradas
- No usar automáticamente el universo histórico de 296,441 de Guanajuato.
- Necesidad no se infiere desde DENUE.
- Capacidad propia no equivale a flota.
- Pipeline está separado del score.
- No existen fallbacks silenciosos.
- Cada corrida debe ser trazable.

## Decisiones aún abiertas
1. Elegibilidad mínima/máxima de empleados.
2. Función matemática de geografía después del filtro P0.2.
3. Uso exacto de Score_Afinidad vs Prioridad_Comercial.
4. Comportamiento comercial de P1 cuando necesidad = 0.
5. Operación de P0.4 y captura de evidencia.

## Próximo gate
No modificar el motor de forma libre. Primero cerrar las decisiones abiertas y después dar a Peer instrucciones de implementación.
