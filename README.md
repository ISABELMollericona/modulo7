# Modulo7 - Dashboard RRHH Avanzado

Dashboard de Recursos Humanos con análisis avanzado de datos de nómina, beneficios, equidad salarial y desempeño de empleados.

## Características

- 📊 **10+ Gráficos Estadísticos**: Competitividad, beneficios, bonos, equidad, género, tipo de contrato, distribución salarial, ausentismo, desempeño vs salario, top/bottom performers
- 🔍 **Sistema de Filtros Avanzado**: Filtrado por departamento, puesto, ciudad, tipo contrato, género, estado y rango salarial/antigüedad
- 📋 **Resumen Ejecutivo**: KPIs principales (competitividad, promedio beneficios, bonos, headcount, salario promedio)
- 👥 **Tabla de Equidad Salarial**: Análisis de brecha salarial por género y departamento
- 👤 **Detalle de Empleados**: Información completa con agregaciones de nómina, evaluación, capacitación y asistencia
- 💡 **Tolerancia de Filtros**: Los filtros aceptan entrada libre - si no coinciden con valores conocidos, se ignoran sin bloquear datos

## Requisitos

- Python 3.10+
- PostgreSQL (o Neon PostgreSQL)
- Variables de entorno: `DATABASE_URL`

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/modulo7.git
cd modulo7

# Crear ambiente virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar base de datos
# Ejecutar bd.sql en tu PostgreSQL:
# psql -U usuario -d base_datos -f bd.sql
```

## Uso

```bash
# Desarrollo
python app.py

# Producción (con Gunicorn)
gunicorn app:app --bind 0.0.0.0:5000
```

La aplicación estará disponible en `http://localhost:5001` (desarrollo) o `http://0.0.0.0:5000` (producción).

## Estructura

- `app.py` - Aplicación Flask con todas las rutas, lógica de filtrado y generación de gráficos
- `bd.sql` - Schema SQL y datos iniciales
- `requirements.txt` - Dependencias Python
- `ALGORITMOS.md` - Documentación de algoritmos y cálculos

## Parámetros de Filtro

La URL acepta los siguientes parámetros de query:

- `departamento` - Filtrar por departamento
- `puesto` - Filtrar por puesto
- `ciudad` - Filtrar por sucursal/ciudad
- `tipo_contrato` - Filtrar por tipo de contrato
- `genero` - Filtrar por género (M/F)
- `estado` - Filtrar por estado (Activo/Inactivo)
- `antiguedad_min` - Antigüedad mínima en años
- `antiguedad_max` - Antigüedad máxima en años
- `salario_min` - Salario mínimo
- `salario_max` - Salario máximo

Ejemplo:
```
http://localhost:5001/?departamento=Ventas&genero=M&salario_min=50000
```

## Despliegue en Railway

1. Crear proyecto en [Railway](https://railway.app)
2. Conectar repositorio GitHub
3. Configurar variable de entorno: `DATABASE_URL`
4. Railway detectará `requirements.txt` y `Procfile` automáticamente
5. Desplegar

## Arquitectura

- **Backend**: Flask 3.0+
- **Frontend**: Plotly.js (CDN), Font Awesome 6.4.0
- **Base de Datos**: PostgreSQL con conexión remota Neon
- **Servidor**: Gunicorn (producción)

## API Endpoints

- `GET /` - Dashboard principal con todos los gráficos
- `GET /favicon.ico` - Respuesta vacía para favicon
- Errores 404/500 devuelven HTML con traceback

## Contribución

Las modificaciones de filtros deben seguir el patrón:
1. Agregar parámetro a `build_filter_where()`
2. Agregar normalización en `home()` con `normalize_filter_value()`
3. Pasar parámetro a todas las funciones que generen visualizaciones

## Notas de Desarrollo

- Los filtros usan consultas parameterizadas para prevenir SQL injection
- El sistema tolera entrada de usuario: valores no coincidentes se ignoran
- Las funciones de gráficos requieren actualizarse si se agregan nuevos filtros
- Jinja2 cachea templates - considerar usar archivo externo si hay problemas de actualización

## Licencia

Privado - Proyecto Interno

