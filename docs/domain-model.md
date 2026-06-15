# Domain Model

## Principios

- El modelo de dominio representa el lenguaje ubicuo del negocio.
- Debe ser independiente de frameworks, infraestructura y transporte.
- Contiene entidades, agregados, value objects y reglas de negocio.
- Evita la persistencia, serialización o detalles técnicos dentro del dominio.

## Estructura recomendada

- `domain/model/` — entidades y value objects.
- `domain/service/` — reglas de dominio y validaciones.
- `domain/exception/` — excepciones de negocio.

## Buenas prácticas

- Usa objetos inmutables siempre que sea posible.
- Mantén las invariantes en el constructor o en métodos de fábrica.
- No expongas clases de infraestructura desde el dominio.
- Usa nombres claros y consistentes con el vocabulario del negocio.
