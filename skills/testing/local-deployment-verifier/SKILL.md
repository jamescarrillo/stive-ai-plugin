---
name: local-deployment-verifier
description: Compila, arranca y verifica que el microservicio levanta correctamente. Luego lo detiene. Pide permiso antes de ejecutarse.
---

# Instrucciones para el Agente

Este skill se ejecuta después de la implementación y antes del Checkpoint 3. **No ejecutes nada sin permiso explícito del usuario.**

## 0. Pedir permiso al usuario

Antes de ejecutar cualquier comando, DETENTE y pregunta al usuario:

```
He llegado al paso de validación local. ¿Quieres que compile y arranque
el microservicio para verificar que levanta correctamente?

Si hay errores, intentaré corregirlos o te indicaré qué se necesita.
```

Espera su confirmación para continuar.

## 1. Compilar el proyecto

```bash
echo "=== 1/4 Compilando el proyecto ==="
if [ -f "mvnw" ]; then
    BUILD_CMD="./mvnw clean package -DskipTests -q"
elif [ -f "pom.xml" ]; then
    BUILD_CMD="mvn clean package -DskipTests -q"
elif [ -f "gradlew" ]; then
    BUILD_CMD="./gradlew bootJar -x test"
elif [ -f "build.gradle" ]; then
    BUILD_CMD="gradle bootJar -x test"
else
    echo "FAIL: No se detectó gestor de builds"
    exit 1
fi

echo "Ejecutando: $BUILD_CMD"
if ! eval "$BUILD_CMD" 2>&1; then
    echo "FAIL: Error de compilación/empaquetado"
    echo "Revisa los errores de compilación arriba. Pueden ser:"
    echo "  - Dependencias faltantes en pom.xml/build.gradle"
    echo "  - Errores de sintaxis en el código generado"
    echo "  - Versiones de Java/Spring incompatibles"
    exit 1
fi
echo "PASS: Compilación exitosa"
```

## 2. Detectar puerto y JAR

```bash
echo ""
echo "=== 2/4 Preparando despliegue ==="

# Detectar puerto del application.yml (default 8080)
APP_PORT=$(grep -E "port:" src/main/resources/application.yml 2>/dev/null \
    | grep -oE "[0-9]+" | head -1)
APP_PORT="${APP_PORT:-8080}"

# Detectar JAR generado
JAR_FILE=$(find target/ -name "*.jar" -type f 2>/dev/null | head -1)
if [ -z "$JAR_FILE" ] && [ -d "build/libs/" ]; then
    JAR_FILE=$(find build/libs/ -name "*.jar" -type f 2>/dev/null | head -1)
fi

echo "  Puerto: $APP_PORT"
echo "  JAR: ${JAR_FILE:-usando spring-boot:run}"
```

## 3. Iniciar y verificar

```bash
echo ""
echo "=== 3/4 Iniciando aplicación ==="

# Limpiar puerto si está ocupado
if lsof -ti:$APP_PORT &>/dev/null; then
    echo "Puerto $APP_PORT ocupado. Liberando..."
    kill -9 $(lsof -ti:$APP_PORT) 2>/dev/null || true
    sleep 2
fi

APP_LOG="/tmp/${APP_NAME:-microservice}-boot.log"
rm -f "$APP_LOG"
APP_PID=""

if [ -n "$JAR_FILE" ]; then
    java -jar "$JAR_FILE" > "$APP_LOG" 2>&1 &
    APP_PID=$!
elif command -v mvn &>/dev/null || [ -f "mvnw" ]; then
    (mvn spring-boot:run > "$APP_LOG" 2>&1) &
    APP_PID=$!
fi

if [ -z "$APP_PID" ]; then
    echo "FAIL: No se pudo iniciar la aplicación"
    exit 1
fi

echo "  PID: $APP_PID"
echo "  Log: $APP_LOG"
echo "  Esperando hasta 60 segundos..."
```

```bash
# Esperar a que arranque (máx 60s)
START_TIME=$(date +%s)
TIMEOUT=60
BOOTED=false
ERROR_MSG=""

while true; do
    ELAPSED=$(( $(date +%s) - START_TIME ))
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo ""
        echo "TIMEOUT: La aplicación no arrancó en ${TIMEOUT}s"
        kill $APP_PID 2>/dev/null || true
        echo "FAIL: Timeout de inicio"
        echo ""
        echo "Últimos logs:"
        tail -30 "$APP_LOG"
        exit 1
    fi

    # Éxito
    if grep -q "Started .* in " "$APP_LOG" 2>/dev/null; then
        BOOTED=true
        break
    fi

    # Error de arranque
    if grep -q "APPLICATION FAILED TO START" "$APP_LOG" 2>/dev/null; then
        ERROR_MSG=$(grep -A 30 "APPLICATION FAILED TO START" "$APP_LOG")
        break
    fi

    # Otros errores fatales
    if grep -q "Exception\|ERROR\|FATAL" "$APP_LOG" 2>/dev/null; then
        # Podría ser error recuperable, seguir esperando pero registrar
        :
    fi

    sleep 2
    echo -n "."
done
```

## 4. Analizar resultado

```bash
echo ""
echo "=== 4/4 Resultado ==="

if [ "$BOOTED" = true ]; then
    echo ""
    echo "=========================================="
    echo "  ✅  MICROSERVICIO LEVANTA CORRECTAMENTE"
    echo "=========================================="
    echo ""
    echo "  Puerto: $APP_PORT"
    echo "  PID: $APP_PID"
    echo ""

    # Health check opcional
    sleep 2
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:$APP_PORT/actuator/health" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo "  Health check: OK (HTTP $HTTP_CODE)"
    else
        echo "  (sin actuator, se omite health check)"
    fi

    echo ""
    echo "Últimos logs:"
    tail -5 "$APP_LOG"

    echo ""
    echo "--- TODO CORRECTO ---"

elif [ -n "$ERROR_MSG" ]; then
    echo ""
    echo "  ❌  LA APLICACIÓN FALLÓ AL ARRANCAR"
    echo ""
    echo "$ERROR_MSG"
    echo ""
    echo "--- ANÁLISIS DE ERROR ---"

    # Intentar diagnosticar
    if echo "$ERROR_MSG" | grep -q "port.*already in use"; then
        echo "🔧 El puerto $APP_PORT está ocupado por otro proceso."
        echo "   Cierra el otro proceso o cambia el puerto en application.yml"
    elif echo "$ERROR_MSG" | grep -q "datasource\|DataSource\|Database\|Connection refused"; then
        echo "🔧 La base de datos no está disponible."
        echo "   Asegúrate de tener PostgreSQL corriendo (o la BD que uses)."
        echo "   Puedes levantar la BD con Docker:"
        echo "   docker run --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16-alpine"
    elif echo "$ERROR_MSG" | grep -q "ClassNotFoundException\|NoClassDefFoundError"; then
        echo "🔧 Falta una dependencia en el classpath."
        echo "   Revisa el pom.xml/build.gradle para dependencias faltantes."
        echo "   Esto puede requerir intervención manual si la dependencia no está declarada."
    elif echo "$ERROR_MSG" | grep -q "BeanCreationException\|UnsatisfiedDependency"; then
        echo "🔧 Error en la configuración de Spring Beans."
        echo "   Revisa DomainConfig.java y las anotaciones en infrastructure/."
        echo "   Puede ser un error de inyección de dependencias que debo corregir en el código."
    elif echo "$ERROR_MSG" | grep -q "MigrationException\|Flyway\|Validate"; then
        echo "🔧 Error en migraciones Flyway."
        echo "   Revisa que las migraciones SQL en db/migration/ sean válidas."
        echo "   Si es un error de validación, puede que la BD ya tenga un esquema distinto."
    else
        echo "⚠️  Error no clasificado automáticamente."
        echo "   Revisa los logs completos en: $APP_LOG"
        echo "   Si el error está en el código generado, lo corrijo."
        echo "   Si falta infraestructura externa (BD, Redis, etc.), debes instalarla."
    fi

    exit 1
else
    echo "FAIL: Error desconocido al iniciar la aplicación"
    echo "Últimos logs:"
    tail -30 "$APP_LOG"
    exit 1
fi
```

## 5. Detener la aplicación

```bash
echo ""
echo "=== Deteniendo aplicación ==="
kill $APP_PID 2>/dev/null
sleep 1
if kill -0 $APP_PID 2>/dev/null; then
    kill -9 $APP_PID 2>/dev/null || true
fi
echo "✅ Aplicación detenida"
```

## 6. Notificar al usuario

```bash
echo ""
echo "=========================================="
echo "  VERIFICACIÓN LOCAL COMPLETADA"
echo "=========================================="
echo ""
echo "La aplicación compila y arranca correctamente."
echo "Puedes continuar con el siguiente paso del workflow."
echo ""
```

## Manejo de errores fuera de alcance

Si el error es por infraestructura externa (BD no disponible, puerto ocupado, falta Docker), indícaselo claramente al usuario con las instrucciones para resolverlo. No intentes instalar herramientas globales sin permiso.

Si el error es en el código generado (beans, inyección, config), **intenta corregirlo automáticamente** y vuelve a ejecutar la verificación. Si después de 3 intentos no se resuelve, exponlo al usuario con el diagnóstico completo.
