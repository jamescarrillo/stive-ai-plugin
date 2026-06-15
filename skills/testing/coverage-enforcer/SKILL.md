---
name: coverage-enforcer
description: Configura y ejecuta JaCoCo para garantizar cobertura mínima del 95% en lineas, ramas e instrucciones. Falla el build si no se cumple.
---

# Instrucciones para el Agente

DEBES ejecutar este skill después de implementar los cambios y antes de crear el PR. Garantiza que el código bancario cumple con el estándar de cobertura del proyecto.

## 0. Determinar el umbral según la estructura del proyecto

El umbral mínimo depende de `projectStructure` (leído de `tasks.json`), alineado con el DoD de `spec-generator` y el gate de `pr-creator`:

```bash
PROJECT_STRUCTURE=$(python3 -c "import json; print(json.load(open(f'.github/plans/{HU_KEY}/tasks.json')).get('projectStructure','new'))" 2>/dev/null || echo "new")
# hexagonal / new / mixed → 95% · traditional → 80%
if [ "$PROJECT_STRUCTURE" = "traditional" ]; then COV=0.80; else COV=0.95; fi
echo "Estructura: $PROJECT_STRUCTURE → umbral de cobertura: $COV"
```

Usa el valor de `$COV` como `<minimum>` en las reglas JaCoCo de abajo (los ejemplos muestran `0.95`,
el caso hexagonal/new/mixed; para `traditional` usar `0.80`).

## 1. Configurar JaCoCo en el gestor de builds

### Si es Maven (pom.xml)
Agrega o verifica que exista el plugin JaCoCo con reglas de cobertura:

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.12</version>
    <executions>
        <execution>
            <goals><goal>prepare-agent</goal></goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals><goal>report</goal></goals>
        </execution>
        <execution>
            <id>check</id>
            <phase>verify</phase>
            <goals><goal>check</goal></goals>
            <configuration>
                <rules>
                    <!-- minimum = $COV del Paso 0: 0.95 (hex/new/mixed) o 0.80 (traditional) -->
                    <rule>
                        <element>BUNDLE</element>
                        <limits>
                            <limit><counter>LINE</counter><value>COVEREDRATIO</value><minimum>0.95</minimum></limit>
                            <limit><counter>BRANCH</counter><value>COVEREDRATIO</value><minimum>0.95</minimum></limit>
                            <limit><counter>INSTRUCTION</counter><value>COVEREDRATIO</value><minimum>0.95</minimum></limit>
                        </limits>
                    </rule>
                </rules>
                <excludes>
                    <!-- Excluir configuraciones, DTOs y repos sin lógica (Spring Data + Quarkus Panache) -->
                    <exclude>**/config/**</exclude>
                    <exclude>**/dto/**</exclude>
                    <exclude>**/*MapperImpl.*</exclude>
                    <exclude>**/Jpa*Repository.*</exclude>
                    <exclude>**/*PanacheRepository.*</exclude>
                </excludes>
            </configuration>
        </execution>
    </executions>
</plugin>
```

### Si es Gradle (build.gradle)
```groovy
plugins {
    id 'jacoco'
}

jacocoTestCoverageVerification {
    violationRules {
        rule {
            limit {
                counter = 'LINE'
                minimum = 0.95
            }
            limit {
                counter = 'BRANCH'
                minimum = 0.95
            }
            limit {
                counter = 'INSTRUCTION'
                minimum = 0.95
            }
        }
    }
    afterEvaluate {
        classDirectories.setFrom(files(classDirectories.files.collect {
            fileTree(dir: it, exclude: [
                '**/config/**',
                '**/dto/**',
                '**/*MapperImpl.*',
                '**/Jpa*Repository.*',
                '**/*PanacheRepository.*'
            ])
        }))
    }
}

check.dependsOn jacocoTestCoverageVerification
```

## 2. Ejecutar tests con cobertura

```bash
# Maven
./mvnw clean verify

# Gradle
./gradlew clean test jacocoTestReport jacocoTestCoverageVerification
```

## 3. Interpretar resultados

### Si el build pasa → ✅
La cobertura cumple el umbral del proyecto (`$COV`: 95% hex/new/mixed · 80% traditional). Continúa con el Checkpoint 3 del flujo de Stive.

### Si el build falla por cobertura → ⚠️
JaCoCo mostrará algo como:
```
Rule violated for bundle: lines covered ratio is 0.87, but expected minimum is 0.95
```

Pasos a seguir:
1. **Generar reporte HTML** para identificar código no cubierto:
   ```bash
   # Abrir el reporte en el navegador
   open target/site/jacoco/index.html  # Maven
   open build/reports/jacoco/test/html/index.html  # Gradle
   ```
2. **Identificar clases/métodos sin cubrir.**
3. **Agregar tests faltantes:**
   - Dominio: probar todos los branches de condicionales.
   - Aplicación: probar caso feliz + cada escenario de error.
   - Infraestructura: probar mappers y controladores.
4. **Re-ejecutar** `mvn clean verify` o `gradle clean test jacocoTestReport jacocoTestCoverageVerification`.
5. Repetir hasta que pase.

## 4. Exclusiones permitidas
Estas clases pueden excluirse del conteo de cobertura (aplica a Spring Boot y Quarkus):
- `*Config.java`, `*Configuration.java` — configuración / wiring (Spring `@Configuration`, etc.)
- `*Dto.java`, `*Request.java`, `*Response.java` — DTOs planos (records)
- `*MapperImpl.java` — código generado por MapStruct
- `*Entity.java` — entidades JPA (solo getters/setters)
- `Jpa*Repository.java` — interfaces Spring Data (sin lógica)
- `*PanacheRepository.java` — repositorios Panache de Quarkus sin lógica de negocio

Toda exclusión debe justificarse. NO excluyas lógica de negocio.
