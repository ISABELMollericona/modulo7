from flask import Flask, render_template_string, request
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
import json
import random

app = Flask(__name__)

# ======================================================
# 🎲 GENERADOR DE DATOS ESTÁTICOS PERSISTENTES
# ======================================================

random.seed(42) 

NOMBRES = ["Cayetana", "Amador", "Roque Leon", "Pia", "Jorge", "Cayetana", "Julie", "Elena", "Jorge", "Carmen", 
           "Roberto", "Lucia", "Fernando", "Gabriela", "Ricardo", "Patricia", "Daniel", "Laura", "Oscar", "Veronica"]
APELLIDOS = ["Porras", "Bonet", "Leon", "Valverde", "Lopez", "Gonzalez", "Martinez", "Sanchez", "Romero", "Torres",
             "Porras", "Rivera", "Vargas", "Castillo", "Chavez", "Silva", "Mendoza", "Rojas", "Miranda", "Contreras"]

SUCURSALES = ["Sucursal - Central", "Sucursal A", "Sucursal B", "Sucursal C"]
DEPARTAMENTOS = ["Tecnología", "Ventas", "RRHH", "Finanzas", "Operaciones"]
PUESTOS_POR_DEPT = {
    "Tecnología": [("Analista Senior", 18000), ("Dev Junior", 9000), ("Lider de proyectos", 12000)],
    "Ventas": [("Ejecutivo Ventas", 6000), ("Gerente Comercial", 15000), ("Gerente de ventas", 4500)],
    "RRHH": [("Analista RRHH", 8000), ("Gerente RRHH", 16000)],
    "Finanzas": [("Gerente de Finanzas", 10000), ("Auditor", 12000), ("Contador", 28000)],
    "Operaciones": [("Lider de proyectos", 11000), ("Asistente", 3500)]
}

EMPRESAS_EXTERNAS = {
    "InnovaSoft Latam": {"factor_salario": 1.15, "factor_beneficios": 1.2},
    "GlobalServices Inc": {"factor_salario": 1.05, "factor_beneficios": 0.9},
    "StartupX": {"factor_salario": 0.90, "factor_beneficios": 0.5},
    "PymeBolivia SA": {"factor_salario": 0.85, "factor_beneficios": 0.6},
    "CorporativoBig": {"factor_salario": 1.25, "factor_beneficios": 1.3}
}

def generate_persistent_data():
    employees = []
    num_employees = 100
    
    for i in range(num_employees):
        nombre = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"
        dept = random.choice(DEPARTAMENTOS)
        puesto_titulo, salario_base_ref = random.choice(PUESTOS_POR_DEPT[dept])
        sucursal = random.choice(SUCURSALES)
        
        variacion = random.uniform(0.9, 1.1)
        salario_base = int(salario_base_ref * variacion)
        
        factor_ben = 1.2 if dept in ["Tecnología", "RRHH"] else 1.0
        beneficios = int(salario_base * random.uniform(0.10, 0.25) * factor_ben)
        
        desempeno = random.randint(50, 100)
        bono_potencial = int(salario_base * 0.2)
        bono = int(bono_potencial * (desempeno/100)) if random.random() > 0.2 else 0
        
        mercados = {}
        for emp_ext, factores in EMPRESAS_EXTERNAS.items():
            mercados[emp_ext] = int(salario_base_ref * factores['factor_salario'])

        employees.append({
            "nombre": nombre,
            "departamento": dept,
            "puesto": puesto_titulo,
            "sucursal": sucursal,
            "salario_base": float(salario_base),
            "beneficios": float(beneficios),
            "bono": float(bono),
            "desempeno": desempeno,
            "mercados": mercados
        })
        
    return employees

DATA_EMPLEADOS = generate_persistent_data()

# ======================================================
# 📊 LÓGICA DE GRÁFICAS
# ======================================================

def get_grafica_1_heatmap():
    """
    ESTILO IMAGEN REFERENCIA: Cuadrícula con números grandes dentro
    """
    y_labels = SUCURSALES
    x_labels = sorted(list(set([e['puesto'] for e in DATA_EMPLEADOS])))
    
    matrix_sum = [[0.0 for _ in x_labels] for _ in y_labels]
    matrix_count = [[0 for _ in x_labels] for _ in y_labels]
    
    for e in DATA_EMPLEADOS:
        if e['puesto'] in x_labels and e['sucursal'] in y_labels:
            y_idx = y_labels.index(e['sucursal'])
            x_idx = x_labels.index(e['puesto'])
            matrix_sum[y_idx][x_idx] += e['salario_base']
            matrix_count[y_idx][x_idx] += 1
            
    z_values = []
    text_values = []
    
    for y in range(len(y_labels)):
        row_z = []
        row_text = []
        for x in range(len(x_labels)):
            if matrix_count[y][x] > 0:
                avg = matrix_sum[y][x] / matrix_count[y][x]
                row_z.append(avg)
                # El número que va DENTRO del cuadro
                row_text.append(f"{avg:.0f}") # Redondeado para que se vea limpio como en la imagen, o .2f si prefieres decimales
            else:
                row_z.append(None)
                row_text.append("")
        z_values.append(row_z)
        text_values.append(row_text)

    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=x_labels,
        y=y_labels,
        colorscale='RdYlGn', # Verde a Rojo (como gestión de riesgos) o 'Viridis'
        hoverongaps=False,
        text=text_values,     
        texttemplate="%{text}", # Muestra el número grande
        textfont={"size": 14, "color": "black", "family": "Arial Black"}, # Texto grande y oscuro para contraste
        hovertemplate="Sucursal: %{y}<br>Puesto: %{x}<br>Promedio: %{z:.2f} Bs<extra></extra>"
    ))

    fig.update_layout(
        title='1. Mapa de Calor: Promedio Salarial por Cuadro',
        xaxis_title='Puesto',
        yaxis_title='Sucursal',
        template='plotly_white', # Fondo blanco para que parezca más a la imagen de referencia, o plotly_dark
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff'),
        height=500
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)

def get_grafica_2_comparativa(empresa_seleccionada):
    puestos_internos = {}
    for e in DATA_EMPLEADOS:
        if e['puesto'] not in puestos_internos:
            puestos_internos[e['puesto']] = []
        puestos_internos[e['puesto']].append(e['salario_base'])
    
    labels = []
    avg_nosotros = []
    avg_competencia = []
    
    factor_comp = EMPRESAS_EXTERNAS[empresa_seleccionada]['factor_salario']
    
    for p, salaries in puestos_internos.items():
        labels.append(p)
        avg = sum(salaries)/len(salaries)
        avg_nosotros.append(avg)
        avg_competencia.append(avg * factor_comp)

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Nuestra Empresa', x=labels, y=avg_nosotros, marker_color='#06b6d4',
                         hovertemplate='<b>%{x}</b><br>Nosotros: %{y:.2f} Bs<extra></extra>'))
    fig.add_trace(go.Bar(name=empresa_seleccionada, x=labels, y=avg_competencia, marker_color='#ec4899',
                         hovertemplate='<b>%{x}</b><br>Competencia: %{y:.2f} Bs<extra></extra>'))

    fig.update_layout(
        title=f'2. Competitividad: Nosotros vs {empresa_seleccionada}',
        barmode='group',
        yaxis_title='Salario Promedio (Bs)',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff'),
        xaxis_tickangle=-45
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)

def get_grafica_3_beneficios():
    dept_ben = {}
    dept_count = {}
    for e in DATA_EMPLEADOS:
        dept = e['departamento']
        dept_ben[dept] = dept_ben.get(dept, 0) + e['beneficios']
        dept_count[dept] = dept_count.get(dept, 0) + 1
        
    depts = list(dept_ben.keys())
    total_ben = [dept_ben[d] for d in depts]
    avg_ben_per_emp = [dept_ben[d]/dept_count[d] for d in depts]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Inversión Total', x=depts, y=total_ben, marker_color='#84cc16', opacity=0.8,
                         hovertemplate='<b>%{x}</b><br>Total: %{y:.2f} Bs<extra></extra>'))
    fig.add_trace(go.Scatter(name='Promedio/Empleado', x=depts, y=avg_ben_per_emp, 
                             mode='lines+markers', line=dict(width=4, color='#facc15'), yaxis='y2',
                             marker=dict(size=10, color='#fff'),
                             hovertemplate='<b>%{x}</b><br>Promedio: %{y:.2f} Bs<extra></extra>'))

    fig.update_layout(
        title='3. Beneficios: Inversión Total vs Promedio',
        yaxis=dict(title='Total (Bs)'),
        yaxis2=dict(title='Promedio (Bs)', overlaying='y', side='right'),
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff')
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)

def get_grafica_4_equidad_bonos():
    sorted_bonos = sorted([e['bono'] for e in DATA_EMPLEADOS])
    total_bonos = sum(sorted_bonos)
    
    if total_bonos == 0:
        return json.dumps(go.Figure(), cls=PlotlyJSONEncoder)

    cumulative_bonos = []
    current_sum = 0
    percent_employees = []
    
    for i, b in enumerate(sorted_bonos):
        current_sum += b
        cumulative_bonos.append((current_sum / total_bonos) * 100)
        percent_employees.append(((i + 1) / len(sorted_bonos)) * 100)
        
    perfect_equality = [p for p in percent_employees]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=percent_employees, y=perfect_equality, name='Equidad Perfecta', line=dict(dash='dot', width=2, color='#94a3b8')))
    fig.add_trace(go.Scatter(x=percent_employees, y=cumulative_bonos, name='Distribución Real', 
                             fill='tozeroy', fillcolor='rgba(249, 115, 22, 0.3)', 
                             line=dict(color='#f97316', width=3)))

    fig.update_layout(
        title='4. Concentración de Bonos (%)',
        xaxis_title='% Empleados (Menor a Mayor Bono)',
        yaxis_title='% Acumulado Bonos',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff')
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)

def get_grafica_5_top_performers():
    sorted_emps = sorted(DATA_EMPLEADOS, key=lambda x: x['salario_base'] + x['bono'], reverse=True)[:15]
    
    nombres = [e['nombre'] for e in reversed(sorted_emps)]
    salarios = [e['salario_base'] + e['bono'] for e in reversed(sorted_emps)]
    desempenos = [e['desempeno'] for e in reversed(sorted_emps)]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=nombres, 
        x=salarios, 
        name='Salario Total',
        orientation='h',
        marker_color='#8b5cf6',
        hovertemplate='<b>%{y}</b><br>Total: %{x:.2f} Bs<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        y=nombres,
        x=desempenos,
        name='Desempeño',
        xaxis='x2',
        mode='markers',
        marker=dict(color='#22d3ee', size=10, symbol='diamond', line=dict(width=2, color='white')),
        hovertemplate='<b>%{y}</b><br>Desempeño: %{x}<extra></extra>'
    ))

    fig.update_layout(
        title='5. Top 15: Costo Laboral vs Desempeño',
        yaxis_title='Empleado',
        xaxis_title='Salario Total (Bs)',
        xaxis2=dict(title='Puntaje Desempeño', overlaying='x', side='top'),
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ffffff'),
        height=650
    )
    return json.dumps(fig, cls=PlotlyJSONEncoder)

# ======================================================
# 🌐 RUTA FLASK
# ======================================================

@app.route('/')
def dashboard():
    empresa_sel = request.args.get('competidor', 'InnovaSoft Latam')
    if empresa_sel not in EMPRESAS_EXTERNAS:
        empresa_sel = 'InnovaSoft Latam'
        
    g1 = get_grafica_1_heatmap()
    g2 = get_grafica_2_comparativa(empresa_sel)
    g3 = get_grafica_3_beneficios()
    g4 = get_grafica_4_equidad_bonos()
    g5 = get_grafica_5_top_performers()
    
    return render_template_string(HTML_TEMPLATE, 
                                  g1=g1, g2=g2, g3=g3, g4=g4, g5=g5,
                                  empresas=list(EMPRESAS_EXTERNAS.keys()),
                                  selected=empresa_sel)

# ======================================================
# 📄 HTML TEMPLATE (UNA SOLA COLUMNA)
# ======================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Dashboard Compensación - Crucicel</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root{
            --bg: #0f172a;
            --card: #1e293b;
            --text: #f1f5f9;
            --muted: #94a3b8;
            --accent: #06b6d4;
        }
        .light-theme{
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #0f172a;
            --muted: #475569;
            --accent: #06b6d4;
        }
        body { 
            background-color: var(--bg); 
            color: var(--text); 
            font-family: 'Inter', sans-serif; 
            margin: 0; 
            padding: 20px; 
            transition: background-color 250ms, color 250ms;
        }
        header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 30px; 
            border-bottom: 2px solid rgba(71,85,105,0.25); 
            padding-bottom: 20px; 
        }
        h1 { margin: 0; font-size: 1.8rem; color: var(--accent); text-transform: uppercase; letter-spacing: 1px; }
        .controls select { 
            padding: 12px; 
            border-radius: 8px; 
            background: var(--card); 
            color: var(--text); 
            border: 2px solid var(--accent); 
            font-size: 1rem; 
            cursor: pointer; 
            font-weight: bold;
        }
        .theme-btn{
            padding: 8px 12px;
            margin-right: 12px;
            border-radius: 8px;
            background: transparent;
            color: var(--text);
            border: 2px solid var(--accent);
            cursor: pointer;
            font-weight: 600;
        }
        /* UNA SOLA COLUMNA */
        .grid { 
            display: grid; 
            grid-template-columns: 1fr; 
            gap: 30px; 
            max-width: 1200px;
            margin: 0 auto;
        }
        .card { 
            background: var(--card); 
            border-radius: 16px; 
            padding: 25px; 
            border: 1px solid rgba(71,85,105,0.2); 
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.15); 
            transition: background-color 250ms, color 250ms;
        }
        .subtitle { color: var(--muted); font-size: 0.9rem; margin-top: 5px; }
    </style>
</head>
<body>

<header>
    <div>
        <h1>Módulo 7: Compensación y Beneficios</h1>
        <p class="subtitle">Análisis Modulo 7| Desarrollado por grupo 7</p>
    </div>
    <div class="controls">
        <form method="get">
            <button type="button" id="themeToggle" class="theme-btn">Tema: Oscuro</button>
            <label for="competidor" style="margin-right:10px; color:var(--muted);">Comparar con:</label>
            <select name="competidor" id="competidor" onchange="this.form.submit()">
                {% for emp in empresas %}
                    <option value="{{ emp }}" {% if emp == selected %}selected{% endif %}>{{ emp }}</option>
                {% endfor %}
            </select>
        </form>
    </div>
</header>

<div class="grid">
    <!-- 1. Mapa de Calor Estilo Gestión de Riesgos -->
    <div class="card">
        <div id="g1"></div>
    </div>
    
    <!-- 2. Competitividad -->
    <div class="card">
        <div id="g2"></div>
    </div>

    <!-- 3. Beneficios -->
    <div class="card">
        <div id="g3"></div>
    </div>

    <!-- 4. Equidad Bonos -->
    <div class="card">
        <div id="g4"></div>
    </div>

    <!-- 5. Top Performers -->
    <div class="card">
        <div id="g5"></div>
    </div>
</div>

<script>
    const config = {responsive: true, displayModeBar: false};
    function draw(id, json) { Plotly.newPlot(id, JSON.parse(json), null, config); }
    
    draw('g1', '{{ g1 | safe }}');
    draw('g2', '{{ g2 | safe }}');
    draw('g3', '{{ g3 | safe }}');
    draw('g4', '{{ g4 | safe }}');
    draw('g5', '{{ g5 | safe }}');

    // Tema claro/oscuro: persistir en localStorage
    const themeToggle = document.getElementById('themeToggle');
    function applyTheme(theme){
        if(theme === 'light'){
            document.body.classList.add('light-theme');
            themeToggle.textContent = 'Tema: Claro';
        } else {
            document.body.classList.remove('light-theme');
            themeToggle.textContent = 'Tema: Oscuro';
        }
        localStorage.setItem('theme', theme);
    }

    themeToggle.addEventListener('click', () => {
        const current = document.body.classList.contains('light-theme') ? 'light' : 'dark';
        const next = current === 'light' ? 'dark' : 'light';
        applyTheme(next);
    });

    // Inicializar tema: preferencia guardada o preferencia del sistema
    (function(){
        const saved = localStorage.getItem('theme');
        if(saved) return applyTheme(saved);
        const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
        applyTheme(prefersLight ? 'light' : 'dark');
    })();
</script>

</body>
</html>
"""

if __name__ == '__main__':
    print(" Servidor iniciado en http://127.0.0.1:5001")
    app.run(debug=True, port=5001)