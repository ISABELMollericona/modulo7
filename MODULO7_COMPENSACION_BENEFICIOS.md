# Módulo 7: Compensación y Beneficios

## Objetivo del módulo
Analizar la equidad salarial, la competitividad externa y la efectividad de los programas de beneficios dentro de la organización.

Este módulo responde preguntas como:
- ¿Los empleados reciben salarios justos frente a puestos similares?
- ¿La empresa paga por encima o por debajo del mercado?
- ¿Cuánto cuesta realmente el esquema de beneficios?
- ¿Cómo se distribuyen los bonos entre empleados y departamentos?

## Fuentes de datos potenciales
- Sistema de nómina
- Encuestas salariales de mercado
- Registros de beneficios
- Datos de empleados, puestos, departamentos y sucursales

## Dimensiones clave
- Tiempo
- Empleado
- Beneficio
- Rango salarial
- Mercado laboral
- Puesto
- Departamento
- Sucursal
- Tipo de contrato
- Género
- Estado laboral

## Hechos y métricas principales

### 1. Equidad salarial interna
Compara salarios entre puestos similares dentro de la organización para detectar brechas injustificadas.

### 2. Competitividad salarial externa
Compara el salario interno con una referencia de mercado para saber si la empresa está por encima, por debajo o en paridad.

### 3. Costo de beneficios por empleado
Mide la inversión total en beneficios, ya sea por empleado, por departamento o por empresa.

### 4. Distribución de bonos
Analiza cómo se asignan los incentivos y si están concentrados en pocos empleados o más repartidos.

## Consultas implementadas en `app.py` y su propósito

### Consultas SQL utilizadas

Estas son las consultas base que usa el módulo. Están simplificadas para que se entienda la lógica sin perder el objetivo de cada cálculo.

#### A. Resumen ejecutivo

```sql
WITH benchmark_externo_tiempo AS (
	SELECT b.TiempoKey, b.PuestoKey, AVG(COALESCE(b.SalarioMercadoMed, 0)) AS SalarioMercadoMedExterno
	FROM Ref_Benchmark_Salarial b
	INNER JOIN DimEmpresa eb ON b.EmpresaKey = eb.EmpresaKey
	WHERE COALESCE(eb.EsEmpresaPropia, FALSE) = FALSE
	GROUP BY b.TiempoKey, b.PuestoKey
), benchmark_externo_puesto AS (
	SELECT b.PuestoKey, AVG(COALESCE(b.SalarioMercadoMed, 0)) AS SalarioMercadoMedExterno
	FROM Ref_Benchmark_Salarial b
	INNER JOIN DimEmpresa eb ON b.EmpresaKey = eb.EmpresaKey
	WHERE COALESCE(eb.EsEmpresaPropia, FALSE) = FALSE
	GROUP BY b.PuestoKey
)
SELECT
	AVG(CASE
		WHEN COALESCE(bet.SalarioMercadoMedExterno, bep.SalarioMercadoMedExterno, 0) = 0 THEN NULL
		ELSE (COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0))
				 / COALESCE(bet.SalarioMercadoMedExterno, bep.SalarioMercadoMedExterno, 0)
	END) AS competitividad,
	SUM(n.Beneficios) AS beneficios,
	SUM(n.Bono) AS bonos,
	COUNT(*) AS headcount,
	AVG(COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0)) AS salario_promedio
FROM Fact_Nomina n
INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
LEFT JOIN benchmark_externo_tiempo bet ON n.PuestoKey = bet.PuestoKey AND n.TiempoKey = bet.TiempoKey
LEFT JOIN benchmark_externo_puesto bep ON n.PuestoKey = bep.PuestoKey
WHERE /* filtros dinámicos */;
```

Qué hace:
- Compara salario interno vs mercado.
- Calcula total de beneficios y bonos.
- Cuenta empleados activos.
- Calcula salario promedio total.

#### B. Beneficios por departamento

```sql
SELECT d.NombreDepartamento, SUM(COALESCE(n.Beneficios,0))
FROM Fact_Nomina n
INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
WHERE /* filtros dinámicos */
GROUP BY d.NombreDepartamento
ORDER BY 2 DESC;
```

Qué devuelve:
- Total de beneficios por área.
- Sirve para ver dónde se concentra la inversión en beneficios.

#### C. Top 20 bonos

```sql
SELECT e.NombreCompleto, COALESCE(n.Bono,0)
FROM Fact_Nomina n
INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
WHERE /* filtros dinámicos */
ORDER BY 2 DESC
LIMIT 20;
```

Qué devuelve:
- Los empleados con bono más alto.
- Sirve para revisar si los incentivos están concentrados o repartidos.

#### D. Equidad salarial por puesto

```sql
SELECT
	COALESCE(e.NombreCompleto, 'SIN NOMBRE') AS Empleado,
	COALESCE(p.NombrePuesto, 'SIN PUESTO') AS Puesto,
	COALESCE(n.SalarioBase, 0) AS SalarioBase,
	AVG(COALESCE(n.SalarioBase, 0)) OVER (PARTITION BY n.PuestoKey) AS Promedio,
	(COALESCE(n.SalarioBase, 0) - AVG(COALESCE(n.SalarioBase, 0)) OVER (PARTITION BY n.PuestoKey))
		/ AVG(COALESCE(n.SalarioBase, 0)) OVER (PARTITION BY n.PuestoKey) AS IndiceEquidad
FROM Fact_Nomina n
INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey
WHERE /* filtros dinámicos */
LIMIT 50;
```

Qué devuelve:
- Diferencia entre salario de cada persona y el promedio de su puesto.
- Sirve para medir equidad interna.

#### E. Distribución por género

```sql
SELECT COALESCE(e.Genero, 'N/A'), COUNT(*), AVG(COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0))
FROM Fact_Nomina n
INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
WHERE /* filtros dinámicos */
GROUP BY e.Genero
ORDER BY 2 DESC;
```

Qué devuelve:
- Cantidad de empleados por género.
- Salario promedio por género.

#### F. Tipo de contrato

```sql
SELECT COALESCE(n.TipoContrato, 'N/A'), COUNT(*), SUM(COALESCE(n.Bono,0))
FROM Fact_Nomina n
INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
WHERE /* filtros dinámicos */
GROUP BY n.TipoContrato
ORDER BY 2 DESC;
```

Qué devuelve:
- Número de empleados por tipo de contrato.
- Ayuda a entender la estructura laboral.

#### G. Distribución de salarios

```sql
SELECT COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0) AS SalarioTotal
FROM Fact_Nomina n
INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
WHERE /* filtros dinámicos */
ORDER BY 1;
```

Qué devuelve:
- Lista de salarios totales para construir un histograma.
- Sirve para ver dispersión, outliers y concentración salarial.

#### H. Ausentismo por departamento

```sql
SELECT COALESCE(d.NombreDepartamento, 'SIN DEPTO'), AVG(COALESCE(a.TasaAusentismo, 0)), COUNT(DISTINCT a.EmpleadoKey)
FROM Fact_Asistencia a
INNER JOIN DimEmpresa ei ON a.EmpresaKey = ei.EmpresaKey
LEFT JOIN DimEmpleado e ON a.EmpleadoKey = e.EmpleadoKey
LEFT JOIN Fact_Nomina n ON n.EmpleadoKey = e.EmpleadoKey
LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
WHERE /* filtros dinámicos */
GROUP BY d.NombreDepartamento
ORDER BY 2 DESC
LIMIT 15;
```

Qué devuelve:
- Tasa promedio de ausentismo por área.
- Ayuda a relacionar bienestar con compensación.

#### I. Desempeño vs salario

```sql
SELECT
	COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0),
	COALESCE(ev.PuntajeDesempeno, 0),
	COALESCE(e.NombreCompleto, 'SIN NOMBRE')
FROM Fact_Nomina n
INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
LEFT JOIN Fact_Evaluacion ev ON n.EmpleadoKey = ev.EmpleadoKey
WHERE /* filtros dinámicos */
LIMIT 100;
```

Qué devuelve:
- Relación entre salario total y desempeño.
- Sirve para validar meritocracia.

#### J. Top vs bottom performers

```sql
SELECT COALESCE(e.NombreCompleto, 'SIN NOMBRE'), COALESCE(ev.PuntajeDesempeno, 0)
FROM Fact_Nomina n
INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
LEFT JOIN Fact_Evaluacion ev ON n.EmpleadoKey = ev.EmpleadoKey
WHERE /* filtros dinámicos */
ORDER BY COALESCE(ev.PuntajeDesempeno, 0) DESC
LIMIT 50;
```

Qué devuelve:
- Ranking de mejor desempeño.
- Base para comparar con quienes están por debajo.

#### K. Detalle integral de empleados

```sql
WITH nomagg AS (
	SELECT n.EmpleadoKey, MAX(n.EmpresaKey) AS EmpresaKey, MAX(n.PuestoKey) AS PuestoKey,
				 MAX(n.DepartamentoKey) AS DepartamentoKey, MAX(n.SucursalKey) AS SucursalKey,
				 MAX(n.TipoContrato) AS TipoContrato,
				 AVG(COALESCE(n.SalarioBase, 0)) AS SalarioBasePromedio,
				 SUM(COALESCE(n.Bono, 0)) AS BonoAcumulado,
				 SUM(COALESCE(n.Beneficios, 0)) AS BeneficiosAcumulados,
				 SUM(COALESCE(n.CostoTotalNomina, 0)) AS CostoTotalNomina,
				 MAX(COALESCE(n.AntiguedadMeses, 0)) AS AntiguedadMeses,
				 MAX(COALESCE(n.EdadActual, 0)) AS EdadActual,
				 BOOL_OR(COALESCE(n.FlagActivo, FALSE)) AS FlagActivo
	FROM Fact_Nomina n
	INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
	LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
	LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey
	LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
	LEFT JOIN DimSucursal s ON n.SucursalKey = s.SucursalKey
	WHERE /* filtros dinámicos */
	GROUP BY n.EmpleadoKey
)
SELECT ...
FROM nomagg n
LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey
LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
LEFT JOIN DimSucursal s ON n.SucursalKey = s.SucursalKey
LEFT JOIN DimEmpresa emp ON n.EmpresaKey = emp.EmpresaKey;
```

Qué devuelve:
- La ficha completa del empleado.
- Sirve para auditoría, análisis de compensación total y seguimiento de RRHH.

### 1. `resumen_ejecutivo()`
Esta consulta resume el estado general del módulo con KPIs principales.

Devuelve:
- **Competitividad**: promedio del salario interno dividido entre la referencia de mercado.
- **Beneficios**: suma total de beneficios pagados.
- **Bonos**: suma total de bonos pagados.
- **Headcount**: cantidad de empleados activos.
- **Salario promedio**: promedio del salario total interno.

Objetivo:
- Dar una visión ejecutiva rápida del estado de compensación.
- Detectar si el costo de nómina sube o baja.
- Ver si los beneficios y bonos están concentrados o controlados.

Resultado esperado:
- Si `competitividad` es cercana a `1.0`, la empresa está alineada con el mercado.
- Si `beneficios` y `bonos` suben mucho, el costo total de compensación aumenta.
- Si `headcount` cambia de forma brusca, hay variación relevante en la plantilla activa.

### 2. `grafica_competitividad()`
Muestra el salario interno frente al salario de mercado para los principales empleados o puestos.

Devuelve:
- Barras comparativas de **salario interno** vs **mercado**.

Objetivo:
- Ver si la empresa está pagando por encima o por debajo del mercado.
- Detectar posiciones críticas con riesgo de fuga por baja competitividad.

### 3. `grafica_beneficios()`
Resume los beneficios por departamento.

Devuelve:
- Total o ratio de beneficios por área.

Objetivo:
- Identificar qué departamentos reciben más inversión en beneficios.
- Comparar áreas y detectar desigualdades en la asignación de recursos.

### 4. `grafica_bonos()`
Lista el top 20 de bonos pagados.

Devuelve:
- Empleados con mayor bono.
- Diferenciación visual entre el bono más alto, el top 5 y el resto.

Objetivo:
- Ver la distribución de incentivos.
- Detectar si los bonos están muy concentrados en pocos empleados.
- Identificar posibles sesgos o criterios poco equilibrados.

### 5. `grafica_equidad()`
Calcula el salario promedio por puesto y sirve como base para revisar equidad interna.

Devuelve:
- Promedio salarial por puesto.

Objetivo:
- Comparar salarios dentro de roles similares.
- Detectar puestos con desviaciones salariales importantes.
- Apoyar decisiones de ajuste salarial.

### 6. `equidad()`
Construye la tabla detallada de equidad salarial por empleado.

Devuelve:
- Empleado
- Puesto
- Salario base
- Promedio del puesto
- Índice de equidad
- Desviación absoluta

Objetivo:
- Tener una lectura precisa de la brecha salarial interna.
- Ver qué empleados están por encima o por debajo del promedio de su puesto.
- Priorizar ajustes o revisiones salariales.

### 7. `grafica_genero()`
Analiza la distribución por género junto con el salario promedio.

Devuelve:
- Cantidad de empleados por género.
- Salario promedio por género.

Objetivo:
- Revisar equidad y representación.
- Detectar posibles diferencias salariales entre géneros.

### 8. `grafica_tipo_contrato()`
Muestra la distribución de empleados por tipo de contrato.

Devuelve:
- Proporción de contratos indefinidos, temporales, por obra, practicantes, etc.

Objetivo:
- Entender la composición laboral.
- Ver si la empresa depende demasiado de contratos temporales.
- Relacionar el tipo de contrato con costos y beneficios.

### 9. `grafica_distribucion_salarios()`
Analiza la distribución total de salarios.

Devuelve:
- Histograma de salarios totales.

Objetivo:
- Ver la concentración salarial.
- Detectar outliers, dispersión y tramos dominantes.
- Entender la estructura de compensación.

### 10. `grafica_ausentismo()`
Mide la tasa de ausentismo por departamento.

Devuelve:
- Tasa promedio de ausentismo.
- Ranking por departamento.

Objetivo:
- Relacionar compensación y beneficios con salud organizacional.
- Detectar áreas con mayor ausentismo.
- Revisar si los programas de bienestar están funcionando.

### 11. `grafica_desempeno_vs_salario()`
Cruza el salario total con el desempeño.

Devuelve:
- Scatter de salario vs puntaje de desempeño.

Objetivo:
- Validar si el salario acompaña el rendimiento.
- Encontrar casos de alto desempeño con baja compensación.
- Detectar posibles desalineaciones en meritocracia.

### 12. `grafica_top_bottom()`
Compara empleados con mejor y peor desempeño.

Devuelve:
- Top performers
- Bottom performers

Objetivo:
- Analizar si el desempeño está vinculado a la compensación.
- Identificar talento clave.
- Detectar empleados que requieren intervención o reconocimiento.

### 13. `detalle_empleados()`
Agrupa información de nómina, desempeño, capacitación y asistencia por empleado.

Devuelve:
- Datos personales y laborales
- Salario, bonos, beneficios y costo de nómina
- Desempeño, capacitación y ausentismo

Objetivo:
- Tener una ficha completa por empleado.
- Permitir análisis más finos de compensación total.
- Dar soporte a auditorías, revisión de equidad y decisiones de RRHH.

## Interpretación general de los resultados

Cuando el dashboard muestra resultados de estas consultas, lo que se obtiene es una lectura integral del módulo:
- **Resumen ejecutivo**: muestra el estado global de la compensación.
- **Gráficas de beneficios y bonos**: permiten ver si la inversión está distribuida de forma razonable.
- **Equidad interna**: ayuda a validar si personas con roles similares tienen salarios coherentes.
- **Competitividad externa**: muestra si la empresa está alineada con el mercado laboral.
- **Relación con desempeño**: permite revisar si la política salarial recompensa realmente el rendimiento.
- **Ausentismo y tipo de contrato**: complementan el análisis con señales de clima, estabilidad y estructura de personal.

## Conclusión
El módulo 7 no solo calcula salarios; construye una visión de justicia interna, posicionamiento externo y eficiencia de los beneficios. Esto permite tomar decisiones de RRHH basadas en evidencia y no solo en intuición.
