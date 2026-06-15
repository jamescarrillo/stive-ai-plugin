---
name: mock-strategist
description: Proporciona estrategias de mocking para dependencias externas (BD, Redis, Service Bus, APIs) en pruebas unitarias y de integración bancarias.
---

# Instrucciones para el Agente

Cuando un microservicio bancario se conecta a servicios externos, los tests deben aislar esas dependencias. Este skill define **cuándo y cómo mockear** cada tipo de dependencia.

## Estrategia general

| Dependencia | Test Unitario (Dominio/Aplicación) | Test de Integración (Infraestructura) |
|---|---|---|
| **Base de datos** (Postgres, MySQL) | Mockito en Outbound Port | Testcontainers (@DataJpaTest) |
| **Redis** | Mockito en Outbound Port | Testcontainers (RedisContainer) |
| **Service Bus / RabbitMQ / Kafka** | Mockito en Outbound Port | Testcontainers (KafkaContainer, RabbitMQContainer) o Embedded broker |
| **APIs de otros microservicios** | Mockito en Outbound Port | WireMock (@WireMockTest) |
| **AWS S3 / SQS / SNS** | Mockito en Outbound Port | Testcontainers + LocalStack |
| **Cache (Caffeine, Redis)** | Mockito en Outbound Port | Test simple con cache real |

## Reglas para mockear

### 1. Tests de Dominio (`domain/`) y Aplicación (`application/`)
- **Siempre Mockito** en los Outbound Ports.
- **Prohibido:** `@SpringBootTest`, `@MockBean`, Testcontainers.
- Usar `@Mock` + `@InjectMocks` + `@ExtendWith(MockitoExtension.class)`.

```java
@ExtendWith(MockitoExtension.class)
class AccountQueryServiceTest {

    @Mock
    private AccountRepositoryPort repository;

    @InjectMocks
    private AccountQueryService service;

    @Test
    void shouldReturnAccountsWhenCustomerExists() {
        when(repository.findByCustomerId("CU-12345"))
            .thenReturn(List.of(account()));

        var result = service.findByCustomerId("CU-12345");

        assertThat(result).hasSize(1);
    }

    @Test
    void shouldReturnEmptyWhenCustomerHasNoAccounts() {
        when(repository.findByCustomerId("CU-99999"))
            .thenReturn(List.of());

        var result = service.findByCustomerId("CU-99999");

        assertThat(result).isEmpty();
    }
}
```

### 2. Tests de Infraestructura - Persistencia

#### Base de datos relacional → Testcontainers + @DataJpaTest
```java
@ActiveProfiles("test")
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Testcontainers
class JpaAccountRepositoryAdapterTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUri);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private JpaAccountRepository jpaRepository;

    private AccountJpaRepositoryAdapter adapter;

    @BeforeEach
    void setUp() {
        var mapper = new AccountEntityMapperImpl();
        adapter = new AccountJpaRepositoryAdapter(jpaRepository, mapper);
    }

    @Test
    void shouldFindAccountsByCustomerId() {
        jpaRepository.save(accountEntity("CU-12345"));

        var result = adapter.findByCustomerId("CU-12345");

        assertThat(result).hasSize(1);
    }
}
```

#### Redis → Testcontainers
```java
@SpringBootTest
@Testcontainers
class RedisSessionAdapterTest {

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine")
        .withExposedPorts(6379);

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry registry) {
        registry.add("spring.data.redis.host", redis::getHost);
        registry.add("spring.data.redis.port", () -> redis.getMappedPort(6379));
    }
}
```

### 3. Tests de Infraestructura - APIs externas

#### WebClient → WireMock
```java
@SpringBootTest
@WireMockTest(httpPort = 8089)
class CustomerServiceClientTest {

    @Autowired
    private CustomerServiceClient client;

    @Test
    void shouldReturnCustomerWhenServiceResponds() {
        stubFor(get(urlEqualTo("/customer-registration/customer/retrieve?customerCu=CU-12345"))
            .willReturn(aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBody("{\"id\":\"CU-12345\",\"name\":\"Juan\"}")));

        var result = client.findByCustomerId("CU-12345");

        assertThat(result).isPresent();
        assertThat(result.get().getName()).isEqualTo("Juan");
    }

    @Test
    void shouldReturnEmptyWhenServiceReturns404() {
        stubFor(get(urlEqualTo("/customer-registration/customer/retrieve?customerCu=CU-99999"))
            .willReturn(aResponse().withStatus(404)));

        var result = client.findByCustomerId("CU-99999");

        assertThat(result).isEmpty();
    }

    @Test
    void shouldReturnEmptyWhenServiceIsDown() {
        stubFor(get(urlEqualTo("/customer-registration/customer/retrieve?customerCu=CU-12345"))
            .willReturn(aResponse().withStatus(500)));

        var result = client.findByCustomerId("CU-12345");

        assertThat(result).isEmpty();
    }
}
```

### 4. Kafka / Service Bus → Testcontainers

```java
@SpringBootTest
@Testcontainers
class PaymentEventPublisherTest {

    @Container
    static KafkaContainer kafka = new KafkaContainer(
        DockerImageName.parse("confluentinc/cp-kafka:7.6.0"));

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry registry) {
        registry.add("spring.kafka.bootstrap-servers", kafka::getBootstrapServers);
    }

    @Autowired
    private PaymentEventPublisher publisher;

    @Test
    void shouldPublishPaymentEvent() {
        publisher.publish(new PaymentEvent("order-123", 100.00));

        // Verificar usando un TestConsumer
    }
}
```

## Resumen de dependencias para tests

Para los test de infraestructura, agregar en `pom.xml`:

```xml
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>testcontainers</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>postgresql</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>kafka</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.wiremock</groupId>
    <artifactId>wiremock-spring-boot</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>io.projectreactor</groupId>
    <artifactId>reactor-test</artifactId>
    <scope>test</scope>
</dependency>
```
