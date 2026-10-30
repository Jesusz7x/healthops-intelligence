# HEALTHOPS INTELLIGENCE

**Demostración ficticia de inteligencia operativa para centros sanitarios pequeños.** El sistema muestra una aplicación web autenticada, endpoints REST con roles, datos relacionales, flujos CSV, analítica operativa explicable y bitácora de auditoría. Todas las personas, citas, cantidades, cuentas y métricas incluidas son sintéticas. No es un producto clínico, expediente médico ni software sanitario certificado.

## Implementación actual

- API HTTP y servidor estático con la biblioteca estándar de Python 3.13.
- SQLite mediante `sqlite3` incluido con Python: claves foráneas, restricciones, índices y transacciones.
- Interfaz bilingüe adaptable en HTML, CSS y JavaScript, con temas claro y oscuro.
- Contraseñas con PBKDF2-HMAC-SHA256, tokens de sesión aleatorios guardados como hashes, cookies HttpOnly/SameSite, permisos por rol, límite de intentos de inicio y auditoría.
- Panel, registro ficticio de pacientes, citas, directorio de personal y roles de cuentas demo, movimientos de inventario, importación/exportación CSV, revisión de calidad de datos, auditoría, configuración, tendencias diarias, alertas experimentales de anomalías y una proyección base de demanda.
- CLI de revisión CSV y 18 pruebas automatizadas de integración, unitarias y de contrato frontend.

Esta primera versión ejecutable usa la biblioteca estándar porque Angular/Express no están instalados y el entorno de construcción no tiene acceso al registro de paquetes. PostgreSQL está instalado como cliente, pero no hay servidor activo. **Angular, Express, PostgreSQL y las pruebas de extremo a extremo en navegador no forman parte de la versión verificada.** El contrato REST queda documentado para reemplazar/extender el adaptador local en una fase posterior. Esta limitación no se presenta como funcionalidad terminada.

## Ejecución local

Requisitos: Python 3.11 o superior. No se requiere `pip install`, compilación de Node, servidor PostgreSQL, Docker ni servicio de pago.

```sh
cd projects/07-healthops-intelligence
python3 api/server.py
```

Abre `http://127.0.0.1:8787`. El servidor solo escucha loopback de forma predeterminada. En el primer inicio crea `data/healthops.sqlite3` y carga registros ficticios. La base de datos está excluida de Git.

### Cuentas de demostración

Todas usan la contraseña local de demo `DemoHealthOps!2026`. No la reutilices fuera de esta demostración ficticia.

| Correo | Rol |
|---|---|
| `admin@healthops.local` | Administración |
| `ops@healthops.local` | Operaciones |
| `clinical@healthops.local` | Administración clínica |
| `stock@healthops.local` | Inventario |
| `viewer@healthops.local` | Solo lectura |

## Pruebas

```sh
python3 -m unittest discover -s tests -v
node --check web/app.js
python3 -m py_compile api/*.py processing/*.py
```

Las 13 pruebas de integración de API despachan solicitudes dentro del proceso porque este sandbox no permite crear sockets. Dos prueban el módulo Python de calidad y tres verifican IDs, traducciones y enlaces a recursos estáticos del frontend. Son pruebas reales del handler y la base de datos, pero no sustituyen la comprobación con HTTP/navegador real.

## Documentación principal

Consulta [instalación y despliegue](docs/INSTALLATION.md), [arquitectura](docs/ARCHITECTURE.md), [modelo de datos](docs/DATA_MODEL.md), [contrato OpenAPI](docs/openapi.yaml), [manual de usuario](docs/USER_GUIDE.md), [seguridad](docs/SECURITY.md), [plan de pruebas](docs/TEST_PLAN.md), [caso de estudio](docs/CASE_STUDY.md) y [decisiones técnicas](docs/DECISIONS.md).

## Seguridad de la demo pública

El servidor rechaza conexiones remotas salvo que `HEALTHOPS_READ_ONLY=1`. En ese modo, todos los usuarios se tratan como lectores. Para un proxy HTTPS público configura `HEALTHOPS_HOST=0.0.0.0`, `HEALTHOPS_READ_ONLY=1` y `HEALTHOPS_SECURE_COOKIES=1`. No expongas el modo local modificable, no uses HTTP sin TLS ni subas una base con datos ingresados por personas. Este repositorio no se ha desplegado públicamente.

## Licencia

MIT. Las cuentas, personas y muestras son ficticias y se pueden reutilizar como datos de prueba.
