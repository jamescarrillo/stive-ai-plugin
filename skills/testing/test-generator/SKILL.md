---
name: test-generator
description: Genera tests unitarios (JUnit 5 + Mockito) para dominio/aplicación y tests de integración (@WebMvcTest, @DataJpaTest + Testcontainers) para infraestructura.
---

# Instrucciones para el Agente

Ejecuta este skill **inmediatamente después** de `spring-use-case-implementer` o cuando existan clases nuevas en cualquier capa. Genera tests para cada clase siguiendo las reglas de `dependencies.md`.

## 0. Detectar package base del proyecto

Antes de generar tests, detecta el package base real:

```bash
# Detectar package base real desde la estructura del proyecto
DOMAIN_DIR=$(find src/main/java -type d -name "domain" -not -path "*/test/*" 2>/dev/null | head -1)
if [ -n "$DOMAIN_DIR" ]; then
    FINAL_PACKAGE=$(echo "$DOMAIN_DIR" | sed 's|src/main/java/||; s|/domain.*||' | tr '/' '.')
else
    echo "⚠️ No se detectó proyecto Java. Usando $FINAL_PACKAGE como fallback."
    FINAL_PACKAGE="$FINAL_PACKAGE"
fi

echo "Package para tests: $FINAL_PACKAGE"
```

**IMPORTANTE:** En todos los templates de esta sección, reemplaza `$FINAL_PACKAGE` con el valor real detectado. NO uses `$FINAL_PACKAGE` ni `$FINAL_PACKAGE_DIR`.

## 1. Detectar clases nuevas sin test

```bash
# Encontrar clases Java que NO tienen test correspondiente
find src/main/java -name "*.java" | while read src; do
  test_file="src/test/java${src#src/main/java}"
  test_file="${test_file%.java}Test.java"
  if [ ! -f "$test_file" ]; then
    echo "MISSING TEST: $src"
  fi
done
```

## 2. Generar tests por capa

### 2.1. Tests de dominio (`domain/`)

Para cada modelo, VO, enum o servicio de dominio. **Prohibido**: `@SpringBootTest`, `@MockBean`.

#### Modelo / Value Object

Para cada Value Object (`record`) en el dominio, generar test de validación:

```java
package $FINAL_PACKAGE.domain.model;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class CustomerCuTest {

    @Test
    void shouldRejectNullValue() {
        assertThatThrownBy(() -> new CustomerCu(null))
            .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void shouldRejectBlankValue() {
        assertThatThrownBy(() -> new CustomerCu("  "))
            .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void shouldAcceptValidValue() {
        var cu = new CustomerCu("CU-12345");
        assertThat(cu.value()).isEqualTo("CU-12345");
    }
}
```

Archivo: `src/test/java/$FINAL_PACKAGE_DIR/domain/model/<BusinessObject>Test.java`

```java
package $FINAL_PACKAGE.domain.model;

import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import static org.assertj.core.api.Assertions.assertThat;

class <BusinessObject>Test {

    @Test
    void shouldBuildWithBuilder() {
        var account = <BusinessObject>.builder()
            .accountNumber("191-98765432-0-12")
            .currency("PEN")
            .cci("00219100987654320112")
            .balance(new BigDecimal("4500.50"))
            .type(<BusinessObject>Type.SALARY)
            .build();

        assertThat(account.getAccountNumber()).isEqualTo("191-98765432-0-12");
        assertThat(account.getCurrency()).isEqualTo("PEN");
        assertThat(account.getBalance()).isEqualByComparingTo(new BigDecimal("4500.50"));
        assertThat(account.getType()).isEqualTo(<BusinessObject>Type.SALARY);
    }

    @Test
    void shouldPreserveImmutability() {
        var account = <BusinessObject>.builder()
            .accountNumber("191-98765432-0-12")
            .currency("PEN")
            .cci("00219100987654320112")
            .balance(BigDecimal.ZERO)
            .type(<BusinessObject>Type.SALARY)
            .build();

        assertThat(account.getClass().getDeclaredFields())
            .allMatch(f -> java.lang.reflect.Modifier.isFinal(f.getModifiers()));
    }

    // --- DDD: Business behavior tests ---
    // Implementar si el Aggregate tiene métodos de negocio (deposit, withdraw, etc.)
    @Test
    void shouldDepositIncreasesBalance() {
        var account = <BusinessObject>.builder()
            .accountNumber("191-98765432-0-12")
            .currency("PEN")
            .cci("00219100987654320112")
            .balance(new BigDecimal("1000.00"))
            .type(<BusinessObject>Type.SALARY)
            .build();

        account.<businessMethod>(new BigDecimal("500.00"));

        assertThat(account.getBalance()).isEqualByComparingTo(new BigDecimal("1500.00"));
    }

    @Test
    void shouldRegisterDomainEventOnBusinessAction() {
        var account = <BusinessObject>.builder()
            .accountNumber("191-98765432-0-12")
            .currency("PEN")
            .cci("00219100987654320112")
            .balance(new BigDecimal("1000.00"))
            .type(<BusinessObject>Type.SALARY)
            .build();

        account.<businessMethod>(new BigDecimal("500.00"));

        assertThat(account.getDomainEvents()).isNotEmpty();
    }
}
```

#### Enum

Archivo: `src/test/java/$FINAL_PACKAGE_DIR/domain/model/<BusinessObject>TypeTest.java`

```java
package $FINAL_PACKAGE.domain.model;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class <BusinessObject>TypeTest {

    @Test
    void shouldHaveAllExpectedValues() {
        assertThat(<BusinessObject>Type.values())
            .containsExactlyInAnyOrder(
                <BusinessObject>Type.SALARY,
                <BusinessObject>Type.FIXED_TERM,
                <BusinessObject>Type.CTS,
                <BusinessObject>Type.CURRENT
            );
    }
}
```

### 2.2. Tests de aplicación (`application/`)

Para cada servicio de aplicación. **Prohibido**: `@SpringBootTest`, `@MockBean`.

Archivo: `src/test/java/$FINAL_PACKAGE_DIR/application/service/<BusinessObject>QueryServiceTest.java`

```java
package $FINAL_PACKAGE.application.service;

import $FINAL_PACKAGE.application.ports.outbound.<BusinessObject>RepositoryPort;
import $FINAL_PACKAGE.domain.model.<BusinessObject>;
import $FINAL_PACKAGE.domain.model.<BusinessObject>Type;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import java.math.BigDecimal;
import java.util.List;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class <BusinessObject>QueryServiceTest {

    @Mock
    private <BusinessObject>RepositoryPort repository;

    @InjectMocks
    private <BusinessObject>QueryService service;

    @Test
    void shouldReturnAccountsWhenCustomerExists() {
        var account = <BusinessObject>.builder()
            .accountNumber("191-98765432-0-12")
            .currency("PEN")
            .cci("00219100987654320112")
            .balance(new BigDecimal("4500.50"))
            .type(<BusinessObject>Type.SALARY)
            .build();

        when(repository.findByCustomerId("CU-12345"))
            .thenReturn(List.of(account));

        var result = service.findByCustomerId("CU-12345");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getAccountNumber()).isEqualTo("191-98765432-0-12");
    }

    @Test
    void shouldReturnEmptyListWhenCustomerHasNoAccounts() {
        when(repository.findByCustomerId("CU-99999"))
            .thenReturn(List.of());

        var result = service.findByCustomerId("CU-99999");

        assertThat(result).isEmpty();
    }
}
```

### 2.3. Tests de infraestructura — REST Controller

Usar `@WebMvcTest`. Archivo: `src/test/java/$FINAL_PACKAGE_DIR/infrastructure/adapters/inbound/rest/<BusinessObject>ControllerTest.java`

```java
package $FINAL_PACKAGE.infrastructure.adapters.inbound.rest;

import $FINAL_PACKAGE.application.ports.inbound.Retrieve<BusinessObject>sUseCase;
import $FINAL_PACKAGE.domain.model.<BusinessObject>;
import $FINAL_PACKAGE.domain.model.<BusinessObject>Type;
import $FINAL_PACKAGE.infrastructure.adapters.inbound.mapper.<BusinessObject>DtoMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import java.math.BigDecimal;
import java.util.List;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(<BusinessObject>Controller.class)
class <BusinessObject>ControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private Retrieve<BusinessObject>sUseCase useCase;

    @Autowired
    private <BusinessObject>DtoMapper mapper;

    @Test
    void shouldReturn200WhenAccountsFound() throws Exception {
        var account = <BusinessObject>.builder()
            .accountNumber("191-98765432-0-12")
            .currency("PEN")
            .cci("00219100987654320112")
            .balance(new BigDecimal("4500.50"))
            .type(<BusinessObject>Type.SALARY)
            .build();

        when(useCase.findByCustomerId("CU-12345"))
            .thenReturn(List.of(account));

        mockMvc.perform(get("/<microservicename>/<behaviorqualifier>/<bianVerbLower>")
                .param("cu", "CU-12345"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].accountNumber").value("191-98765432-0-12"))
            .andExpect(jsonPath("$[0].type").value("SALARY"));
    }

    @Test
    void shouldReturn200WithEmptyListWhenNoAccounts() throws Exception {
        when(useCase.findByCustomerId("CU-99999"))
            .thenReturn(List.of());

        mockMvc.perform(get("/<microservicename>/<behaviorqualifier>/<bianVerbLower>")
                .param("cu", "CU-99999"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isEmpty());
    }

    @Test
    void shouldReturn400WhenCuMissing() throws Exception {
        mockMvc.perform(get("/<microservicename>/<behaviorqualifier>/<bianVerbLower>"))
            .andExpect(status().isBadRequest());
    }
}
```

### 2.4. Tests de infraestructura — Persistencia JPA

Usar `@DataJpaTest` + Testcontainers. Archivo: `src/test/java/$FINAL_PACKAGE_DIR/infrastructure/adapters/outbound/database/<BusinessObject>JpaRepositoryAdapterTest.java`

```java
package $FINAL_PACKAGE.infrastructure.adapters.outbound.database;

import $FINAL_PACKAGE.infrastructure.adapters.outbound.mapper.<BusinessObject>EntityMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import java.math.BigDecimal;
import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
class <BusinessObject>JpaRepositoryAdapterTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUri);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private Jpa<BusinessObject>Repository jpaRepository;

    private <BusinessObject>JpaRepositoryAdapter adapter;

    @BeforeEach
    void setUp() {
        var mapper = new <BusinessObject>EntityMapper();
        adapter = new <BusinessObject>JpaRepositoryAdapter(jpaRepository, mapper);
    }

    @Test
    void shouldFindAccountsByCustomerId() {
        var entity = new <BusinessObject>Entity();
        entity.setAccountNumber("191-98765432-0-12");
        entity.setCustomerCu("CU-12345");
        entity.setCurrency("PEN");
        entity.setCci("00219100987654320112");
        entity.setBalance(new BigDecimal("4500.50"));
        entity.setType("SALARY");
        jpaRepository.save(entity);

        var result = adapter.findByCustomerId("CU-12345");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getAccountNumber()).isEqualTo("191-98765432-0-12");
    }

    @Test
    void shouldReturnEmptyWhenNoAccounts() {
        var result = adapter.findByCustomerId("CU-NONEXISTENT");

        assertThat(result).isEmpty();
    }
}
```

### 2.5. Tests de infraestructura — Mappers

Archivo: `src/test/java/$FINAL_PACKAGE_DIR/infrastructure/adapters/outbound/mapper/<BusinessObject>EntityMapperTest.java`

```java
package $FINAL_PACKAGE.infrastructure.adapters.outbound.mapper;

import $FINAL_PACKAGE.infrastructure.adapters.outbound.database.<BusinessObject>Entity;
import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import static org.assertj.core.api.Assertions.assertThat;

class <BusinessObject>EntityMapperTest {

    private final <BusinessObject>EntityMapper mapper = new <BusinessObject>EntityMapper();

    @Test
    void shouldMapEntityToDomain() {
        var entity = new <BusinessObject>Entity();
        entity.setAccountNumber("191-98765432-0-12");
        entity.setCurrency("PEN");
        entity.setCci("00219100987654320112");
        entity.setBalance(new BigDecimal("4500.50"));
        entity.setType("SALARY");

        var domain = mapper.toDomain(entity);

        assertThat(domain).isNotNull();
        assertThat(domain.getAccountNumber()).isEqualTo("191-98765432-0-12");
        assertThat(domain.getType().name()).isEqualTo("SALARY");
    }

    @Test
    void shouldReturnNullWhenEntityIsNull() {
        assertThat(mapper.toDomain(null)).isNull();
    }
}
```

## 3. Verificar que los tests compilan y pasan

```bash
if [ -f "mvnw" ]; then
  ./mvnw test -q
elif [ -f "gradlew" ]; then
  ./gradlew test
elif [ -f "pom.xml" ]; then
  mvn test -q
elif [ -f "build.gradle" ]; then
  gradle test
fi
```

Si algún test falla:
1. Lee el mensaje de error específico
2. Corrige la lógica o el test
3. Re-ejecuta hasta que todos pasen

## 4. Post-tests

Ejecuta `coverage-enforcer` para verificar que la cobertura alcance el 95%.
