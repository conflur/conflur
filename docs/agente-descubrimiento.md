# Agente de Descubrimiento — validación de mercado por conversación

> **Es una pieza de PLATAFORMA (Capa 0-1), reusable por toda instancia.** El motor (entrevistar
> conversacionalmente + sintetizar al KM) es genérico; el *guion* (preguntas, concepto, términos a
> testear) es **config por instancia**. Primer uso real de un agente haciendo trabajo valioso, sobre
> una tarea de **bajo riesgo** (investiga, no opera plata ni clientes). Además: **doble función** —
> investigación + adquisición (meses gratis → primeros usuarios).

## Por qué (decisión 2026-06-30)
Reemplaza "el humano hace 5 entrevistas" por **"un agente conduce la validación por conversación"**.
Validar así prueba la tesis agéntica temprano y —al ser plataforma— **acelera la fase de validación
de cada empresa futura**, no solo Conflur.

## Canal
**Web/Telegram** (menor fricción que WhatsApp Business API). El contacto tibio comparte un **link** al bot.

## Flujo conversacional (v0)
Principios: ~10 min · una pregunta por vez · repregunta adaptativa · transparente · **descubrimiento
antes del ofrecimiento** (anti-sesgo) · salida fácil.

0. **Apertura + consentimiento** — transparente: es un bot y **parte de lo que validamos es el bot**.
1. **Contexto/rol** — ¿solo o consultorio con secretaria? (segmenta owner/professional/assistant).
2. **Descubrimiento (el corazón)** — día típico · lo más tedioso · cómo lleva notas/agenda/plata hoy ·
   qué le da culpa/ansiedad/evita · **¿te pagás un sueldo o sacás de la caja?** (separación
   consultorio/personal).
3. **Tests de lenguaje** — turno/cita · paciente/consultante · "¿qué esperás en 'Mis números'?" ·
   "'pagate un sueldo…' ¿te suena?".
4. **Reacción al concepto** — descripción corta (o link) → "¿te resolvería algo? ¿qué le falta?".
5. **Feedback del bot** — "¿cómo se sintió hablar con este bot? ¿lo preferís a formulario/llamada?".
6. **Ofrecimiento (al final)** — meses gratis/descuento como gracias → captura de contacto.
7. **Cierre** — consentimiento para contactar.

## Calibración y volumen (metodología)
- Los primeros **2-3** son para **calibrar** el bot: se leen los transcripts, se ve dónde repreguntó
  bien o se quedó corto, y se ajustan los prompts antes de escalar.
- Los **dolores** se dan por validados al llegar a **saturación (~5-8 charlas)**, no a las 3 (evitar
  sesgo de confirmación).
- El volumen **posterior** a la saturación sirve para: adquisición (meses gratis), validar el
  **lenguaje a escala**, validar el **bot mismo**, y **pipeline de primeros usuarios**.

## Síntesis → KM
Por charla, extrae estructurado `{rol, dolores (tags), términos usados, reacción, feedback del bot,
interés/contacto}` + transcript crudo. Consolida across charlas → **hallazgos** → alimenta
`docs/capa-profesional.md`.

## Ético / cuidado de contactos
Los contactos son intros tibias → una mala primera impresión tiene costo social. El bot es
**transparente desde el arranque**, respetuoso, con **consentimiento**, y con audiencia sensible
(psicólogos) esto es doble de importante.

## Relación con el roster de agentes
Es un **agente de plataforma** (como el de mantenimiento que faltaba). Va en el mapa de agentes
pendiente. Registrado también en `../docs/NEW_INSTANCE_PROTOCOL.md`.
