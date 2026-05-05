from flask import Flask, render_template_string, request, Response
import psycopg2
import plotly.graph_objects as go
import traceback
from typing import List, Tuple, Dict, Any
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.config["PROPAGATE_EXCEPTIONS"] = False  # queremos manejarlo nosotros
app.jinja_env.cache = None  # Deshabilitar caché de Jinja2

@app.errorhandler(Exception)
def handle_exception(e):
    # Mantener códigos HTTP reales (404, 405, etc.) en lugar de convertirlos en 500.
    if isinstance(e, HTTPException):
        return e.get_response()

    tb = traceback.format_exc()
    print("=" * 60)
    print("EXCEPCIÓN GLOBAL:")
    print(tb)
    print("=" * 60)
    html = f"""
    <!DOCTYPE html><html><head><meta charset='UTF-8'>
    <title>Error — Dashboard RRHH</title>
    <style>
      body {{ font-family: monospace; background: #0d1117; color: #f0f6fc; padding: 40px; }}
      h1 {{ color: #f85149; margin-bottom: 20px; }}
      pre {{ background: #161b22; border: 1px solid #f85149; border-radius: 8px;
             padding: 20px; white-space: pre-wrap; word-break: break-all;
             color: #ffa198; font-size: 0.85rem; line-height: 1.6; }}
      p {{ color: #8b949e; margin-bottom: 16px; }}
    </style></head><body>
    <h1>⚠️ Error en el servidor</h1>
    <p>Copia este traceback y pégalo para que pueda corregirlo:</p>
    <pre>{tb}</pre>
    </body></html>
    """
    return html, 500

# ======================================================
# 🔥 CONEXIÓN NEON
# ======================================================
DATABASE_URL = "postgresql://neondb_owner:npg_EHKwDAa6t8PM@ep-ancient-voice-anfnctl8-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_connection():
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)


def get_empresas():
  conn = get_connection()
  cur = conn.cursor()
  cur.execute("SELECT EmpresaKey, IdEmpresaNegocio, NombreEmpresa, EsEmpresaPropia FROM DimEmpresa ORDER BY EmpresaKey;")
  rows = cur.fetchall()
  cur.close()
  conn.close()
  return rows


def get_filter_options(empresa_key: int | None = None):
    """Obtiene opciones de filtro dinámicamente."""
    conn = get_connection()
    cur = conn.cursor()
    empresa_filter = "ei.EmpresaKey = %s" if empresa_key is not None else "COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE"
    params = (empresa_key,) if empresa_key is not None else ()
    
    result = {}
    
    # Departamentos
    cur.execute(f"SELECT DISTINCT COALESCE(d.NombreDepartamento, 'SIN DEPARTAMENTO') FROM Fact_Nomina n INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey WHERE {empresa_filter} ORDER BY 1;", params)
    result["departamentos"] = [r[0] for r in cur.fetchall()]
    
    # Puestos
    cur.execute(f"SELECT DISTINCT COALESCE(p.NombrePuesto, 'SIN PUESTO') FROM Fact_Nomina n INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey WHERE {empresa_filter} ORDER BY 1;", params)
    result["puestos"] = [r[0] for r in cur.fetchall()]
    
    # Ciudades
    cur.execute(f"SELECT DISTINCT COALESCE(s.Ciudad, 'SIN CIUDAD') FROM Fact_Nomina n INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey LEFT JOIN DimSucursal s ON n.SucursalKey = s.SucursalKey WHERE {empresa_filter} ORDER BY 1;", params)
    result["ciudades"] = [r[0] for r in cur.fetchall()]
    
    # Tipos de contrato
    cur.execute(f"SELECT DISTINCT COALESCE(n.TipoContrato, 'N/A') FROM Fact_Nomina n INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey WHERE {empresa_filter} ORDER BY 1;", params)
    result["tipos_contrato"] = [r[0] for r in cur.fetchall()]
    
    # Géneros
    cur.execute(f"SELECT DISTINCT COALESCE(e.Genero, 'N/A') FROM Fact_Nomina n INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey WHERE {empresa_filter} ORDER BY 1;", params)
    result["generos"] = [r[0] for r in cur.fetchall()]
    
    # Estados de empleado
    cur.execute(f"SELECT DISTINCT COALESCE(e.EstadoActual, 'N/A') FROM Fact_Nomina n INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey WHERE {empresa_filter} ORDER BY 1;", params)
    result["estados"] = [r[0] for r in cur.fetchall()]
    
    cur.close()
    conn.close()
    return result


def normalize_filter_value(value, valid_values):
    """Devuelve el valor escrito solo si coincide con una opción válida; si no, None."""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    normalized = text.casefold()
    for option in valid_values or []:
        if str(option).strip().casefold() == normalized:
            return option

    return None


def build_filter_where(empresa_key: int | None, departamento: str | None, puesto: str | None, ciudad: str | None, tipo_contrato: str | None, genero: str | None, estado: str | None, antigüedad_min: int | None, antigüedad_max: int | None, salario_min: float | None, salario_max: float | None) -> tuple[str, tuple]:
    """Construye WHERE clause dinámicamente basado en filtros."""
    conditions = []
    params = []
    
    if empresa_key is not None:
        conditions.append("n.EmpresaKey = %s")
        params.append(empresa_key)
    else:
        conditions.append("COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE")
    
    if departamento and departamento != "":
        conditions.append("COALESCE(d.NombreDepartamento, 'SIN DEPARTAMENTO') = %s")
        params.append(departamento)
    
    if puesto and puesto != "":
        conditions.append("COALESCE(p.NombrePuesto, 'SIN PUESTO') = %s")
        params.append(puesto)
    
    if ciudad and ciudad != "":
        conditions.append("COALESCE(s.Ciudad, 'SIN CIUDAD') = %s")
        params.append(ciudad)
    
    if tipo_contrato and tipo_contrato != "":
        conditions.append("COALESCE(n.TipoContrato, 'N/A') = %s")
        params.append(tipo_contrato)
    
    if genero and genero != "":
        conditions.append("COALESCE(e.Genero, 'N/A') = %s")
        params.append(genero)
    
    if estado and estado != "":
        conditions.append("COALESCE(e.EstadoActual, 'N/A') = %s")
        params.append(estado)
    
    if antigüedad_min is not None and antigüedad_min > 0:
        conditions.append("COALESCE(n.AntiguedadMeses, 0) >= %s")
        params.append(antigüedad_min)
    
    if antigüedad_max is not None and antigüedad_max > 0:
        conditions.append("COALESCE(n.AntiguedadMeses, 0) <= %s")
        params.append(antigüedad_max)
    
    if salario_min is not None and salario_min > 0:
        conditions.append("(COALESCE(n.SalarioBase, 0) + COALESCE(n.Bono, 0) + COALESCE(n.Beneficios, 0)) >= %s")
        params.append(salario_min)
    
    if salario_max is not None and salario_max > 0:
        conditions.append("(COALESCE(n.SalarioBase, 0) + COALESCE(n.Bono, 0) + COALESCE(n.Beneficios, 0)) <= %s")
        params.append(salario_max)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, tuple(params)


# ======================================================
# 📊 KPI COMPENSACIÓN
# ======================================================
def kpi_compensacion(empresa_key: int | None = None):
    conn = get_connection()
    cur = conn.cursor()
    empresa_filter = "ei.EmpresaKey = %s" if empresa_key is not None else "COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE"
    params = (empresa_key,) if empresa_key is not None else ()
    cur.execute(f"""
      WITH benchmark_externo_tiempo AS (
      SELECT
        b.TiempoKey,
        b.PuestoKey,
        AVG(COALESCE(b.SalarioMercadoMed, 0)) AS SalarioMercadoMedExterno
      FROM Ref_Benchmark_Salarial b
      INNER JOIN DimEmpresa eb ON b.EmpresaKey = eb.EmpresaKey
      WHERE COALESCE(eb.EsEmpresaPropia, FALSE) = FALSE
      GROUP BY b.TiempoKey, b.PuestoKey
      ),
      benchmark_externo_puesto AS (
        SELECT
          b.PuestoKey,
          AVG(COALESCE(b.SalarioMercadoMed, 0)) AS SalarioMercadoMedExterno
        FROM Ref_Benchmark_Salarial b
        INNER JOIN DimEmpresa eb ON b.EmpresaKey = eb.EmpresaKey
        WHERE COALESCE(eb.EsEmpresaPropia, FALSE) = FALSE
        GROUP BY b.PuestoKey
    )
        SELECT 
            e.NombreCompleto AS Empleado,
            p.NombrePuesto AS Puesto,
            (COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0)) AS SalarioInterno,
        COALESCE(bet.SalarioMercadoMedExterno, bep.SalarioMercadoMedExterno, 0) AS SalarioMercado,
            CASE 
          WHEN COALESCE(bet.SalarioMercadoMedExterno, bep.SalarioMercadoMedExterno, 0) = 0 THEN 0
                ELSE (COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0)) 
             / COALESCE(bet.SalarioMercadoMedExterno, bep.SalarioMercadoMedExterno, 0)
            END AS IndiceCompetitividad
        FROM Fact_Nomina n
    INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
        LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
        LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey
      LEFT JOIN benchmark_externo_tiempo bet
        ON n.PuestoKey = bet.PuestoKey
         AND n.TiempoKey = bet.TiempoKey
      LEFT JOIN benchmark_externo_puesto bep
        ON n.PuestoKey = bep.PuestoKey
    WHERE {empresa_filter}
        LIMIT 50;
    """, params)
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

# ======================================================
# 📊 GRÁFICA COMPETITIVIDAD
# ======================================================

def grafica_competitividad(empresa_key: int | None = None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        empresa_filter = "ei.EmpresaKey = %s" if empresa_key is not None else "COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE"
        params = (empresa_key,) if empresa_key is not None else ()

        cur.execute(f"""
           WITH benchmark_externo_tiempo AS (
            SELECT
              b.TiempoKey,
              b.PuestoKey,
              AVG(COALESCE(b.SalarioMercadoMed, 0)) AS SalarioMercadoMedExterno
            FROM Ref_Benchmark_Salarial b
            INNER JOIN DimEmpresa eb ON b.EmpresaKey = eb.EmpresaKey
            WHERE COALESCE(eb.EsEmpresaPropia, FALSE) = FALSE
            GROUP BY b.TiempoKey, b.PuestoKey
          ),
          benchmark_externo_puesto AS (
            SELECT
              b.PuestoKey,
              AVG(COALESCE(b.SalarioMercadoMed, 0)) AS SalarioMercadoMedExterno
            FROM Ref_Benchmark_Salarial b
            INNER JOIN DimEmpresa eb ON b.EmpresaKey = eb.EmpresaKey
            WHERE COALESCE(eb.EsEmpresaPropia, FALSE) = FALSE
            GROUP BY b.PuestoKey
          )
           SELECT 
                COALESCE(e.NombreCompleto, 'SIN NOMBRE') AS Empleado,
                COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0) AS Interno,
            COALESCE(bet.SalarioMercadoMedExterno, bep.SalarioMercadoMedExterno, 0) AS Mercado
            FROM Fact_Nomina n
          INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
            LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
          LEFT JOIN benchmark_externo_tiempo bet
            ON n.PuestoKey = bet.PuestoKey 
          AND n.TiempoKey = bet.TiempoKey
          LEFT JOIN benchmark_externo_puesto bep
            ON n.PuestoKey = bep.PuestoKey
          WHERE {empresa_filter}
            LIMIT 20;
        """, params)

        data = cur.fetchall()

        empleados = [str(r[0]) for r in data]
        interno = [float(r[1] or 0) for r in data]
        mercado = [float(r[2] or 0) for r in data]

        fig = go.Figure()
        fig.add_bar(name="Interno", x=empleados, y=interno)
        fig.add_bar(name="Mercado", x=empleados, y=mercado)

        fig.update_layout(barmode="group", title="Competitividad Salarial")

        html = fig.to_html(full_html=False, include_plotlyjs=False)

        cur.close()
        conn.close()

        return html, None

    except Exception:
        return "", traceback.format_exc()



# ======================================================
# 📊 GRÁFICA BENEFICIOS POR DEPARTAMENTO
# ======================================================
def grafica_beneficios(empresa_key: int | None = None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        empresa_filter = "ei.EmpresaKey = %s" if empresa_key is not None else "COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE"
        params = (empresa_key,) if empresa_key is not None else ()

        cur.execute(f"""
            SELECT 
                d.NombreDepartamento,
                SUM(COALESCE(n.Beneficios,0))
            FROM Fact_Nomina n
          INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
            LEFT JOIN DimDepartamento d 
                ON n.DepartamentoKey = d.DepartamentoKey
          WHERE {empresa_filter}
            GROUP BY d.NombreDepartamento
            ORDER BY 2 DESC;
        """, params)

        data = cur.fetchall()

        deptos = [r[0] for r in data]
        valores = [float(r[1] or 0) for r in data]

        fig = go.Figure()
        fig.add_bar(x=deptos, y=valores)

        fig.update_layout(title="Beneficios por Departamento")

        html = fig.to_html(full_html=False, include_plotlyjs=False)

        cur.close()
        conn.close()

        return html, None

    except Exception:
        return "", traceback.format_exc()


# ======================================================
# 📊 GRÁFICA BONOS TOP 20
# ======================================================
def grafica_bonos(empresa_key: int | None = None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        empresa_filter = "ei.EmpresaKey = %s" if empresa_key is not None else "COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE"
        params = (empresa_key,) if empresa_key is not None else ()

        cur.execute(f"""
            SELECT 
                e.NombreCompleto,
                COALESCE(n.Bono,0)
            FROM Fact_Nomina n
          INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
            LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
          WHERE {empresa_filter}
            ORDER BY 2 DESC
            LIMIT 20;
        """, params)

        data = cur.fetchall()

        empleados = [r[0] for r in data]
        bonos = [float(r[1] or 0) for r in data]

        # colores: destacar el mayor (top1) y los top5, resto en azul
        colors = []
        if bonos:
          sorted_desc = sorted(bonos, reverse=True)
          top5_threshold = sorted_desc[4] if len(sorted_desc) > 4 else (sorted_desc[-1] if sorted_desc else 0)
          max_val = sorted_desc[0] if sorted_desc else 0
          for b in bonos:
            if b == max_val:
              colors.append('#ff7043')  # naranja para el mayor
            elif b >= top5_threshold and b > 0:
              colors.append('#ffd54f')  # dorado para top5
            else:
              colors.append('#6ea0ff')  # azul por defecto

        fig = go.Figure(data=[
          go.Bar(
            x=empleados,
            y=bonos,
            marker=dict(color=colors),
            hovertemplate='%{x}<br>$%{y:,.2f}<extra></extra>'
          )
        ])

        fig.update_layout(title="Top 20 Bonos", showlegend=False)

        html = fig.to_html(full_html=False, include_plotlyjs=False)

        cur.close()
        conn.close()

        return html, None

    except Exception:
        return "", traceback.format_exc()
    
# ======================================================
# 📊 GRÁFICA EQUIDAD SALARIAL
# ======================================================
def grafica_equidad(empresa_key: int | None = None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        empresa_filter = "ei.EmpresaKey = %s" if empresa_key is not None else "COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE"
        params = (empresa_key,) if empresa_key is not None else ()

        cur.execute(f"""
            SELECT 
                p.NombrePuesto,
                AVG(COALESCE(n.SalarioBase,0))
            FROM Fact_Nomina n
          INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
            LEFT JOIN DimPuesto p 
                ON n.PuestoKey = p.PuestoKey
          WHERE {empresa_filter}
            GROUP BY p.NombrePuesto
            ORDER BY 2 DESC;
        """, params)

        data = cur.fetchall()

        puestos = [r[0] for r in data]
        promedios = [float(r[1] or 0) for r in data]

        fig = go.Figure()
        fig.add_bar(x=puestos, y=promedios)

        fig.update_layout(title="Equidad Salarial por Puesto")

        html = fig.to_html(full_html=False, include_plotlyjs=False)

        cur.close()
        conn.close()

        return html, None

    except Exception:
        return "", traceback.format_exc()

# ======================================================
# 📊 GRÁFICA DISTRIBUCIÓN POR GÉNERO
# ======================================================
def grafica_genero(empresa_key: int | None = None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        empresa_filter = "ei.EmpresaKey = %s" if empresa_key is not None else "COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE"
        params = (empresa_key,) if empresa_key is not None else ()
        
        cur.execute(f"""
            SELECT COALESCE(e.Genero, 'N/A'), COUNT(*), AVG(COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0))
            FROM Fact_Nomina n
            INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
            LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
            WHERE {empresa_filter}
            GROUP BY e.Genero
            ORDER BY 2 DESC;
        """, params)
        
        data = cur.fetchall()
        generos = [str(r[0]) for r in data]
        cantidades = [int(r[1]) for r in data]
        salarios_prom = [float(r[2] or 0) for r in data]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Cantidad', x=generos, y=cantidades, marker_color='#4f86c6'))
        fig.add_trace(go.Scatter(name='Salario Promedio', x=generos, y=salarios_prom, yaxis='y2', mode='lines+markers', marker_color='#e07b54'))
        
        fig.update_layout(
            title='Distribución por Género',
            yaxis=dict(title='Cantidad'),
            yaxis2=dict(title='Salario Promedio', overlaying='y', side='right'),
            hovermode='x unified'
        )
        
        html = fig.to_html(full_html=False, include_plotlyjs=False)
        cur.close()
        conn.close()
        return html, None
    except Exception:
        return "", traceback.format_exc()

# ======================================================
# 📊 GRÁFICA DISTRIBUCIÓN POR TIPO CONTRATO
# ======================================================
def grafica_tipo_contrato(empresa_key: int | None = None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        empresa_filter = "ei.EmpresaKey = %s" if empresa_key is not None else "COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE"
        params = (empresa_key,) if empresa_key is not None else ()
        
        cur.execute(f"""
            SELECT COALESCE(n.TipoContrato, 'N/A'), COUNT(*), SUM(COALESCE(n.Bono,0))
            FROM Fact_Nomina n
            INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
            WHERE {empresa_filter}
            GROUP BY n.TipoContrato
            ORDER BY 2 DESC;
        """, params)
        
        data = cur.fetchall()
        contratos = [str(r[0]) for r in data]
        cantidades = [int(r[1]) for r in data]
        
        fig = go.Figure(data=[go.Pie(labels=contratos, values=cantidades, hole=.3)])
        fig.update_layout(title='Distribución por Tipo de Contrato')
        
        html = fig.to_html(full_html=False, include_plotlyjs=False)
        cur.close()
        conn.close()
        return html, None
    except Exception:
        return "", traceback.format_exc()

# ======================================================
# 📊 GRÁFICA DISTRIBUCIÓN DE SALARIOS (HISTOGRAMA)
# ======================================================
def grafica_distribucion_salarios(empresa_key: int | None = None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        empresa_filter = "ei.EmpresaKey = %s" if empresa_key is not None else "COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE"
        params = (empresa_key,) if empresa_key is not None else ()
        
        cur.execute(f"""
            SELECT (COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0)) as SalarioTotal
            FROM Fact_Nomina n
            INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
            WHERE {empresa_filter}
            ORDER BY 1;
        """, params)
        
        data = [float(r[0]) for r in cur.fetchall()]
        
        fig = go.Figure(data=[go.Histogram(x=data, nbinsx=20, marker_color='#3fb950')])
        fig.update_layout(title='Distribución de Salarios Totales', xaxis_title='Salario Total', yaxis_title='Cantidad')
        
        html = fig.to_html(full_html=False, include_plotlyjs=False)
        cur.close()
        conn.close()
        return html, None
    except Exception:
        return "", traceback.format_exc()

# ======================================================
# 📊 GRÁFICA AUSENTISMO POR DEPARTAMENTO
# ======================================================
def grafica_ausentismo(empresa_key: int | None = None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        empresa_filter = "ei.EmpresaKey = %s" if empresa_key is not None else "COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE"
        params = (empresa_key,) if empresa_key is not None else ()
        
        cur.execute(f"""
            SELECT COALESCE(d.NombreDepartamento, 'SIN DEPTO'), AVG(COALESCE(a.TasaAusentismo, 0)), COUNT(DISTINCT a.EmpleadoKey)
            FROM Fact_Asistencia a
            INNER JOIN DimEmpresa ei ON a.EmpresaKey = ei.EmpresaKey
            LEFT JOIN DimEmpleado e ON a.EmpleadoKey = e.EmpleadoKey
            LEFT JOIN Fact_Nomina n ON n.EmpleadoKey = e.EmpleadoKey
            LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
            WHERE {empresa_filter}
            GROUP BY d.NombreDepartamento
            ORDER BY 2 DESC
            LIMIT 15;
        """, params)
        
        data = cur.fetchall()
        deptos = [str(r[0]) for r in data]
        ausentismo = [float(r[1] or 0) for r in data]
        
        fig = go.Figure(data=[go.Bar(x=deptos, y=ausentismo, marker_color='#f85149')])
        fig.update_layout(title='Tasa de Ausentismo por Departamento', xaxis_title='Departamento', yaxis_title='Tasa Ausentismo (%)')
        
        html = fig.to_html(full_html=False, include_plotlyjs=False)
        cur.close()
        conn.close()
        return html, None
    except Exception:
        return "", traceback.format_exc()

# ======================================================
# 📊 GRÁFICA DESEMPEÑO VS SALARIO
# ======================================================
def grafica_desempeno_vs_salario(empresa_key: int | None = None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        empresa_filter = "ei.EmpresaKey = %s" if empresa_key is not None else "COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE"
        params = (empresa_key,) if empresa_key is not None else ()
        
        cur.execute(f"""
            SELECT 
                COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0),
                COALESCE(ev.PuntajeDesempeno, 0),
                COALESCE(e.NombreCompleto, 'SIN NOMBRE')
            FROM Fact_Nomina n
            INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
            LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
            LEFT JOIN Fact_Evaluacion ev ON n.EmpleadoKey = ev.EmpleadoKey
            WHERE {empresa_filter}
            LIMIT 100;
        """, params)
        
        data = cur.fetchall()
        salarios = [float(r[0]) for r in data]
        desempenos = [float(r[1]) for r in data]
        nombres = [str(r[2]) for r in data]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=salarios, y=desempenos, mode='markers', marker=dict(size=8, color='#bc8cff'), text=nombres, hovertemplate='%{text}<br>Salario: $%{x:,.0f}<br>Desempeño: %{y:.1f}<extra></extra>'))
        fig.update_layout(title='Desempeño vs Salario', xaxis_title='Salario Total', yaxis_title='Puntaje Desempeño')
        
        html = fig.to_html(full_html=False, include_plotlyjs=False)
        cur.close()
        conn.close()
        return html, None
    except Exception:
        return "", traceback.format_exc()

# ======================================================
# 📊 GRÁFICA TOP PERFORMERS Y BOTTOM PERFORMERS
# ======================================================
def grafica_top_bottom(empresa_key: int | None = None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        empresa_filter = "ei.EmpresaKey = %s" if empresa_key is not None else "COALESCE(ei.EsEmpresaPropia, FALSE) = TRUE"
        params = (empresa_key,) if empresa_key is not None else ()
        
        cur.execute(f"""
            SELECT COALESCE(e.NombreCompleto, 'SIN NOMBRE'), COALESCE(ev.PuntajeDesempeno, 0)
            FROM Fact_Nomina n
            INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
            LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
            LEFT JOIN Fact_Evaluacion ev ON n.EmpleadoKey = ev.EmpleadoKey
            WHERE {empresa_filter}
            ORDER BY COALESCE(ev.PuntajeDesempeno, 0) DESC
            LIMIT 50;
        """, params)
        
        datos_top = cur.fetchall()
        top = datos_top[:10]
        
        cur.execute(f"""
            SELECT COALESCE(e.NombreCompleto, 'SIN NOMBRE'), COALESCE(ev.PuntajeDesempeno, 0)
            FROM Fact_Nomina n
            INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
            LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
            LEFT JOIN Fact_Evaluacion ev ON n.EmpleadoKey = ev.EmpleadoKey
            WHERE {empresa_filter} AND COALESCE(ev.PuntajeDesempeno, 0) > 0
            ORDER BY COALESCE(ev.PuntajeDesempeno, 0) ASC
            LIMIT 10;
        """, params)
        
        bottom = cur.fetchall()
        
        nombres_top = [str(r[0]) for r in top]
        desempenos_top = [float(r[1]) for r in top]
        nombres_bottom = [str(r[0]) for r in bottom]
        desempenos_bottom = [float(r[1]) for r in bottom]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Top Performers', x=nombres_top, y=desempenos_top, marker_color='#3fb950'))
        fig.add_trace(go.Bar(name='Bottom Performers', x=nombres_bottom, y=desempenos_bottom, marker_color='#f85149'))
        fig.update_layout(title='Top vs Bottom Performers', barmode='group')
        
        html = fig.to_html(full_html=False, include_plotlyjs=False)
        cur.close()
        conn.close()
        return html, None
    except Exception:
        return "", traceback.format_exc()

# ======================================================
# ⚖️ EQUIDAD — tabla
# ======================================================
def equidad(
  empresa_key: int | None = None,
  departamento: str | None = None,
  puesto: str | None = None,
  ciudad: str | None = None,
  tipo_contrato: str | None = None,
  genero: str | None = None,
  estado: str | None = None,
  antiguedad_min: int | None = None,
  antiguedad_max: int | None = None,
  salario_min: float | None = None,
  salario_max: float | None = None,
) -> List[Tuple]:
    conn = get_connection()
    cur = conn.cursor()
    where_clause, filter_params = build_filter_where(
      empresa_key,
      departamento,
      puesto,
      ciudad,
      tipo_contrato,
      genero,
      estado,
      antiguedad_min,
      antiguedad_max,
      salario_min,
      salario_max,
    )
    cur.execute(f"""
        SELECT 
            COALESCE(e.NombreCompleto, 'SIN NOMBRE') AS Empleado,
            COALESCE(p.NombrePuesto, 'SIN PUESTO') AS Puesto,
            COALESCE(n.SalarioBase, 0) AS SalarioBase,
            ROUND(AVG(COALESCE(n.SalarioBase, 0)) OVER (PARTITION BY n.PuestoKey), 2) AS Promedio,
            CASE
                WHEN AVG(COALESCE(n.SalarioBase, 0)) OVER (PARTITION BY n.PuestoKey) = 0 THEN 0
                ELSE ROUND(
                    (COALESCE(n.SalarioBase, 0) - AVG(COALESCE(n.SalarioBase, 0)) OVER (PARTITION BY n.PuestoKey))
                    / AVG(COALESCE(n.SalarioBase, 0)) OVER (PARTITION BY n.PuestoKey),
                    4
                )
            END AS IndiceEquidad
        FROM Fact_Nomina n
          INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
        LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
        LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey
      LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
      LEFT JOIN DimSucursal s ON n.SucursalKey = s.SucursalKey
      WHERE {where_clause}
        LIMIT 50;
    """, filter_params)
    data = cur.fetchall()
    cur.close()
    conn.close()

    resultado = []
    for r in data:
        empleado = r[0]
        puesto   = r[1]
        salario  = float(r[2] or 0)
        promedio = float(r[3] or 0)
        indice   = float(r[4] or 0)
        resultado.append((
            empleado, puesto,
            round(salario, 2), round(promedio, 2),
            round(indice, 4), round(abs(indice), 4)
        ))
    return resultado


# ======================================================
# 🧭 RESUMEN EJECUTIVO
# ======================================================
def resumen_ejecutivo(
  empresa_key: int | None = None,
  departamento: str | None = None,
  puesto: str | None = None,
  ciudad: str | None = None,
  tipo_contrato: str | None = None,
  genero: str | None = None,
  estado: str | None = None,
  antiguedad_min: int | None = None,
  antiguedad_max: int | None = None,
  salario_min: float | None = None,
  salario_max: float | None = None,
) -> Dict[str, float]:
    conn = get_connection()
    cur = conn.cursor()
    where_clause, params = build_filter_where(
      empresa_key,
      departamento,
      puesto,
      ciudad,
      tipo_contrato,
      genero,
      estado,
      antiguedad_min,
      antiguedad_max,
      salario_min,
      salario_max,
    )

    cur.execute(f"""
      WITH benchmark_externo_tiempo AS (
        SELECT
          b.TiempoKey,
          b.PuestoKey,
          AVG(COALESCE(b.SalarioMercadoMed, 0)) AS SalarioMercadoMedExterno
        FROM Ref_Benchmark_Salarial b
        INNER JOIN DimEmpresa eb ON b.EmpresaKey = eb.EmpresaKey
        WHERE COALESCE(eb.EsEmpresaPropia, FALSE) = FALSE
        GROUP BY b.TiempoKey, b.PuestoKey
      ),
      benchmark_externo_puesto AS (
        SELECT
          b.PuestoKey,
          AVG(COALESCE(b.SalarioMercadoMed, 0)) AS SalarioMercadoMedExterno
        FROM Ref_Benchmark_Salarial b
        INNER JOIN DimEmpresa eb ON b.EmpresaKey = eb.EmpresaKey
        WHERE COALESCE(eb.EsEmpresaPropia, FALSE) = FALSE
        GROUP BY b.PuestoKey
    conn = get_connection() 
        SELECT COALESCE(
            AVG(
                CASE 
            WHEN COALESCE(bet.SalarioMercadoMedExterno, bep.SalarioMercadoMedExterno, 0) = 0 THEN NULL
                    ELSE (COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0))
               / COALESCE(bet.SalarioMercadoMedExterno, bep.SalarioMercadoMedExterno, 0)
                END
            ), 0)
        FROM Fact_Nomina n
      INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
        LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
        LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey
        LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
        LEFT JOIN DimSucursal s ON n.SucursalKey = s.SucursalKey
      LEFT JOIN benchmark_externo_tiempo bet
        ON n.PuestoKey = bet.PuestoKey
         AND n.TiempoKey = bet.TiempoKey
      LEFT JOIN benchmark_externo_puesto bep
        ON n.PuestoKey = bep.PuestoKey
        WHERE {where_clause};
    """, params)
    comp = cur.fetchone()

    cur.execute(f"""
      SELECT COALESCE(SUM(n.Beneficios), 0)
      FROM Fact_Nomina n
      INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
      LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
      LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey
      LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
      LEFT JOIN DimSucursal s ON n.SucursalKey = s.SucursalKey
      WHERE {where_clause};
    """, params)
    ben = cur.fetchone()

    cur.execute(f"""
      SELECT COALESCE(SUM(n.Bono), 0)
      FROM Fact_Nomina n
      INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
      LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
      LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey
      LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
      LEFT JOIN DimSucursal s ON n.SucursalKey = s.SucursalKey
      WHERE {where_clause};
    """, params)
    bon = cur.fetchone()

    cur.execute(f"""
      SELECT COUNT(*)
      FROM Fact_Nomina n
      INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
      LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
      LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey
      LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
      LEFT JOIN DimSucursal s ON n.SucursalKey = s.SucursalKey
      WHERE {where_clause}
        AND n.FlagActivo = TRUE;
    """, params)
    headcount = cur.fetchone()

    cur.execute(f"""
        SELECT COALESCE(AVG(
        COALESCE(n.SalarioBase,0) + COALESCE(n.Bono,0) + COALESCE(n.Beneficios,0)
      ), 0)
      FROM Fact_Nomina n
      INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
      LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
      LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey
      LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
      LEFT JOIN DimSucursal s ON n.SucursalKey = s.SucursalKey
      WHERE {where_clause}
        AND n.FlagActivo = TRUE;
    """, params)
    salario_prom = cur.fetchone()

    cur.close()
    conn.close()

    return {
        "competitividad":   round(float(comp[0]        if comp        else 0), 4),
        "beneficios":       round(float(ben[0]         if ben         else 0), 2),
        "bonos":            round(float(bon[0]         if bon         else 0), 2),
        "headcount":        int(headcount[0]            if headcount   else 0),
        "salario_promedio": round(float(salario_prom[0] if salario_prom else 0), 2),
    }


def detalle_empleados(
  empresa_key: int | None = None,
  departamento: str | None = None,
  puesto: str | None = None,
  ciudad: str | None = None,
  tipo_contrato: str | None = None,
  genero: str | None = None,
  estado: str | None = None,
  antiguedad_min: int | None = None,
  antiguedad_max: int | None = None,
  salario_min: float | None = None,
  salario_max: float | None = None,
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()

    where_clause, params_nomina = build_filter_where(
      empresa_key,
      departamento,
      puesto,
      ciudad,
      tipo_contrato,
      genero,
      estado,
      antiguedad_min,
      antiguedad_max,
      salario_min,
      salario_max,
    )

    if empresa_key is not None:
      filtro_eval = "ev.EmpresaKey = %s"
      filtro_cap = "c.EmpresaKey = %s"
      filtro_asis = "a.EmpresaKey = %s"
      params_sec = (empresa_key, empresa_key, empresa_key)
    else:
      filtro_eval = "ev.EmpresaKey IN (SELECT EmpresaKey FROM DimEmpresa WHERE COALESCE(EsEmpresaPropia, FALSE) = TRUE)"
      filtro_cap = "c.EmpresaKey IN (SELECT EmpresaKey FROM DimEmpresa WHERE COALESCE(EsEmpresaPropia, FALSE) = TRUE)"
      filtro_asis = "a.EmpresaKey IN (SELECT EmpresaKey FROM DimEmpresa WHERE COALESCE(EsEmpresaPropia, FALSE) = TRUE)"
      params_sec = ()

    cur.execute(f"""
      WITH nomagg AS (
        SELECT
          n.EmpleadoKey,
          MAX(n.EmpresaKey) AS EmpresaKey,
          MAX(n.PuestoKey) AS PuestoKey,
          MAX(n.DepartamentoKey) AS DepartamentoKey,
          MAX(n.SucursalKey) AS SucursalKey,
          MAX(n.TipoContrato) AS TipoContrato,
          AVG(COALESCE(n.SalarioBase, 0)) AS SalarioBasePromedio,
          SUM(COALESCE(n.Bono, 0)) AS BonoAcumulado,
          SUM(COALESCE(n.Beneficios, 0)) AS BeneficiosAcumulados,
          SUM(COALESCE(n.CostoTotalNomina, 0)) AS CostoTotalNomina,
          MAX(COALESCE(n.AntiguedadMeses, 0)) AS AntiguedadMeses,
          MAX(COALESCE(n.EdadActual, 0)) AS EdadActual,
          BOOL_OR(COALESCE(n.FlagActivo, FALSE)) AS FlagActivo,
          BOOL_OR(COALESCE(n.FlagBaja, FALSE)) AS FlagBaja,
          BOOL_OR(COALESCE(n.FlagNuevoIngreso, FALSE)) AS FlagNuevoIngreso,
          BOOL_OR(COALESCE(n.FlagJubilacionProxima, FALSE)) AS FlagJubilacionProxima
        FROM Fact_Nomina n
        INNER JOIN DimEmpresa ei ON n.EmpresaKey = ei.EmpresaKey
        LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
        LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey
        LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
        LEFT JOIN DimSucursal s ON n.SucursalKey = s.SucursalKey
        WHERE {where_clause}
        GROUP BY n.EmpleadoKey
      ),
      evalagg AS (
        SELECT
          ev.EmpleadoKey,
          AVG(COALESCE(ev.PuntajeDesempeno, 0)) AS PuntajeDesempenoProm,
          AVG(COALESCE(ev.CumplimientoObjetivos, 0)) AS CumplimientoObjetivosProm,
          BOOL_OR(COALESCE(ev.FlagAltoPotencial, FALSE)) AS FlagAltoPotencial
        FROM Fact_Evaluacion ev
        WHERE {filtro_eval}
        GROUP BY ev.EmpleadoKey
      ),
      capagg AS (
        SELECT
          c.EmpleadoKey,
          SUM(COALESCE(c.HorasCapacitacion, 0)) AS HorasCapacitacion,
          SUM(COALESCE(c.CostoCapacitacion, 0)) AS CostoCapacitacion,
          AVG(COALESCE(c.MejoraHabilidad, 0)) AS MejoraHabilidadProm,
          SUM(CASE WHEN COALESCE(c.FlagFinalizado, FALSE) THEN 1 ELSE 0 END) AS CursosFinalizados
        FROM Fact_Capacitacion c
        WHERE {filtro_cap}
        GROUP BY c.EmpleadoKey
      ),
      asisagg AS (
        SELECT
          a.EmpleadoKey,
          SUM(COALESCE(a.DiasFalta, 0)) AS DiasFalta,
          SUM(COALESCE(a.TotalHorasExtra, 0)) AS HorasExtra,
          AVG(COALESCE(a.TasaAusentismo, 0)) AS TasaAusentismoProm,
          AVG(COALESCE(a.TasaPuntualidad, 0)) AS TasaPuntualidadProm
        FROM Fact_Asistencia a
        WHERE {filtro_asis}
        GROUP BY a.EmpleadoKey
      )
      SELECT
        COALESCE(emp.NombreEmpresa, 'SIN EMPRESA') AS Empresa,
        COALESCE(e.IdEmpleadoNegocio, 'N/A') AS IdEmpleado,
        COALESCE(e.NombreCompleto, 'SIN NOMBRE') AS Empleado,
        COALESCE(e.Genero, 'N/A') AS Genero,
        COALESCE(e.NivelEducativo, 'N/A') AS NivelEducativo,
        COALESCE(e.Nacionalidad, 'N/A') AS Nacionalidad,
        COALESCE(e.CorreoElectronico, 'N/A') AS Correo,
        COALESCE(e.Telefono, 'N/A') AS Telefono,
        e.FechaIngreso,
        COALESCE(e.EstadoActual, 'N/A') AS EstadoEmpleado,
        COALESCE(p.NombrePuesto, 'SIN PUESTO') AS Puesto,
        COALESCE(d.NombreDepartamento, 'SIN DEPARTAMENTO') AS Departamento,
        COALESCE(s.NombreSucursal, 'SIN SUCURSAL') AS Sucursal,
        COALESCE(s.Ciudad, 'N/A') AS Ciudad,
        COALESCE(n.TipoContrato, 'N/A') AS TipoContrato,
        COALESCE(n.SalarioBasePromedio, 0) AS SalarioBasePromedio,
        COALESCE(n.BonoAcumulado, 0) AS BonoAcumulado,
        COALESCE(n.BeneficiosAcumulados, 0) AS BeneficiosAcumulados,
        COALESCE(n.CostoTotalNomina, 0) AS CostoTotalNomina,
        COALESCE(n.AntiguedadMeses, 0) AS AntiguedadMeses,
        COALESCE(n.EdadActual, 0) AS EdadActual,
        COALESCE(n.FlagActivo, FALSE) AS FlagActivo,
        COALESCE(n.FlagBaja, FALSE) AS FlagBaja,
        COALESCE(n.FlagNuevoIngreso, FALSE) AS FlagNuevoIngreso,
        COALESCE(n.FlagJubilacionProxima, FALSE) AS FlagJubilacionProxima,
        COALESCE(ev.PuntajeDesempenoProm, 0) AS PuntajeDesempenoProm,
        COALESCE(ev.CumplimientoObjetivosProm, 0) AS CumplimientoObjetivosProm,
        COALESCE(ev.FlagAltoPotencial, FALSE) AS FlagAltoPotencial,
        COALESCE(ca.HorasCapacitacion, 0) AS HorasCapacitacion,
        COALESCE(ca.CostoCapacitacion, 0) AS CostoCapacitacion,
        COALESCE(ca.MejoraHabilidadProm, 0) AS MejoraHabilidadProm,
        COALESCE(ca.CursosFinalizados, 0) AS CursosFinalizados,
        COALESCE(aa.DiasFalta, 0) AS DiasFalta,
        COALESCE(aa.HorasExtra, 0) AS HorasExtra,
        COALESCE(aa.TasaAusentismoProm, 0) AS TasaAusentismoProm,
        COALESCE(aa.TasaPuntualidadProm, 0) AS TasaPuntualidadProm
      FROM nomagg n
      LEFT JOIN DimEmpleado e ON n.EmpleadoKey = e.EmpleadoKey
      LEFT JOIN DimPuesto p ON n.PuestoKey = p.PuestoKey
      LEFT JOIN DimDepartamento d ON n.DepartamentoKey = d.DepartamentoKey
      LEFT JOIN DimSucursal s ON n.SucursalKey = s.SucursalKey
      LEFT JOIN DimEmpresa emp ON n.EmpresaKey = emp.EmpresaKey
      LEFT JOIN evalagg ev ON n.EmpleadoKey = ev.EmpleadoKey
      LEFT JOIN capagg ca ON n.EmpleadoKey = ca.EmpleadoKey
      LEFT JOIN asisagg aa ON n.EmpleadoKey = aa.EmpleadoKey
      ORDER BY COALESCE(n.CostoTotalNomina, 0) DESC
      LIMIT 200;
    """, params_nomina + params_sec)

    rows = cur.fetchall()
    columns = [d[0] for d in (cur.description or [])]
    cur.close()
    conn.close()

    detalle = []
    for row in rows:
        item = dict(zip(columns, row))
        item["FechaIngreso"] = item["fechaingreso"].strftime("%Y-%m-%d") if item.get("fechaingreso") else "N/A"
        item["Empresa"] = item.get("empresa", "SIN EMPRESA")
        item["IdEmpleado"] = item.get("idempleado", "N/A")
        item["Empleado"] = item.get("empleado", "SIN NOMBRE")
        item["Genero"] = item.get("genero", "N/A")
        item["NivelEducativo"] = item.get("niveleducativo", "N/A")
        item["Nacionalidad"] = item.get("nacionalidad", "N/A")
        item["Correo"] = item.get("correo", "N/A")
        item["Telefono"] = item.get("telefono", "N/A")
        item["EstadoEmpleado"] = item.get("estadoempleado", "N/A")
        item["Puesto"] = item.get("puesto", "SIN PUESTO")
        item["Departamento"] = item.get("departamento", "SIN DEPARTAMENTO")
        item["Sucursal"] = item.get("sucursal", "SIN SUCURSAL")
        item["Ciudad"] = item.get("ciudad", "N/A")
        item["TipoContrato"] = item.get("tipocontrato", "N/A")
        detalle.append(item)

    return detalle


# ======================================================
# 🌐 HTML — con manejo de errores visible
# ======================================================
HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard RRHH</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'IBM Plex Sans', sans-serif; background: #0d1117; color: #e6edf3; min-height: 100vh; }

  header {
    background: linear-gradient(135deg, #161b22 0%, #1c2333 100%);
    border-bottom: 1px solid #30363d;
    padding: 24px 40px;
    display: flex;
    align-items: center;
    gap: 20px;
  }
  header .logo { font-size: 2rem; }
  header h1 { font-size: 1.4rem; font-weight: 700; color: #f0f6fc; letter-spacing: -0.3px; }
  header p  { font-size: 0.82rem; color: #8b949e; margin-top: 3px; font-family: 'IBM Plex Mono', monospace; }

  main { max-width: 1280px; margin: 0 auto; padding: 32px 24px; }

  /* ─── GLOBAL ERRORS ─── */
  .error-banner {
    background: #2d1b1b;
    border: 1px solid #6e2121;
    border-left: 4px solid #f85149;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 24px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem;
  }
  .error-banner .error-title { color: #f85149; font-weight: 600; margin-bottom: 8px; font-size: 0.88rem; }
  .error-banner .error-item { color: #ffa198; margin: 4px 0; padding-left: 12px; border-left: 2px solid #6e2121; }
  .error-banner pre { color: #ffa198; white-space: pre-wrap; word-break: break-all; margin-top: 6px; font-size: 0.76rem; line-height: 1.5; }

  /* ─── SECTION ERROR ─── */
  .section-error {
    background: #161b22;
    border: 1px solid #6e2121;
    border-radius: 8px;
    padding: 20px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem;
  }
  .section-error .err-label { color: #f85149; font-weight: 600; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
  .section-error pre { color: #ffa198; background: #0d1117; padding: 12px; border-radius: 6px; white-space: pre-wrap; word-break: break-all; font-size: 0.75rem; line-height: 1.6; max-height: 300px; overflow-y: auto; }

  /* ─── KPI GRID ─── */
  .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 28px; }
  .kpi-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
    transition: border-color .2s;
  }
  .kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent, #4f86c6);
  }
  .kpi-card:hover { border-color: var(--accent, #4f86c6); }
  .kpi-card.blue   { --accent: #4f86c6; }
  .kpi-card.green  { --accent: #3fb950; }
  .kpi-card.orange { --accent: #e07b54; }
  .kpi-card.purple { --accent: #bc8cff; }
  .kpi-card.teal   { --accent: #39d353; }

  .kpi-label { font-size: 0.72rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
  .kpi-value { font-size: 1.9rem; font-weight: 700; color: #f0f6fc; margin-top: 8px; font-family: 'IBM Plex Mono', monospace; letter-spacing: -1px; }
  .kpi-sub   { font-size: 0.72rem; color: #8b949e; margin-top: 4px; }

  /* ─── SECTION ─── */
  .section {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 24px;
    margin-bottom: 22px;
  }
  .section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 18px;
    padding-bottom: 14px;
    border-bottom: 1px solid #21262d;
  }
  .section-header h2 { font-size: 1rem; font-weight: 600; color: #f0f6fc; }
  .section-header .icon { font-size: 1.2rem; }

  /* ─── TABLE ─── */
  .table-wrap { overflow-x: auto; border-radius: 6px; border: 1px solid #21262d; }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  thead th {
    background: #0d1117;
    color: #8b949e;
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: .5px;
    border-bottom: 1px solid #21262d;
    white-space: nowrap;
  }
  tbody td { padding: 10px 14px; border-bottom: 1px solid #21262d; color: #c9d1d9; }
  tbody tr:last-child td { border-bottom: none; }
  tbody tr:hover td { background: #1c2333; }

  .mono { font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; }

  .badge { display: inline-flex; align-items: center; padding: 2px 9px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; font-family: 'IBM Plex Mono', monospace; }
  .badge-green  { background: rgba(63,185,80,.15);  color: #3fb950; border: 1px solid rgba(63,185,80,.3); }
  .badge-red    { background: rgba(248,81,73,.15);  color: #f85149; border: 1px solid rgba(248,81,73,.3); }
  .badge-yellow { background: rgba(210,153,34,.15); color: #e3b341; border: 1px solid rgba(210,153,34,.3); }

  .empty-state {
    text-align: center; padding: 40px;
    color: #8b949e; font-size: 0.88rem;
  }
  .empty-state .empty-icon { font-size: 2rem; margin-bottom: 10px; }

  /* plotly override */
  .plotly-graph { border-radius: 6px; overflow: hidden; }
  /* ─── GLOBOS / TOOLTIP CLICK ─── */
  .emp-name { background: transparent; border: none; color: #58a6ff; font: inherit; padding: 0; margin: 0; cursor: pointer; text-align: left; text-decoration: underline; }
  .emp-balloon {
    position: absolute; z-index: 9999; display: none;
    background: #0b1220; color: #e6edf3; border: 1px solid #263244; padding: 12px; border-radius: 10px; min-width: 220px; box-shadow: 0 8px 30px rgba(2,6,23,.6);
    font-size: 0.86rem; max-width: 420px; word-break: break-word;
  }
  .emp-balloon .balloon-header { font-weight: 700; margin-bottom: 8px; color: #9ad1ff; }
  .emp-balloon .balloon-body div { margin: 4px 0; color: #cfe8ff; }
</style>
</head>
<body>

<header>
  <div class="logo">📊</div>
  <div>
    <h1>Dashboard de Recursos Humanos</h1>
    <p>módulo / compensación &amp; beneficios — AVANZADO CON FILTROS</p>
  </div>
  <div style="margin-left:auto; display:flex; align-items:center; gap:12px;">
    <form method="get" style="display:flex; gap:8px; align-items:center;">
      <label for="empresa" style="color:#8b949e; font-size:0.85rem;">Empresa:</label>
      <select name="empresa" id="empresa" onchange="this.form.submit()" style="padding:6px;border-radius:6px;background:#0d1117;color:#f0f6fc;border:1px solid #21262d">
        <option value="">Propia (por defecto)</option>
        {% for e in empresas %}
          <option value="{{ e[0] }}" {% if empresa_selected and empresa_selected==e[0] %}selected{% endif %}>{{ e[2] }} {% if e[3] %}(Propia){% else %}(Externa){% endif %}</option>
        {% endfor %}
      </select>
      <button type="button" onclick="document.getElementById('filtros').style.display = document.getElementById('filtros').style.display === 'none' ? 'block' : 'none';" style="padding:6px 10px;background:#4f86c6;color:white;border:none;border-radius:6px;cursor:pointer;">⚙️ Más Filtros</button>
    </form>
  </div>
</header>

<div id="filtros" style="background:#1c2333;border-bottom:1px solid #30363d;padding:16px;display:none;">
  <form method="get" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;">
    <input type="hidden" name="empresa" value="{{ empresa_selected or '' }}">
    
    <div>
      <label style="color:#8b949e;font-size:0.75rem;">Departamento</label>
      <input list="departamentos-list" name="departamento" value="{{ filtro_departamento }}" placeholder="Escribe o elige un valor" style="width:100%;padding:6px;border-radius:6px;background:#0d1117;color:#f0f6fc;border:1px solid #21262d;">
      <datalist id="departamentos-list">{% for d in filter_options.departamentos %}<option value="{{ d }}">{% endfor %}</datalist>
    </div>
    
    <div>
      <label style="color:#8b949e;font-size:0.75rem;">Puesto</label>
      <input list="puestos-list" name="puesto" value="{{ filtro_puesto }}" placeholder="Escribe o elige un valor" style="width:100%;padding:6px;border-radius:6px;background:#0d1117;color:#f0f6fc;border:1px solid #21262d;">
      <datalist id="puestos-list">{% for p in filter_options.puestos %}<option value="{{ p }}">{% endfor %}</datalist>
    </div>
    
    <div>
      <label style="color:#8b949e;font-size:0.75rem;">Ciudad</label>
      <input list="ciudades-list" name="ciudad" value="{{ filtro_ciudad }}" placeholder="Escribe o elige un valor" style="width:100%;padding:6px;border-radius:6px;background:#0d1117;color:#f0f6fc;border:1px solid #21262d;">
      <datalist id="ciudades-list">{% for c in filter_options.ciudades %}<option value="{{ c }}">{% endfor %}</datalist>
    </div>
    
    <div>
      <label style="color:#8b949e;font-size:0.75rem;">Tipo Contrato</label>
      <input list="tipos-contrato-list" name="tipo_contrato" value="{{ filtro_tipo_contrato }}" placeholder="Escribe o elige un valor" style="width:100%;padding:6px;border-radius:6px;background:#0d1117;color:#f0f6fc;border:1px solid #21262d;">
      <datalist id="tipos-contrato-list">{% for t in filter_options.tipos_contrato %}<option value="{{ t }}">{% endfor %}</datalist>
    </div>
    
    <div>
      <label style="color:#8b949e;font-size:0.75rem;">Género</label>
      <input list="generos-list" name="genero" value="{{ filtro_genero }}" placeholder="Escribe o elige un valor" style="width:100%;padding:6px;border-radius:6px;background:#0d1117;color:#f0f6fc;border:1px solid #21262d;">
      <datalist id="generos-list">{% for g in filter_options.generos %}<option value="{{ g }}">{% endfor %}</datalist>
    </div>
    
    <div>
      <label style="color:#8b949e;font-size:0.75rem;">Estado</label>
      <input list="estados-list" name="estado" value="{{ filtro_estado }}" placeholder="Escribe o elige un valor" style="width:100%;padding:6px;border-radius:6px;background:#0d1117;color:#f0f6fc;border:1px solid #21262d;">
      <datalist id="estados-list">{% for e in filter_options.estados %}<option value="{{ e }}">{% endfor %}</datalist>
    </div>
    
    <div><label style="color:#8b949e;font-size:0.75rem;">Antigüedad Min (meses)</label><input type="number" name="antigüedad_min" value="{{ filtro_antigüedad_min }}" style="width:100%;padding:6px;border-radius:6px;background:#0d1117;color:#f0f6fc;border:1px solid #21262d;"></div>
    
    <div><label style="color:#8b949e;font-size:0.75rem;">Antigüedad Max (meses)</label><input type="number" name="antigüedad_max" value="{{ filtro_antigüedad_max }}" style="width:100%;padding:6px;border-radius:6px;background:#0d1117;color:#f0f6fc;border:1px solid #21262d;"></div>
    
    <div><label style="color:#8b949e;font-size:0.75rem;">Salario Mínimo ($)</label><input type="number" step="0.01" name="salario_min" value="{{ filtro_salario_min }}" style="width:100%;padding:6px;border-radius:6px;background:#0d1117;color:#f0f6fc;border:1px solid #21262d;"></div>
    
    <div><label style="color:#8b949e;font-size:0.75rem;">Salario Máximo ($)</label><input type="number" step="0.01" name="salario_max" value="{{ filtro_salario_max }}" style="width:100%;padding:6px;border-radius:6px;background:#0d1117;color:#f0f6fc;border:1px solid #21262d;"></div>
    
    <div style="display:flex;gap:8px;"><button type="submit" style="padding:6px 12px;background:#3fb950;color:white;border:none;border-radius:6px;cursor:pointer;font-weight:600;">Aplicar</button><button type="reset" style="padding:6px 12px;background:#6e2121;color:white;border:none;border-radius:6px;cursor:pointer;">Limpiar</button></div>
  </form>
</div>

<main>

  {% if global_errors %}
  <div class="error-banner">
    <div class="error-title">⚠️ Errores detectados en {{ global_errors|length }} sección(es)</div>
    {% for e in global_errors %}
    <div class="error-item">
      <strong>{{ e.seccion }}</strong>: {{ e.mensaje }}<br>
      <pre>{{ e.traceback }}</pre>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- ── KPIs ── -->
  <div class="kpi-grid">
    <div class="kpi-card blue">
      <div class="kpi-label">Índice Competitividad</div>
      <div class="kpi-value">{{ "%.2f"|format(resumen.competitividad) }}</div>
      <div class="kpi-sub">vs. mercado (1.0 = paridad)</div>
    </div>
    <div class="kpi-card green">
      <div class="kpi-label">Total Beneficios</div>
      <div class="kpi-value">${{ "{:,.0f}".format(resumen.beneficios) }}</div>
    </div>
    <div class="kpi-card orange">
      <div class="kpi-label">Total Bonos</div>
      <div class="kpi-value">${{ "{:,.0f}".format(resumen.bonos) }}</div>
    </div>
    <div class="kpi-card purple">
      <div class="kpi-label">Headcount Activo</div>
      <div class="kpi-value">{{ resumen.headcount }}</div>
    </div>
    <div class="kpi-card teal">
      <div class="kpi-label">Salario Promedio</div>
      <div class="kpi-value">${{ "{:,.0f}".format(resumen.salario_promedio) }}</div>
    </div>
  </div>

  <!-- ── Gráfica Competitividad ── -->
  <div class="section">
    <div class="section-header">
      <span class="icon"><i class="fas fa-chart-line"></i></span>
      <h2>Competitividad Salarial</h2>
    </div>
    {% if grafica_comp_error %}
      <div class="section-error">
        <div class="err-label"><i class="fas fa-exclamation-circle"></i> Error en gráfica de competitividad</div>
        <pre>{{ grafica_comp_error }}</pre>
      </div>
    {% else %}
      <div class="plotly-graph">{{ grafica_comp | safe }}</div>
    {% endif %}
  </div>

  <!-- ── Gráfica Beneficios ── -->
  <div class="section">
    <div class="section-header">
      <span class="icon"><i class="fas fa-gift"></i></span>
      <h2>Beneficios por Departamento</h2>
    </div>
    {% if grafica_benef_error %}
      <div class="section-error">
        <div class="err-label"><i class="fas fa-exclamation-circle"></i> Error en gráfica de beneficios</div>
        <pre>{{ grafica_benef_error }}</pre>
      </div>
    {% else %}
      <div class="plotly-graph">{{ grafica_benef | safe }}</div>
    {% endif %}
  </div>

  <!-- ── Gráfica Bonos ── -->
  <div class="section">
    <div class="section-header">
      <span class="icon"><i class="fas fa-trophy"></i></span>
      <h2>Análisis de Bonos — Top 20</h2>
    </div>
    {% if grafica_bonos_error %}
      <div class="section-error">
        <div class="err-label"><i class="fas fa-exclamation-circle"></i> Error en gráfica de bonos</div>
        <pre>{{ grafica_bonos_error }}</pre>
      </div>
    {% else %}
      <div class="plotly-graph">{{ grafica_bonos | safe }}</div>
    {% endif %}
  </div>

  <!-- ── Gráfica Equidad ── -->
  <div class="section">
    <div class="section-header">
      <span class="icon"><i class="fas fa-balance-scale"></i></span>
      <h2>Equidad Salarial por Puesto</h2>
    </div>
    {% if grafica_equidad_error %}
      <div class="section-error">
        <div class="err-label"><i class="fas fa-exclamation-circle"></i> Error en gráfica de equidad</div>
        <pre>{{ grafica_equidad_error }}</pre>
      </div>
    {% else %}
      <div class="plotly-graph">{{ grafica_equidad | safe }}</div>
    {% endif %}
  </div>

  <!-- ── Tabla Equidad ── -->
  <div class="section">
    <div class="section-header">
      <span class="icon"><i class="fas fa-table"></i></span>
      <h2>Detalle Equidad Salarial</h2>
    </div>
    {% if eq_error %}
      <div class="section-error">
        <div class="err-label"><i class="fas fa-exclamation-circle"></i> Error al cargar tabla de equidad</div>
        <pre>{{ eq_error }}</pre>
      </div>
    {% elif eq %}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Empleado</th>
            <th>Puesto</th>
            <th>Salario Base</th>
            <th>Promedio Puesto</th>
            <th>Índice Equidad</th>
            <th>Desviación Abs.</th>
          </tr>
        </thead>
        <tbody>
        {% for r in eq %}
          <tr>
            <td class="mono">
              <button class="emp-name" data-details='{{ {"Empleado": r[0], "Puesto": r[1], "SalarioBase": r[2], "Promedio": r[3], "IndiceEquidad": r[4], "DesviacionAbs": r[5]} | tojson | safe }}'>
                {{ r[0] }}
              </button>
            </td>
            <td>{{ r[1] }}</td>
            <td class="mono">${{ "{:,.2f}".format(r[2]) }}</td>
            <td class="mono">${{ "{:,.2f}".format(r[3]) }}</td>
            <td>
              {% if r[4] > 0.05 %}
                <span class="badge badge-green">+{{ "%.2f"|format(r[4]) }}</span>
              {% elif r[4] < -0.05 %}
                <span class="badge badge-red">{{ "%.2f"|format(r[4]) }}</span>
              {% else %}
                <span class="badge badge-yellow">{{ "%.2f"|format(r[4]) }}</span>
              {% endif %}
            </td>
            <td class="mono">{{ "%.4f"|format(r[5]) }}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <div class="empty-state">
      <div class="empty-icon">📭</div>
      <p>Sin datos de equidad disponibles.</p>
    </div>
    {% endif %}
  </div>

  <!-- ── Detalle Integral de Empleados ── -->
  <div class="section">
    <div class="section-header">
      <span class="icon"><i class="fas fa-id-card"></i></span>
      <h2>Detalle Integral de Empleados (Top 200 por Costo Nómina)</h2>
    </div>
    {% if emp_detalle_error %}
      <div class="section-error">
        <div class="err-label"><i class="fas fa-exclamation-circle"></i> Error al cargar detalle de empleados</div>
        <pre>{{ emp_detalle_error }}</pre>
      </div>
    {% elif emp_detalle %}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Empresa</th>
            <th>ID</th>
            <th>Empleado</th>
            <th>Estado</th>
            <th>Puesto</th>
            <th>Departamento</th>
            <th>Sucursal</th>
            <th>Ciudad</th>
            <th>Contrato</th>
            <th>Ingreso</th>
            <th>Género</th>
            <th>Nivel Ed.</th>
            <th>Nacionalidad</th>
            <th>Correo</th>
            <th>Teléfono</th>
            <th>Edad</th>
            <th>Antigüedad (meses)</th>
            <th>Salario Base Prom.</th>
            <th>Bono Acum.</th>
            <th>Beneficios Acum.</th>
            <th>Costo Nómina</th>
            <th>Puntaje Desempeño</th>
            <th>Cumpl. Objetivos</th>
            <th>Alto Potencial</th>
            <th>Horas Capac.</th>
            <th>Costo Capac.</th>
            <th>Mejora Hab.</th>
            <th>Cursos Finalizados</th>
            <th>Días Falta</th>
            <th>Horas Extra</th>
            <th>Tasa Ausentismo</th>
            <th>Tasa Puntualidad</th>
          </tr>
        </thead>
        <tbody>
        {% for r in emp_detalle %}
          <tr>
            <td>{{ r.Empresa }}</td>
            <td class="mono">{{ r.IdEmpleado }}</td>
            <td class="mono">
              <button class="emp-name" data-details='{{ r | tojson | safe }}'>{{ r.Empleado }}</button>
            </td>
            <td>{{ r.EstadoEmpleado }}</td>
            <td>{{ r.Puesto }}</td>
            <td>{{ r.Departamento }}</td>
            <td>{{ r.Sucursal }}</td>
            <td>{{ r.Ciudad }}</td>
            <td>{{ r.TipoContrato }}</td>
            <td class="mono">{{ r.FechaIngreso }}</td>
            <td>{{ r.Genero }}</td>
            <td>{{ r.NivelEducativo }}</td>
            <td>{{ r.Nacionalidad }}</td>
            <td class="mono">{{ r.Correo }}</td>
            <td class="mono">{{ r.Telefono }}</td>
            <td class="mono">{{ r.edadactual|int }}</td>
            <td class="mono">{{ r.antiguedadmeses|int }}</td>
            <td class="mono">${{ "{:,.2f}".format(r.salariobasepromedio|float) }}</td>
            <td class="mono">${{ "{:,.2f}".format(r.bonoacumulado|float) }}</td>
            <td class="mono">${{ "{:,.2f}".format(r.beneficiosacumulados|float) }}</td>
            <td class="mono">${{ "{:,.2f}".format(r.costototalnomina|float) }}</td>
            <td class="mono">{{ "%.2f"|format(r.puntajedesempenoprom|float) }}</td>
            <td class="mono">{{ "%.2f"|format(r.cumplimientoobjetivosprom|float) }}</td>
            <td>
              {% if r.flagaltopotencial %}
                <span class="badge badge-green">Sí</span>
              {% else %}
                <span class="badge badge-yellow">No</span>
              {% endif %}
            </td>
            <td class="mono">{{ "%.1f"|format(r.horascapacitacion|float) }}</td>
            <td class="mono">${{ "{:,.2f}".format(r.costocapacitacion|float) }}</td>
            <td class="mono">{{ "%.2f"|format(r.mejorahabilidadprom|float) }}</td>
            <td class="mono">{{ r.cursosfinalizados|int }}</td>
            <td class="mono">{{ r.diasfalta|int }}</td>
            <td class="mono">{{ "%.1f"|format(r.horasextra|float) }}</td>
            <td class="mono">{{ "%.2f"|format(r.tasaausentismoprom|float) }}</td>
            <td class="mono">{{ "%.2f"|format(r.tasapuntualidadprom|float) }}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <div class="empty-state">
      <div class="empty-icon">📭</div>
      <p>Sin detalle integral de empleados para esta selección.</p>
    </div>
    {% endif %}
  </div>

  <!-- ── Gráficas Avanzadas ── -->
  
  <!-- Distribución por Género -->
  <div class="section">
    <div class="section-header">
      <span class="icon"><i class="fas fa-users"></i></span>
      <h2>Distribución por Género</h2>
    </div>
    {% if grafica_genero_error %}
      <div class="section-error">
        <div class="err-label"><i class="fas fa-exclamation-circle"></i> Error al cargar gráfica</div>
        <pre>{{ grafica_genero_error }}</pre>
      </div>
    {% else %}
      <div class="plotly-graph">{{ grafica_genero | safe }}</div>
    {% endif %}
  </div>

  <!-- Distribución por Tipo de Contrato -->
  <div class="section">
    <div class="section-header">
      <span class="icon"><i class="fas fa-file-contract"></i></span>
      <h2>Distribución por Tipo de Contrato</h2>
    </div>
    {% if grafica_tipo_contrato_error %}
      <div class="section-error">
        <div class="err-label"><i class="fas fa-exclamation-circle"></i> Error al cargar gráfica</div>
        <pre>{{ grafica_tipo_contrato_error }}</pre>
      </div>
    {% else %}
      <div class="plotly-graph">{{ grafica_tipo_contrato | safe }}</div>
    {% endif %}
  </div>

  <!-- Distribución de Salarios -->
  <div class="section">
    <div class="section-header">
      <span class="icon"><i class="fas fa-money-bill"></i></span>
      <h2>Distribución de Salarios Totales</h2>
    </div>
    {% if grafica_distribucion_salarios_error %}
      <div class="section-error">
        <div class="err-label"><i class="fas fa-exclamation-circle"></i> Error al cargar gráfica</div>
        <pre>{{ grafica_distribucion_salarios_error }}</pre>
      </div>
    {% else %}
      <div class="plotly-graph">{{ grafica_distribucion_salarios | safe }}</div>
    {% endif %}
  </div>

  <!-- Ausentismo por Departamento -->
  <div class="section">
    <div class="section-header">
      <span class="icon"><i class="fas fa-clock"></i></span>
      <h2>Tasa de Ausentismo por Departamento</h2>
    </div>
    {% if grafica_ausentismo_error %}
      <div class="section-error">
        <div class="err-label"><i class="fas fa-exclamation-circle"></i> Error al cargar gráfica</div>
        <pre>{{ grafica_ausentismo_error }}</pre>
      </div>
    {% else %}
      <div class="plotly-graph">{{ grafica_ausentismo | safe }}</div>
    {% endif %}
  </div>

  <!-- Desempeño vs Salario -->
  <div class="section">
    <div class="section-header">
      <span class="icon"><i class="fas fa-chart-line"></i></span>
      <h2>Desempeño vs Salario (Scatter)</h2>
    </div>
    {% if grafica_desempeno_vs_salario_error %}
      <div class="section-error">
        <div class="err-label"><i class="fas fa-exclamation-circle"></i> Error al cargar gráfica</div>
        <pre>{{ grafica_desempeno_vs_salario_error }}</pre>
      </div>
    {% else %}
      <div class="plotly-graph">{{ grafica_desempeno_vs_salario | safe }}</div>
    {% endif %}
  </div>

  <!-- Top vs Bottom Performers -->
  <div class="section">
    <div class="section-header">
      <span class="icon"><i class="fas fa-trophy"></i></span>
      <h2>Top vs Bottom Performers</h2>
    </div>
    {% if grafica_top_bottom_error %}
      <div class="section-error">
        <div class="err-label"><i class="fas fa-exclamation-circle"></i> Error al cargar gráfica</div>
        <pre>{{ grafica_top_bottom_error }}</pre>
      </div>
    {% else %}
      <div class="plotly-graph">{{ grafica_top_bottom | safe }}</div>
    {% endif %}
  </div>

</main>

<div id="emp-balloon" class="emp-balloon"></div>

<script>
// Mapa de empleados (por nombre en minúsculas y por id) para completar detalles
const EMP_MAP = {};
window.EMP_MAP = EMP_MAP;
{% for r in emp_detalle %}
try{ EMP_MAP[{{ ((r.Empleado or '')|lower|trim)|tojson }}] = {{ r | tojson | safe }}; }catch(e){ }
try{ EMP_MAP[{{ ((r.IdEmpleado or '')|string|lower|trim)|tojson }}] = {{ r | tojson | safe }}; }catch(e){ }
{% endfor %}

function fmtCurrency(v){
  try{ return new Intl.NumberFormat('es-ES',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(Number(v)); }catch(e){ return v; }
}
function fmtDate(v){
  try{ const d=new Date(v); if(isNaN(d)) return v; return d.toLocaleDateString('es-ES'); }catch(e){ return v; }
}

document.addEventListener('click', function(e){
  const btn = e.target.closest('.emp-name');
  const balloon = document.getElementById('emp-balloon');
  if(btn){
    const data = btn.getAttribute('data-details');
    let obj;
    try{ obj = JSON.parse(data); }catch(ex){ obj = {raw: data}; }
    // completar con registro completo si existe en EMP_MAP (buscar por nombre o id)
    try{
      const nameKey = (obj.Empleado || obj.empleado || obj.EmpleadoNombre || '') .toString().toLowerCase().trim();
      const idKey = (obj.IdEmpleado || obj.idempleado || '') .toString().toLowerCase().trim();
      const fromMap = EMP_MAP[nameKey] || EMP_MAP[idKey];
      if(fromMap){
        for(const k in fromMap) if(obj[k]===undefined) obj[k]=fromMap[k];
      }
    }catch(e){/* ignore */}
    // preparar campos preferidos y ordenados (con fallback a minúsculas)
    const fields = [
      ['Empleado','empleado'], ['IdEmpleado','idempleado'], ['Empresa','empresa'], ['Puesto','puesto'], ['Departamento','departamento'], ['Sucursal','sucursal'], ['Ciudad','ciudad'],
      ['EdadActual','edadactual'], ['AntiguedadMeses','antiguedadmeses'], ['FechaIngreso','fechaingreso'], ['TipoContrato','tipocontrato'],
      ['SalarioBasePromedio','salariobasepromedio'], ['BonoAcumulado','bonoacumulado'], ['BeneficiosAcumulados','beneficiosacumulados'], ['CostoTotalNomina','costototalnomina'],
      ['Correo','correo'], ['Telefono','telefono'],
      ['PuntajeDesempenoProm','puntajedesempenoprom'], ['CumplimientoObjetivosProm','cumplimientoobjetivosprom'], ['FlagAltoPotencial','flagaltopotencial'],
      ['HorasCapacitacion','horascapacitacion'], ['CursosFinalizados','cursosfinalizados'], ['DiasFalta','diasfalta'], ['HorasExtra','horasextra'],
      ['TasaAusentismoProm','tasaAusentismoProm'.toLowerCase()], ['TasaPuntualidadProm','tasapuntualidadprom']
    ];

    let html = '<div class="balloon-header">'+(obj.Empleado || obj.empleado || 'Empleado')+'</div><div class="balloon-body">';

    // mostrar campos ordenados
    for(const f of fields){
      const [label, key] = f;
      let val = obj[label] !== undefined ? obj[label] : (obj[key] !== undefined ? obj[key] : undefined);
      if(val === undefined) continue;
      // formateos
      if(label.toLowerCase().includes('salario') || label.toLowerCase().includes('bono') || label.toLowerCase().includes('benef')){
        val = fmtCurrency(val);
      } else if(label.toLowerCase().includes('fecha')){
        val = fmtDate(val);
      } else if(typeof val === 'boolean'){
        val = val ? 'Sí' : 'No';
      }
      html += '<div><strong>'+label+':</strong> '+String(val)+'</div>';
    }

    // mostrar resto de campos que no estaban en la lista (evitar duplicados)
    const shown = new Set(fields.map(f=>f[0].toLowerCase()).concat(fields.map(f=>f[1].toLowerCase())));
    for(const k in obj){
      if(shown.has(k.toLowerCase())) continue;
      let v = obj[k]; if(v === null || v === undefined) v = 'N/A';
      html += '<div><strong>'+k+':</strong> '+String(v)+'</div>';
    }

    html += '</div>';
    balloon.innerHTML = html;
    balloon.style.display='block';
    const rect = btn.getBoundingClientRect();
    balloon.style.top = (window.scrollY + rect.bottom + 8) + 'px';
    const left = window.scrollX + rect.left;
    balloon.style.left = Math.max(8, Math.min(left, window.scrollX + window.innerWidth - 440)) + 'px';
    return;
  }
  if(balloon && !e.target.closest('#emp-balloon')){
    balloon.style.display='none';
  }
});
document.addEventListener('keydown', function(e){ if(e.key==='Escape'){ const b=document.getElementById('emp-balloon'); if(b) b.style.display='none'; }});
</script>

</body>
</html>
"""


# ======================================================
# 🚀 ROUTE
# ======================================================
@app.route("/")
def home():
  global_errors = []

  # Leer parámetros de filtro desde query string
  empresa_key = None
  try:
    v = request.args.get('empresa', None)
    if v is not None and v != "":
      empresa_key = int(v)
  except Exception:
    empresa_key = None

  departamento = request.args.get('departamento', '').strip() or None
  puesto = request.args.get('puesto', '').strip() or None
  ciudad = request.args.get('ciudad', '').strip() or None
  tipo_contrato = request.args.get('tipo_contrato', '').strip() or None
  genero = request.args.get('genero', '').strip() or None
  estado = request.args.get('estado', '').strip() or None
  
  try:
    antigüedad_min = int(request.args.get('antigüedad_min', 0) or 0)
    antigüedad_max = int(request.args.get('antigüedad_max', 0) or 0)
  except:
    antigüedad_min = antigüedad_max = 0
  
  try:
    salario_min = float(request.args.get('salario_min', 0) or 0)
    salario_max = float(request.args.get('salario_max', 0) or 0)
  except:
    salario_min = salario_max = 0

  empresas = []
  filter_options = {}
  try:
    empresas = get_empresas()
    filter_options = get_filter_options(empresa_key)
  except Exception as e:
    print("ERROR al obtener opciones de filtro:", e)

  filtro_departamento = normalize_filter_value(departamento, filter_options.get("departamentos", []))
  filtro_puesto = normalize_filter_value(puesto, filter_options.get("puestos", []))
  filtro_ciudad = normalize_filter_value(ciudad, filter_options.get("ciudades", []))
  filtro_tipo_contrato = normalize_filter_value(tipo_contrato, filter_options.get("tipos_contrato", []))
  filtro_genero = normalize_filter_value(genero, filter_options.get("generos", []))
  filtro_estado = normalize_filter_value(estado, filter_options.get("estados", []))

  # ── resumen ──
  try:
    resumen = resumen_ejecutivo(
      empresa_key,
      filtro_departamento,
      filtro_puesto,
      filtro_ciudad,
      filtro_tipo_contrato,
      filtro_genero,
      filtro_estado,
      antigüedad_min,
      antigüedad_max,
      salario_min,
      salario_max,
    )
  except Exception:
    tb = traceback.format_exc()
    print("ERROR resumen_ejecutivo:\n", tb)
    resumen = {"competitividad": 0, "beneficios": 0, "bonos": 0, "headcount": 0, "salario_promedio": 0}
    global_errors.append({"seccion": "resumen_ejecutivo", "mensaje": "No se pudo calcular el resumen", "traceback": tb})

  # ── equidad tabla ──
  eq = []
  eq_error = None
  try:
    eq = equidad(
      empresa_key,
      filtro_departamento,
      filtro_puesto,
      filtro_ciudad,
      filtro_tipo_contrato,
      filtro_genero,
      filtro_estado,
      antigüedad_min,
      antigüedad_max,
      salario_min,
      salario_max,
    )
  except Exception:
    tb = traceback.format_exc()
    print("ERROR equidad:\n", tb)
    eq_error = tb
    global_errors.append({"seccion": "equidad", "mensaje": "Tabla de equidad no disponible", "traceback": tb})

  # ── detalle empleados ──
  emp_detalle = []
  emp_detalle_error = None
  try:
    emp_detalle = detalle_empleados(
      empresa_key,
      filtro_departamento,
      filtro_puesto,
      filtro_ciudad,
      filtro_tipo_contrato,
      filtro_genero,
      filtro_estado,
      antigüedad_min,
      antigüedad_max,
      salario_min,
      salario_max,
    )
  except Exception:
    tb = traceback.format_exc()
    print("ERROR detalle_empleados:\n", tb)
    emp_detalle_error = tb
    global_errors.append({"seccion": "detalle_empleados", "mensaje": "Detalle de empleados no disponible", "traceback": tb})

  # ── gráfica competitividad ──
  grafica_comp = ""
  grafica_comp_error = None
  try:
    html, err = grafica_competitividad(empresa_key)
    if err:
      grafica_comp_error = err
    else:
      grafica_comp = html
  except Exception:
    tb = traceback.format_exc()
    print("ERROR grafica_competitividad:\n", tb)
    grafica_comp_error = tb
    global_errors.append({"seccion": "grafica_competitividad", "mensaje": "Gráfica no disponible", "traceback": tb})

  # ── gráfica beneficios ──
  grafica_benef = ""
  grafica_benef_error = None
  try:
    html, err = grafica_beneficios(empresa_key)
    if err:
      grafica_benef_error = err
    else:
      grafica_benef = html
  except Exception:
    tb = traceback.format_exc()
    print("ERROR grafica_beneficios:\n", tb)
    grafica_benef_error = tb
    global_errors.append({"seccion": "grafica_beneficios", "mensaje": "Gráfica no disponible", "traceback": tb})

  # ── gráfica bonos ──
  grafica_bonos_html = ""
  grafica_bonos_error = None
  try:
    html, err = grafica_bonos(empresa_key)
    if err:
      grafica_bonos_error = err
    else:
      grafica_bonos_html = html
  except Exception:
    tb = traceback.format_exc()
    print("ERROR grafica_bonos:\n", tb)
    grafica_bonos_error = tb
    global_errors.append({"seccion": "grafica_bonos", "mensaje": "Gráfica no disponible", "traceback": tb})

  # ── gráfica equidad ──
  grafica_equidad_html = ""
  grafica_equidad_error = None
  try:
    html, err = grafica_equidad(empresa_key)
    if err:
      grafica_equidad_error = err
    else:
      grafica_equidad_html = html
  except Exception:
    tb = traceback.format_exc()
    print("ERROR grafica_equidad:\n", tb)
    grafica_equidad_error = tb
    global_errors.append({"seccion": "grafica_equidad", "mensaje": "Gráfica no disponible", "traceback": tb})

  # ── gráficas avanzadas ──
  grafica_genero_html = ""
  grafica_genero_error = None
  try:
    html, err = grafica_genero(empresa_key)
    if err:
      grafica_genero_error = err
    else:
      grafica_genero_html = html
  except Exception:
    tb = traceback.format_exc()
    grafica_genero_error = tb

  grafica_tipo_contrato_html = ""
  grafica_tipo_contrato_error = None
  try:
    html, err = grafica_tipo_contrato(empresa_key)
    if err:
      grafica_tipo_contrato_error = err
    else:
      grafica_tipo_contrato_html = html
  except Exception:
    tb = traceback.format_exc()
    grafica_tipo_contrato_error = tb

  grafica_distribucion_salarios_html = ""
  grafica_distribucion_salarios_error = None
  try:
    html, err = grafica_distribucion_salarios(empresa_key)
    if err:
      grafica_distribucion_salarios_error = err
    else:
      grafica_distribucion_salarios_html = html
  except Exception:
    tb = traceback.format_exc()
    grafica_distribucion_salarios_error = tb

  grafica_ausentismo_html = ""
  grafica_ausentismo_error = None
  try:
    html, err = grafica_ausentismo(empresa_key)
    if err:
      grafica_ausentismo_error = err
    else:
      grafica_ausentismo_html = html
  except Exception:
    tb = traceback.format_exc()
    grafica_ausentismo_error = tb

  grafica_desempeno_vs_salario_html = ""
  grafica_desempeno_vs_salario_error = None
  try:
    html, err = grafica_desempeno_vs_salario(empresa_key)
    if err:
      grafica_desempeno_vs_salario_error = err
    else:
      grafica_desempeno_vs_salario_html = html
  except Exception:
    tb = traceback.format_exc()
    grafica_desempeno_vs_salario_error = tb

  grafica_top_bottom_html = ""
  grafica_top_bottom_error = None
  try:
    html, err = grafica_top_bottom(empresa_key)
    if err:
      grafica_top_bottom_error = err
    else:
      grafica_top_bottom_html = html
  except Exception:
    tb = traceback.format_exc()
    grafica_top_bottom_error = tb

  # Debug: verificar qué HTML se está sirviendo
  if 'fas fa-' in HTML:
    print("[DEBUG] HTML contiene 'fas fa-': YES")
  else:
    print("[DEBUG] HTML contiene 'fas fa-': NO")

  # Debug: ver primeras 500 chars de section-header
  idx = HTML.find('Competitividad')
  if idx >= 0:
    print(f"[DEBUG] Sección Competitividad: {HTML[idx-100:idx+100]}")

  # Reemplazar emojis con Font Awesome dinámicamente
  html_rendered = HTML.replace('<span class="icon">📈</span>', '<span class="icon"><i class="fas fa-chart-line"></i></span>')
  html_rendered = html_rendered.replace('<span class="icon">🎁</span>', '<span class="icon"><i class="fas fa-gift"></i></span>')
  html_rendered = html_rendered.replace('<span class="icon">🏆</span>', '<span class="icon"><i class="fas fa-trophy"></i></span>')
  html_rendered = html_rendered.replace('<span class="icon">⚖️</span>', '<span class="icon"><i class="fas fa-scale-balanced"></i></span>')
  html_rendered = html_rendered.replace('<span class="icon">📋</span>', '<span class="icon"><i class="fas fa-list"></i></span>')
  html_rendered = html_rendered.replace('<span class="icon">👥</span>', '<span class="icon"><i class="fas fa-users"></i></span>')
  html_rendered = html_rendered.replace('<span class="icon">📜</span>', '<span class="icon"><i class="fas fa-document"></i></span>')
  html_rendered = html_rendered.replace('<span class="icon">💰</span>', '<span class="icon"><i class="fas fa-money-bill"></i></span>')
  html_rendered = html_rendered.replace('<span class="icon">⏰</span>', '<span class="icon"><i class="fas fa-hourglass-end"></i></span>')
  html_rendered = html_rendered.replace('<span class="icon">⚠️</span>', '<span class="icon"><i class="fas fa-triangle-exclamation"></i></span>')

  return render_template_string(
    html_rendered,
    resumen=resumen,
    eq=eq,
    eq_error=eq_error,
    emp_detalle=emp_detalle,
    emp_detalle_error=emp_detalle_error,
    grafica_comp=grafica_comp,
    grafica_comp_error=grafica_comp_error,
    grafica_benef=grafica_benef,
    grafica_benef_error=grafica_benef_error,
    grafica_bonos=grafica_bonos_html,
    grafica_bonos_error=grafica_bonos_error,
    grafica_equidad=grafica_equidad_html,
    grafica_equidad_error=grafica_equidad_error,
    grafica_genero=grafica_genero_html,
    grafica_genero_error=grafica_genero_error,
    grafica_tipo_contrato=grafica_tipo_contrato_html,
    grafica_tipo_contrato_error=grafica_tipo_contrato_error,
    grafica_distribucion_salarios=grafica_distribucion_salarios_html,
    grafica_distribucion_salarios_error=grafica_distribucion_salarios_error,
    grafica_ausentismo=grafica_ausentismo_html,
    grafica_ausentismo_error=grafica_ausentismo_error,
    grafica_desempeno_vs_salario=grafica_desempeno_vs_salario_html,
    grafica_desempeno_vs_salario_error=grafica_desempeno_vs_salario_error,
    grafica_top_bottom=grafica_top_bottom_html,
    grafica_top_bottom_error=grafica_top_bottom_error,
    global_errors=global_errors,
    empresas=empresas,
    empresa_selected=empresa_key,
    filter_options=filter_options,
    filtro_departamento=departamento or "",
    filtro_puesto=puesto or "",
    filtro_ciudad=ciudad or "",
    filtro_tipo_contrato=tipo_contrato or "",
    filtro_genero=genero or "",
    filtro_estado=estado or "",
    filtro_antigüedad_min=antigüedad_min,
    filtro_antigüedad_max=antigüedad_max,
    filtro_salario_min=salario_min,
    filtro_salario_max=salario_max,
  )


# ======================================================
# 🏥 HEALTH CHECK
# ======================================================
@app.route("/health")
def health():
    resultado = {}
    try:
        conn = get_connection()
        resultado["conexion"] = "[OK] Conexión confirmada"
        cur = conn.cursor()

        # Listar todas las tablas
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name;
        """)
        resultado["tablas"] = [r[0] for r in cur.fetchall()]

        # Columnas de Fact_Nomina
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'fact_nomina'
            ORDER BY ordinal_position;
        """)
        cols = cur.fetchall()
        if not cols:
            # intentar con mayúsculas
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'Fact_Nomina'
                ORDER BY ordinal_position;
            """)
            cols = cur.fetchall()
        resultado["columnas_fact_nomina"] = [f"{c[0]} ({c[1]})" for c in cols]

        # Columnas de Ref_Benchmark_Salarial
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE lower(table_name) = 'ref_benchmark_salarial'
            ORDER BY ordinal_position;
        """)
        cols2 = cur.fetchall()
        resultado["columnas_benchmark"] = [f"{c[0]} ({c[1]})" for c in cols2]

        # Counts
        for tabla in resultado.get("tablas", []):
            try:
                cur.execute(f'SELECT COUNT(*) FROM "{tabla}";')
                row = cur.fetchone()
                resultado[f"count_{tabla}"] = row[0] if row is not None else 0
            except Exception as e:
                resultado[f"count_{tabla}"] = f"ERROR: {e}"

        cur.close()
        conn.close()
        resultado["status"] = "ok"
    except Exception as e:
        resultado["status"] = "error"
        resultado["error"] = traceback.format_exc()

    # Devolver como HTML legible
    lines = []
    for k, v in resultado.items():
        if isinstance(v, list):
            lines.append(f"<b>{k}</b>:<br>" + "<br>".join(f"&nbsp;&nbsp;• {x}" for x in v))
        else:
            lines.append(f"<b>{k}</b>: {v}")
    return "<html><body style='font-family:monospace;padding:30px;background:#0d1117;color:#f0f6fc'>" + "<br><br>".join(lines) + "</body></html>"


@app.route('/favicon.ico')
def favicon():
    return Response(status=204)


if __name__ == "__main__":
    import inspect, os
    print(">>> INICIANDO FLASK...")
    print(f"[DEBUG] Archivo actual: {__file__}")
    print(f"[DEBUG] Directorio actual: {os.getcwd()}")
    # Debug: verificar qué HTML hay en memoria (v2)
    fas_count = HTML.count('fas fa-')
    emoji_count = HTML.count('📈')
    print(f"[DEBUG] HTML: {fas_count} fas + {emoji_count} emojis")
    try:
        conn = get_connection()
        print("[OK] CONEXIÓN A BD ESTABLECIDA")
        conn.close()
    except Exception:
        print("❌ ERROR EN CONEXIÓN A BASE DE DATOS:")
        print(traceback.format_exc())

    app.run(debug=True, host="127.0.0.1", port=5001, use_reloader=False)
