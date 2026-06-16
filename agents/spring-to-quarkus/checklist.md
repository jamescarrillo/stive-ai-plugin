---
name: spring-to-quarkus-checklist
description: Material de soporte de spring-to-quarkus (no es un agente seleccionable).
user-invocable: false
---

# Checklist: Spring to Quarkus Migration

- [ ] Revisar la arquitectura hexagonal y los boundaries de dominio.
- [ ] Identificar controladores REST y adaptarlos a JAX-RS.
- [ ] Verificar que las entidades del dominio no dependan de Spring.
- [ ] Migrar repositorios JPA a Panache o `PanacheRepository`.
- [ ] Adaptar clientes de servicio externo a Quarkus REST Client.
- [ ] Sustituir Resilience4j por SmallRye Fault Tolerance.
- [ ] Actualizar configuraciones en `application.properties`.
- [ ] Validar tests unitarios y de integración.
- [ ] Ejecutar `mvn compile quarkus:dev` y revisar arranque.
