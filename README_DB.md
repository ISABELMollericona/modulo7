**Esquema de Base de Datos — Módulo GRH**

Este documento describe el esquema relacional usado por el Dashboard RRHH (módulo): tablas principales, columnas, tipos sugeridos, claves primarias/foráneas, índices y ejemplos `CREATE TABLE` para referencia.

**Resumen**:
- **Modelo**: Dimensiones + Hechos (star schema) para consultas analíticas y filtros rápidos.
- **Motor sugerido**: PostgreSQL
- **Variable de conexión**: `DATABASE_URL`

**Tablas Principales**:
- **DimEmpresa**: información de la empresa/entidad.
  - id_empresa (SERIAL, PK)
  - nombre (TEXT)
  - tipo (TEXT) -- (Propia/Externa)
  - region (TEXT)

- **DimDepartamento**: departamentos
  - id_departamento (SERIAL, PK)
  - nombre_departamento (TEXT) UNIQUE

- **DimPuesto**: puestos/cargos
  - id_puesto (SERIAL, PK)
  - nombre_puesto (TEXT) UNIQUE
  - nivel (TEXT) -- (Junior/Senior/Manager)

- **DimSucursal**: ubicación / ciudad
  - id_sucursal (SERIAL, PK)
  - ciudad (TEXT)
  - direccion (TEXT)

- **DimEmpleado**: datos estáticos del empleado
  - id_empleado (BIGINT, PK)
  - nombre (TEXT)
  - genero (TEXT)
  - fecha_ingreso (DATE)
  - estado (TEXT) -- (Activo/Inactivo)
  - id_departamento (INT, FK -> DimDepartamento)
  - id_puesto (INT, FK -> DimPuesto)
  - id_sucursal (INT, FK -> DimSucursal)
  - id_empresa (INT, FK -> DimEmpresa)

- **Fact_Nomina**: nómina por periodo
  - id_nomina (BIGSERIAL, PK)
  - id_empleado (BIGINT, FK -> DimEmpleado)
  - periodo (DATE)
  - salario_base (NUMERIC)
  - bonos (NUMERIC)
  - beneficios (NUMERIC)
  - horas_trabajadas (INT)
  - neto_pagado (NUMERIC)

- **Fact_Evaluacion**: evaluaciones/performance
  - id_eval (BIGSERIAL, PK)
  - id_empleado (BIGINT, FK -> DimEmpleado)
  - fecha_evaluacion (DATE)
  - puntaje (NUMERIC) -- escala 0-100
  - categoria (TEXT)

- **Fact_Capacitacion**:
  - id_cap (BIGSERIAL, PK)
  - id_empleado (BIGINT, FK -> DimEmpleado)
  - fecha (DATE)
  - horas (INT)
  - tema (TEXT)

- **Fact_Asistencia**: ausentismo y asistencia
  - id_asistencia (BIGSERIAL, PK)
  - id_empleado (BIGINT, FK -> DimEmpleado)
  - fecha (DATE)
  - tipo (TEXT) -- (Presente, Ausente, Permiso)
  - minutos_perdidos (INT)

**Índices recomendados**:
- Índice compuesto en `Fact_Nomina(id_empleado, periodo)` para consultas por empleado/periodo.
- Índice por `Fact_Nomina(salario_base)` para histogramas/distribución.
- Índices en `DimEmpleado(id_departamento)`, `DimEmpleado(id_puesto)`, `DimEmpleado(id_sucursal)`, `DimEmpleado(genero)` para filtros rápidos.

**Ejemplos `CREATE TABLE` (simplificados)**:

```sql
CREATE TABLE DimEmpresa (
  id_empresa SERIAL PRIMARY KEY,
  nombre TEXT NOT NULL,
  tipo TEXT,
  region TEXT
);

CREATE TABLE DimDepartamento (
  id_departamento SERIAL PRIMARY KEY,
  nombre_departamento TEXT NOT NULL UNIQUE
);

CREATE TABLE DimPuesto (
  id_puesto SERIAL PRIMARY KEY,
  nombre_puesto TEXT NOT NULL UNIQUE,
  nivel TEXT
);

CREATE TABLE DimSucursal (
  id_sucursal SERIAL PRIMARY KEY,
  ciudad TEXT,
  direccion TEXT
);

CREATE TABLE DimEmpleado (
  id_empleado BIGINT PRIMARY KEY,
  nombre TEXT,
  genero TEXT,
  fecha_ingreso DATE,
  estado TEXT,
  id_departamento INT REFERENCES DimDepartamento(id_departamento),
  id_puesto INT REFERENCES DimPuesto(id_puesto),
  id_sucursal INT REFERENCES DimSucursal(id_sucursal),
  id_empresa INT REFERENCES DimEmpresa(id_empresa)
);

CREATE TABLE Fact_Nomina (
  id_nomina BIGSERIAL PRIMARY KEY,
  id_empleado BIGINT REFERENCES DimEmpleado(id_empleado),
  periodo DATE,
  salario_base NUMERIC(12,2),
  bonos NUMERIC(12,2),
  beneficios NUMERIC(12,2),
  neto_pagado NUMERIC(12,2)
);
```

**Consultas útiles de ejemplo**:
- Headcount por departamento:
```sql
SELECT d.nombre_departamento, COUNT(*) AS headcount
FROM DimEmpleado e
JOIN DimDepartamento d ON e.id_departamento = d.id_departamento
WHERE e.estado = 'Activo'
GROUP BY d.nombre_departamento;
```

- Salario promedio filtrado:
```sql
SELECT AVG(salario_base) as salario_prom
FROM Fact_Nomina n
JOIN DimEmpleado e ON n.id_empleado = e.id_empleado
WHERE e.id_departamento = 3
  AND n.periodo BETWEEN '2024-01-01' AND '2024-12-31';
```

**Notas de diseño / recomendaciones**:
- Usar tipos `NUMERIC` para montos monetarios y `BIGINT` para identificadores de empleados si provienen de sistemas externos.
- Mantener `DimEmpleado` lo más “estático” posible; cambios frecuentes (p.ej. puesto) pueden versionarse o modelarse en una tabla de historial si se requiere trazabilidad.
- Para cargas grandes, particionar `Fact_Nomina` por `periodo` (range partition) mejora rendimiento.
- Añadir vistas materializadas para KPIs costosos (headcount mensual, salario promedio por mes) y refrescarlas periódicamente.

**ER (Descripción rápida)**:
- `DimEmpleado` conecta con `DimDepartamento`, `DimPuesto`, `DimSucursal`, `DimEmpresa`.
- Las tablas de hechos (`Fact_Nomina`, `Fact_Evaluacion`, `Fact_Capacitacion`, `Fact_Asistencia`) referencian `DimEmpleado` por `id_empleado`.

---

Si quieres, puedo:
- Añadir el SQL completo para todas las tablas y constraints en `bd.sql` (si quieres que lo actualice),
- Generar un diagrama ER en formato PNG o Mermaid y añadirlo al repositorio,
- Crear vistas materializadas sugeridas para los KPIs del `resumen_ejecutivo()`.

Indica cuál prefieres y lo implemento.