---
name: spring-webclient-configurator
description: Configura WebClient con Resilience4j CircuitBreaker, timeouts y trazabilidad para la comunicación entre microservicios bancarios.
---

# Instrucciones para el Agente

Cuando un microservicio necesite comunicarse con otro microservicio del ecosistema bancario, DEBES usar **WebClient** (no RestTemplate, no Feign). Este skill configura la comunicación con patrón de resiliencia bancaria.

## 1. Dependencias necesarias

### Maven (pom.xml)
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
</dependency>
<dependency>
    <groupId>io.github.resilience4j</groupId>
    <artifactId>resilience4j-spring-boot3</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aop</artifactId>
</dependency>
```

### Gradle (build.gradle)
```groovy
implementation 'org.springframework.boot:spring-boot-starter-webflux'
implementation 'io.github.resilience4j:resilience4j-spring-boot3'
implementation 'org.springframework.boot:spring-boot-starter-aop'
```

## 2. Configurar WebClient bean

En `infrastructure/config/WebClientConfig.java`:

```java
package com.jotace.<serviceDomain>.infrastructure.config;

import io.netty.channel.ChannelOption;
import io.netty.handler.timeout.ReadTimeoutHandler;
import io.netty.handler.timeout.WriteTimeoutHandler;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;
import java.util.concurrent.TimeUnit;

@Configuration
public class WebClientConfig {

    @Bean
    public WebClient.Builder webClientBuilder() {
        HttpClient httpClient = HttpClient.create()
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 5000)
            .doOnConnected(conn -> conn
                .addHandlerLast(new ReadTimeoutHandler(10, TimeUnit.SECONDS))
                .addHandlerLast(new WriteTimeoutHandler(10, TimeUnit.SECONDS)));

        return WebClient.builder()
            .clientConnector(new ReactorClientHttpConnector(httpClient));
    }
}
```

## 3. Crear el adaptador outbound con WebClient

En `infrastructure/adapters/outbound/external/<ExternalService>Client.java`:

```java
package com.jotace.<serviceDomain>.infrastructure.adapters.outbound.external;

import com.jotace.<serviceDomain>.application.ports.outbound.<ExternalService>Port;
import com.jotace.<serviceDomain>.domain.model.<BusinessObject>;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import java.time.Duration;
import java.util.Collections;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
import reactor.util.retry.Retry;

@Component
public class <ExternalService>Client implements <ExternalService>Port {

    private static final Logger log = LoggerFactory.getLogger(<ExternalService>Client.class);
    private final WebClient webClient;

    public <ExternalService>Client(@Qualifier("webClientBuilder") WebClient.Builder builder) {
        this.webClient = builder.baseUrl("${<external-service>.base-url}").build();
    }

    @CircuitBreaker(name = "<serviceDomain>Service", fallbackMethod = "fallbackFindByCustomerId")
    public List<<BusinessObject>> findByCustomerId(String customerId) {
        return webClient.get()
            .uri("/<serviceDomainKebab>/<behaviorQualifier>/<bianVerbLower>?<queryParam>={param}", customerId)
            .retrieve()
            .bodyToFlux(<BusinessObject>.class)
            .collectList()
            .timeout(Duration.ofSeconds(10))
            .retryWhen(Retry.backoff(3, Duration.ofSeconds(1)))
            .block();
    }

    private List<<BusinessObject>> fallbackFindByCustomerId(String customerId, Throwable t) {
        log.error("Fallback called for customer {}: {}", customerId, t.getMessage());
        return Collections.emptyList();
    }
}
```

## 4. Configurar CircuitBreaker (application.yml)

```yaml
resilience4j:
  circuitbreaker:
    configs:
      default:
        sliding-window-size: 10
        minimum-number-of-calls: 5
        failure-rate-threshold: 50
        wait-duration-in-open-state: 30s
        permitted-number-of-calls-in-half-open-state: 3
        automatic-transition-from-open-to-half-open-enabled: true
    instances:
      <serviceDomain>Service:
        base-config: default
  timelimiter:
    configs:
      default:
        timeout-duration: 12s
    instances:
      <serviceDomain>Service:
        base-config: default
  retry:
    configs:
      default:
        max-attempts: 3
        wait-duration: 1s
    instances:
      <serviceDomain>Service:
        base-config: default
```

## 5. Consideraciones bancarias

| Requisito | Configuración |
|---|---|
| Timeout de conexión | 5s |
| Timeout de lectura/escritura | 10s |
| Número de reintentos | 3 con backoff 1s |
| CircuitBreaker | Ventana deslizante de 10 llamadas, 50% de fallos abre el circuito |
| Trazabilidad | Pasar `trace-id` y `Authorization` en headers si es intra-banca |
| Logging | Siempre loguear fallos en fallback con `log.error()` |

## 6. Pruebas del WebClient

En tests de infraestructura, usar **WireMock** para simular el microservicio destino:
```java
// src/test/java/.../infrastructure/adapters/outbound/external/<ExternalService>ClientTest.java
@SpringBootTest
@AutoConfigureWebTestClient
@WireMockTest(httpPort = 8089)
class <ExternalService>ClientTest {

    @Test
    void shouldReturnAccountsWhenServiceResponds() {
        stubFor(get(urlEqualTo("/account-management/account/retrieve?cu=CU-12345"))
            .willReturn(aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBody("[{\"id\":\"1\"}]")));

        var result = client.findByCustomerId("CU-12345");

        assertThat(result).hasSize(1);
    }
}
```
