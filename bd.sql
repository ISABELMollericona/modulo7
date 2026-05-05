-- ============================================================
-- DATA WAREHOUSE DE RECURSOS HUMANOS
-- Esquema Físico — PostgreSQL
-- Modelo Estrella Modular: 8 Facts + 8 Dims + 2 Vistas
-- Solo estructura (sin datos)
-- ============================================================


-- ============================================================
-- DIMENSIONES COMPARTIDAS (6)
-- Fase 0: pre-carga antes de cualquier fact
-- ============================================================

CREATE TABLE DimTiempo (
    TiempoKey           INT             PRIMARY KEY,
    Fecha               DATE            NOT NULL,
    Dia                 INT             NOT NULL,
    DiaSemana           VARCHAR(15)     NOT NULL,
    DiaDelAnio          INT             NOT NULL,
    Semana              INT             NOT NULL,
    Mes                 INT             NOT NULL,
    NombreMes           VARCHAR(15)     NOT NULL,
    Trimestre           INT             NOT NULL,
    NombreTrimestre     VARCHAR(5)      NOT NULL,
    Semestre            INT             NOT NULL,
    Anio                INT             NOT NULL,
    EsFinDeSemana       BOOLEAN         NOT NULL DEFAULT FALSE,
    EsFestivo           BOOLEAN         NOT NULL DEFAULT FALSE,
    NombreFestivo       VARCHAR(50),
    EsDiaLaboral        BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE TABLE DimSucursal (
    SucursalKey         INT             PRIMARY KEY,
    IdSucursalNegocio   VARCHAR(20)     NOT NULL,
    NombreSucursal      VARCHAR(100)    NOT NULL,
    Direccion           VARCHAR(200),
    Ciudad              VARCHAR(100),
    Estado              VARCHAR(100),
    Pais                VARCHAR(100)    NOT NULL,
    CodigoPostal        VARCHAR(20),
    Telefono            VARCHAR(30),
    EsActiva            BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE TABLE DimEmpleado (
    EmpleadoKey         INT             PRIMARY KEY,
    IdEmpleadoNegocio   VARCHAR(20)     NOT NULL,
    NombreCompleto      VARCHAR(150)    NOT NULL,
    Nombre              VARCHAR(80)     NOT NULL,
    Apellido            VARCHAR(80)     NOT NULL,
    Genero              VARCHAR(20),
    FechaNacimiento     DATE,
    EstadoCivil         VARCHAR(30),
    NivelEducativo      VARCHAR(50),
    Nacionalidad        VARCHAR(50),
    CorreoElectronico   VARCHAR(100),
    Telefono            VARCHAR(30),
    FechaIngreso        DATE            NOT NULL,
    FechaBaja           DATE,
    MotivoBaja          VARCHAR(100),
    EstadoActual        VARCHAR(20)     NOT NULL DEFAULT 'Activo',
    FechaInicioVigencia DATE            NOT NULL,
    FechaFinVigencia    DATE,
    EsRegistroActual    BOOLEAN         NOT NULL DEFAULT TRUE
);

CREATE TABLE DimPuesto (
    PuestoKey           INT             PRIMARY KEY,
    IdPuestoNegocio     VARCHAR(20)     NOT NULL,
    NombrePuesto        VARCHAR(100)    NOT NULL,
    NivelJerarquico     VARCHAR(50)     NOT NULL,
    AreaFuncional       VARCHAR(80),
    BandaSalarial       VARCHAR(30),
    EsRolCritico        BOOLEAN         NOT NULL DEFAULT FALSE,
    Descripcion         VARCHAR(300)
);

CREATE TABLE DimDepartamento (
    DepartamentoKey     INT             PRIMARY KEY,
    IdDepartamentoNeg   VARCHAR(20)     NOT NULL,
    NombreDepartamento  VARCHAR(100)    NOT NULL,
    NombreGerente       VARCHAR(150),
    DepartamentoPadre   VARCHAR(100),
    NivelOrganizacional INT
);

CREATE TABLE DimHabilidad (
    HabilidadKey        INT             PRIMARY KEY,
    IdHabilidadNegocio  VARCHAR(20)     NOT NULL,
    NombreHabilidad     VARCHAR(100)    NOT NULL,
    CategoriaHabilidad  VARCHAR(80)     NOT NULL,
    NivelEsperado       INT,
    Descripcion         VARCHAR(300)
);


-- ============================================================
-- DIMENSIONES DE MÓDULO (2)
-- Fase 1: las crea el equipo responsable
-- ============================================================

CREATE TABLE DimCandidato (
    CandidatoKey        INT             PRIMARY KEY,
    IdCandidatoNegocio  VARCHAR(20)     NOT NULL,
    NombreCompleto      VARCHAR(150)    NOT NULL,
    CorreoElectronico   VARCHAR(100),
    Telefono            VARCHAR(30),
    NivelEducativo      VARCHAR(50),
    AniosExperiencia    INT,
    Ubicacion           VARCHAR(100),
    HabilidadPrincipal  VARCHAR(100),
    EsInterno           BOOLEAN         NOT NULL DEFAULT FALSE
);

CREATE TABLE DimCurso (
    CursoKey            INT             PRIMARY KEY,
    IdCursoNegocio      VARCHAR(20)     NOT NULL,
    NombreCurso         VARCHAR(150)    NOT NULL,
    Modalidad           VARCHAR(30)     NOT NULL,
    DuracionHoras       NUMERIC(6,1)    NOT NULL,
    Proveedor           VARCHAR(100),
    CategoriaCurso      VARCHAR(80),
    NivelDificultad     VARCHAR(30)
);


-- ============================================================
-- FACTS (7) + REFERENCIA (1)
-- Fase 1: cada equipo carga su tabla en paralelo
-- ============================================================

-- Equipo 1: Reclutamiento y Selección
CREATE TABLE Fact_Reclutamiento (
    FactReclutamientoKey    INT             PRIMARY KEY,
    TiempoKey               INT             NOT NULL REFERENCES DimTiempo (TiempoKey),
    CandidatoKey            INT             NOT NULL REFERENCES DimCandidato (CandidatoKey),
    PuestoKey               INT             NOT NULL REFERENCES DimPuesto (PuestoKey),
    DepartamentoKey         INT             NOT NULL REFERENCES DimDepartamento (DepartamentoKey),
    SucursalKey             INT             NOT NULL REFERENCES DimSucursal (SucursalKey),
    IdVacanteNegocio        VARCHAR(20)     NOT NULL,
    EtapaReclutamiento      VARCHAR(30)     NOT NULL,
    FuenteReclutamiento     VARCHAR(50)     NOT NULL,
    DiasEnEtapa             INT             DEFAULT 0,
    DiasContratacionTotal   INT,
    CostoContratacion       NUMERIC(12,2)   DEFAULT 0,
    CantidadCandidatos      INT             NOT NULL DEFAULT 1,
    FlagAvanceEtapa         BOOLEAN         NOT NULL DEFAULT FALSE,
    FlagContratado          BOOLEAN         NOT NULL DEFAULT FALSE
);

-- Equipo 2: Gestión de Personal y Nómina
CREATE TABLE Fact_Nomina (
    FactNominaKey           INT             PRIMARY KEY,
    TiempoKey               INT             NOT NULL REFERENCES DimTiempo (TiempoKey),
    EmpleadoKey             INT             NOT NULL REFERENCES DimEmpleado (EmpleadoKey),
    PuestoKey               INT             NOT NULL REFERENCES DimPuesto (PuestoKey),
    DepartamentoKey         INT             NOT NULL REFERENCES DimDepartamento (DepartamentoKey),
    SucursalKey             INT             NOT NULL REFERENCES DimSucursal (SucursalKey),
    TipoContrato            VARCHAR(30)     NOT NULL,
    SalarioBase             NUMERIC(12,2)   NOT NULL DEFAULT 0,
    Bono                    NUMERIC(12,2)   NOT NULL DEFAULT 0,
    Beneficios              NUMERIC(12,2)   NOT NULL DEFAULT 0,
    CostoTotalNomina        NUMERIC(12,2)   NOT NULL DEFAULT 0,
    Headcount               INT             NOT NULL DEFAULT 1,
    AntiguedadMeses         INT,
    EdadActual              INT,
    FlagActivo              BOOLEAN         NOT NULL DEFAULT TRUE,
    FlagBaja                BOOLEAN         NOT NULL DEFAULT FALSE,
    FlagNuevoIngreso        BOOLEAN         NOT NULL DEFAULT FALSE,
    FlagJubilacionProxima   BOOLEAN         NOT NULL DEFAULT FALSE
);

-- Equipo 3: Formación y Desarrollo
CREATE TABLE Fact_Capacitacion (
    FactCapacitacionKey     INT             PRIMARY KEY,
    TiempoKey               INT             NOT NULL REFERENCES DimTiempo (TiempoKey),
    EmpleadoKey             INT             NOT NULL REFERENCES DimEmpleado (EmpleadoKey),
    CursoKey                INT             NOT NULL REFERENCES DimCurso (CursoKey),
    DepartamentoKey         INT             NOT NULL REFERENCES DimDepartamento (DepartamentoKey),
    HabilidadKey            INT             NOT NULL REFERENCES DimHabilidad (HabilidadKey),
    HorasCapacitacion       NUMERIC(6,1)    NOT NULL DEFAULT 0,
    CostoCapacitacion       NUMERIC(12,2)   NOT NULL DEFAULT 0,
    PuntajePre              NUMERIC(5,2),
    PuntajePost             NUMERIC(5,2),
    MejoraHabilidad         NUMERIC(5,2),
    FlagFinalizado          BOOLEAN         NOT NULL DEFAULT FALSE
);

-- Equipo 4: Evaluación del Desempeño
CREATE TABLE Fact_Evaluacion (
    FactEvaluacionKey       INT             PRIMARY KEY,
    TiempoKey               INT             NOT NULL REFERENCES DimTiempo (TiempoKey),
    EmpleadoKey             INT             NOT NULL REFERENCES DimEmpleado (EmpleadoKey),
    PuestoKey               INT             NOT NULL REFERENCES DimPuesto (PuestoKey),
    DepartamentoKey         INT             NOT NULL REFERENCES DimDepartamento (DepartamentoKey),
    HabilidadKey            INT             REFERENCES DimHabilidad (HabilidadKey),
    PeriodoEvaluacion       VARCHAR(30)     NOT NULL,
    TipoEvaluacion          VARCHAR(30)     NOT NULL,
    PuntajeDesempeno        NUMERIC(5,2)    NOT NULL,
    CumplimientoObjetivos   NUMERIC(5,2)    NOT NULL DEFAULT 0,
    CalificacionFinal       VARCHAR(30)     NOT NULL,
    FlagAltoPotencial       BOOLEAN         NOT NULL DEFAULT FALSE
);

-- Equipo 5: Clima Organizacional y Bienestar
CREATE TABLE Fact_Clima_Bienestar (
    FactClimaBienestarKey   INT             PRIMARY KEY,
    TiempoKey               INT             NOT NULL REFERENCES DimTiempo (TiempoKey),
    EmpleadoKey             INT             NOT NULL REFERENCES DimEmpleado (EmpleadoKey),
    DepartamentoKey         INT             NOT NULL REFERENCES DimDepartamento (DepartamentoKey),
    SucursalKey             INT             NOT NULL REFERENCES DimSucursal (SucursalKey),
    TipoMedicion            VARCHAR(50)     NOT NULL,
    PuntajeSatisfaccion     NUMERIC(4,2),
    PuntajeCompromiso       NUMERIC(4,2),
    CantidadAccidentes      INT             NOT NULL DEFAULT 0,
    FlagAccidente           BOOLEAN         NOT NULL DEFAULT FALSE
);

-- Equipo 6: Gestión de Tiempos y Asistencia
CREATE TABLE Fact_Asistencia (
    FactAsistenciaKey       INT             PRIMARY KEY,
    TiempoKey               INT             NOT NULL REFERENCES DimTiempo (TiempoKey),
    EmpleadoKey             INT             NOT NULL REFERENCES DimEmpleado (EmpleadoKey),
    PuestoKey               INT             NOT NULL REFERENCES DimPuesto (PuestoKey),
    DepartamentoKey         INT             NOT NULL REFERENCES DimDepartamento (DepartamentoKey),
    SucursalKey             INT             NOT NULL REFERENCES DimSucursal (SucursalKey),
    DiasLaboradosMes        INT             NOT NULL DEFAULT 0,
    DiasFalta               INT             NOT NULL DEFAULT 0,
    DiasVacacion            INT             NOT NULL DEFAULT 0,
    DiasPermiso             INT             NOT NULL DEFAULT 0,
    DiasIncapacidad         INT             NOT NULL DEFAULT 0,
    TotalHorasExtra         NUMERIC(8,2)    NOT NULL DEFAULT 0,
    TotalMinutosTardanza    INT             NOT NULL DEFAULT 0,
    TasaPuntualidad         NUMERIC(5,2),
    TasaAusentismo          NUMERIC(5,2)
);

-- Equipo 7: Compensación y Beneficios
CREATE TABLE Ref_Benchmark_Salarial (
    BenchmarkKey            INT             PRIMARY KEY,
    TiempoKey               INT             NOT NULL REFERENCES DimTiempo (TiempoKey),
    PuestoKey               INT             NOT NULL REFERENCES DimPuesto (PuestoKey),
    DepartamentoKey         INT             NOT NULL REFERENCES DimDepartamento (DepartamentoKey),
    FuenteMercado           VARCHAR(80)     NOT NULL,
    RegionMercado           VARCHAR(80),
    IndustriaMercado        VARCHAR(80),
    SalarioMercadoMin       NUMERIC(12,2),
    SalarioMercadoMed       NUMERIC(12,2)   NOT NULL,
    SalarioMercadoMax       NUMERIC(12,2),
    SalarioInternoProm      NUMERIC(12,2),
    BrechaSalarial          NUMERIC(12,2),
    IndiceCompetitividad    NUMERIC(5,2)
);

-- Equipo 8: Planificación de la Fuerza Laboral
CREATE TABLE Fact_Sucesion (
    FactSucesionKey         INT             PRIMARY KEY,
    TiempoKey               INT             NOT NULL REFERENCES DimTiempo (TiempoKey),
    EmpleadoKey             INT             NOT NULL REFERENCES DimEmpleado (EmpleadoKey),
    PuestoKey               INT             NOT NULL REFERENCES DimPuesto (PuestoKey),
    DepartamentoKey         INT             NOT NULL REFERENCES DimDepartamento (DepartamentoKey),
    HabilidadKey            INT             REFERENCES DimHabilidad (HabilidadKey),
    RolClaveCandidato       VARCHAR(80)     NOT NULL,
    BrechaHabilidad         NUMERIC(5,2),
    FlagSucesorListo        BOOLEAN         NOT NULL DEFAULT FALSE,
    CostoProyectadoReemplazo NUMERIC(12,2)
);


-- ============================================================
-- VISTAS DE CONSOLIDACIÓN (2)
-- Fase 2: se crean después de la carga
-- ============================================================

CREATE VIEW Vista_Empleado_Mensual AS
SELECT
    n.TiempoKey,
    n.EmpleadoKey,
    n.PuestoKey,
    n.DepartamentoKey,
    n.SucursalKey,
    n.TipoContrato,
    n.SalarioBase,
    n.Bono,
    n.Beneficios,
    n.CostoTotalNomina,
    n.Headcount,
    n.AntiguedadMeses,
    n.EdadActual,
    n.FlagActivo,
    n.FlagBaja,
    n.FlagNuevoIngreso,
    n.FlagJubilacionProxima,
    a.DiasLaboradosMes,
    a.DiasFalta,
    a.DiasVacacion,
    a.DiasPermiso,
    a.DiasIncapacidad,
    a.TotalHorasExtra,
    a.TotalMinutosTardanza,
    a.TasaPuntualidad,
    a.TasaAusentismo
FROM Fact_Nomina n
LEFT JOIN Fact_Asistencia a
    ON n.TiempoKey = a.TiempoKey
   AND n.EmpleadoKey = a.EmpleadoKey;

CREATE VIEW Vista_Desempeno_Completo AS
SELECT
    e.TiempoKey,
    e.EmpleadoKey,
    e.PuestoKey,
    e.DepartamentoKey,
    e.HabilidadKey,
    e.PeriodoEvaluacion,
    e.TipoEvaluacion,
    e.PuntajeDesempeno,
    e.CumplimientoObjetivos,
    e.CalificacionFinal,
    e.FlagAltoPotencial,
    s.RolClaveCandidato,
    s.BrechaHabilidad,
    s.FlagSucesorListo,
    s.CostoProyectadoReemplazo
FROM Fact_Evaluacion e
LEFT JOIN Fact_Sucesion s
    ON e.TiempoKey = s.TiempoKey
   AND e.EmpleadoKey = s.EmpleadoKey;


-- ============================================================
-- ÍNDICES
-- ============================================================

CREATE INDEX ix_fact_reclutamiento_tiempo     ON Fact_Reclutamiento (TiempoKey);
CREATE INDEX ix_fact_reclutamiento_candidato  ON Fact_Reclutamiento (CandidatoKey);
CREATE INDEX ix_fact_reclutamiento_puesto     ON Fact_Reclutamiento (PuestoKey);
CREATE INDEX ix_fact_reclutamiento_etapa      ON Fact_Reclutamiento (EtapaReclutamiento);

CREATE INDEX ix_fact_nomina_tiempo            ON Fact_Nomina (TiempoKey);
CREATE INDEX ix_fact_nomina_empleado          ON Fact_Nomina (EmpleadoKey);
CREATE INDEX ix_fact_nomina_puesto            ON Fact_Nomina (PuestoKey);
CREATE INDEX ix_fact_nomina_depto             ON Fact_Nomina (DepartamentoKey);
CREATE INDEX ix_fact_nomina_sucursal          ON Fact_Nomina (SucursalKey);

CREATE INDEX ix_fact_capacitacion_tiempo      ON Fact_Capacitacion (TiempoKey);
CREATE INDEX ix_fact_capacitacion_empleado    ON Fact_Capacitacion (EmpleadoKey);
CREATE INDEX ix_fact_capacitacion_curso       ON Fact_Capacitacion (CursoKey);

CREATE INDEX ix_fact_evaluacion_tiempo        ON Fact_Evaluacion (TiempoKey);
CREATE INDEX ix_fact_evaluacion_empleado      ON Fact_Evaluacion (EmpleadoKey);
CREATE INDEX ix_fact_evaluacion_puesto        ON Fact_Evaluacion (PuestoKey);

CREATE INDEX ix_fact_clima_tiempo             ON Fact_Clima_Bienestar (TiempoKey);
CREATE INDEX ix_fact_clima_empleado           ON Fact_Clima_Bienestar (EmpleadoKey);
CREATE INDEX ix_fact_clima_depto              ON Fact_Clima_Bienestar (DepartamentoKey);

CREATE INDEX ix_fact_asistencia_tiempo        ON Fact_Asistencia (TiempoKey);
CREATE INDEX ix_fact_asistencia_empleado      ON Fact_Asistencia (EmpleadoKey);
CREATE INDEX ix_fact_asistencia_depto         ON Fact_Asistencia (DepartamentoKey);
CREATE INDEX ix_fact_asistencia_sucursal      ON Fact_Asistencia (SucursalKey);

CREATE INDEX ix_ref_benchmark_tiempo          ON Ref_Benchmark_Salarial (TiempoKey);
CREATE INDEX ix_ref_benchmark_puesto          ON Ref_Benchmark_Salarial (PuestoKey);

CREATE INDEX ix_fact_sucesion_tiempo          ON Fact_Sucesion (TiempoKey);
CREATE INDEX ix_fact_sucesion_empleado        ON Fact_Sucesion (EmpleadoKey);
CREATE INDEX ix_fact_sucesion_puesto          ON Fact_Sucesion (PuestoKey);


-- ============================================================
-- DICCIONARIO DE DATOS (COMMENT ON)
-- Documentación nativa de PostgreSQL
-- Consultar con: \d+ nombre_tabla  ó  \dt+
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- DimTiempo
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE DimTiempo IS 'Dimensión compartida de calendario. Contiene una fila por cada día en el rango histórico (5 años). Fase 0.';
COMMENT ON COLUMN DimTiempo.TiempoKey IS 'Clave subrogada (PK). Formato sugerido: YYYYMMDD.';
COMMENT ON COLUMN DimTiempo.Fecha IS 'Fecha calendario en formato DATE.';
COMMENT ON COLUMN DimTiempo.Dia IS 'Número del día dentro del mes (1-31).';
COMMENT ON COLUMN DimTiempo.DiaSemana IS 'Nombre del día: Lunes, Martes, Miércoles, etc.';
COMMENT ON COLUMN DimTiempo.DiaDelAnio IS 'Número del día dentro del año (1-366).';
COMMENT ON COLUMN DimTiempo.Semana IS 'Número de semana ISO del año (1-53).';
COMMENT ON COLUMN DimTiempo.Mes IS 'Número del mes (1-12).';
COMMENT ON COLUMN DimTiempo.NombreMes IS 'Nombre del mes: Enero, Febrero, etc.';
COMMENT ON COLUMN DimTiempo.Trimestre IS 'Trimestre del año (1-4).';
COMMENT ON COLUMN DimTiempo.NombreTrimestre IS 'Etiqueta del trimestre: Q1, Q2, Q3, Q4.';
COMMENT ON COLUMN DimTiempo.Semestre IS 'Semestre del año (1-2).';
COMMENT ON COLUMN DimTiempo.Anio IS 'Año calendario (ej. 2025).';
COMMENT ON COLUMN DimTiempo.EsFinDeSemana IS 'TRUE si el día es sábado o domingo.';
COMMENT ON COLUMN DimTiempo.EsFestivo IS 'TRUE si el día es feriado oficial.';
COMMENT ON COLUMN DimTiempo.NombreFestivo IS 'Nombre del feriado (NULL si no aplica).';
COMMENT ON COLUMN DimTiempo.EsDiaLaboral IS 'TRUE si el día es hábil (no fin de semana ni festivo).';

-- ────────────────────────────────────────────────────────────
-- DimSucursal
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE DimSucursal IS 'Dimensión compartida de sedes y ubicaciones físicas de la organización. Incluye fila 0 = No Aplica para empresas sin sucursales. Fase 0.';
COMMENT ON COLUMN DimSucursal.SucursalKey IS 'Clave subrogada (PK). 0 = No Aplica.';
COMMENT ON COLUMN DimSucursal.IdSucursalNegocio IS 'Código identificador en el sistema fuente.';
COMMENT ON COLUMN DimSucursal.NombreSucursal IS 'Nombre descriptivo de la sede.';
COMMENT ON COLUMN DimSucursal.Direccion IS 'Dirección física completa.';
COMMENT ON COLUMN DimSucursal.Ciudad IS 'Ciudad donde se ubica la sede.';
COMMENT ON COLUMN DimSucursal.Estado IS 'Estado, provincia o región.';
COMMENT ON COLUMN DimSucursal.Pais IS 'País de la sede.';
COMMENT ON COLUMN DimSucursal.CodigoPostal IS 'Código postal de la sede.';
COMMENT ON COLUMN DimSucursal.Telefono IS 'Teléfono de contacto de la sede.';
COMMENT ON COLUMN DimSucursal.EsActiva IS 'TRUE si la sede está operativa actualmente.';

-- ────────────────────────────────────────────────────────────
-- DimEmpleado
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE DimEmpleado IS 'Dimensión compartida de colaboradores. Implementa SCD Tipo 2: cada cambio en atributos genera una nueva fila preservando el histórico. Fase 0.';
COMMENT ON COLUMN DimEmpleado.EmpleadoKey IS 'Clave subrogada (PK). Única por versión del registro.';
COMMENT ON COLUMN DimEmpleado.IdEmpleadoNegocio IS 'Código del empleado en el sistema fuente (puede repetirse en SCD Tipo 2).';
COMMENT ON COLUMN DimEmpleado.NombreCompleto IS 'Nombre y apellido concatenados.';
COMMENT ON COLUMN DimEmpleado.Nombre IS 'Nombre(s) del colaborador.';
COMMENT ON COLUMN DimEmpleado.Apellido IS 'Apellido(s) del colaborador.';
COMMENT ON COLUMN DimEmpleado.Genero IS 'Género: Masculino, Femenino, Otro, No Informado.';
COMMENT ON COLUMN DimEmpleado.FechaNacimiento IS 'Fecha de nacimiento del empleado.';
COMMENT ON COLUMN DimEmpleado.EstadoCivil IS 'Estado civil: Soltero, Casado, Divorciado, Viudo, Unión Libre.';
COMMENT ON COLUMN DimEmpleado.NivelEducativo IS 'Máximo nivel educativo: Primaria, Secundaria, Universitario, Posgrado.';
COMMENT ON COLUMN DimEmpleado.Nacionalidad IS 'País de nacionalidad del empleado.';
COMMENT ON COLUMN DimEmpleado.CorreoElectronico IS 'Correo electrónico corporativo o personal.';
COMMENT ON COLUMN DimEmpleado.Telefono IS 'Teléfono de contacto.';
COMMENT ON COLUMN DimEmpleado.FechaIngreso IS 'Fecha de ingreso a la organización.';
COMMENT ON COLUMN DimEmpleado.FechaBaja IS 'Fecha de desvinculación (NULL si sigue activo).';
COMMENT ON COLUMN DimEmpleado.MotivoBaja IS 'Razón de la baja: Renuncia, Despido, Jubilación, Fin Contrato.';
COMMENT ON COLUMN DimEmpleado.EstadoActual IS 'Estado laboral vigente: Activo, Inactivo, Baja.';
COMMENT ON COLUMN DimEmpleado.FechaInicioVigencia IS 'SCD2: fecha desde la cual esta versión del registro es válida.';
COMMENT ON COLUMN DimEmpleado.FechaFinVigencia IS 'SCD2: fecha hasta la cual esta versión es válida. NULL = registro actual.';
COMMENT ON COLUMN DimEmpleado.EsRegistroActual IS 'SCD2: TRUE si esta es la versión vigente del empleado.';

-- ────────────────────────────────────────────────────────────
-- DimPuesto
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE DimPuesto IS 'Dimensión compartida del catálogo de posiciones/cargos de la organización. Fase 0.';
COMMENT ON COLUMN DimPuesto.PuestoKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN DimPuesto.IdPuestoNegocio IS 'Código del puesto en el sistema fuente.';
COMMENT ON COLUMN DimPuesto.NombrePuesto IS 'Nombre del cargo: Analista, Gerente, Director, etc.';
COMMENT ON COLUMN DimPuesto.NivelJerarquico IS 'Nivel organizacional: Operativo, Supervisión, Gerencia, Dirección.';
COMMENT ON COLUMN DimPuesto.AreaFuncional IS 'Área a la que pertenece: Tecnología, Finanzas, Ventas, Operaciones.';
COMMENT ON COLUMN DimPuesto.BandaSalarial IS 'Banda salarial asignada: A, B, C, D o rangos numéricos.';
COMMENT ON COLUMN DimPuesto.EsRolCritico IS 'TRUE si el puesto es considerado clave para la continuidad del negocio.';
COMMENT ON COLUMN DimPuesto.Descripcion IS 'Descripción general del puesto y sus responsabilidades.';

-- ────────────────────────────────────────────────────────────
-- DimDepartamento
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE DimDepartamento IS 'Dimensión compartida de la estructura organizacional por departamentos. Soporta jerarquía mediante referencia al departamento padre. Fase 0.';
COMMENT ON COLUMN DimDepartamento.DepartamentoKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN DimDepartamento.IdDepartamentoNeg IS 'Código del departamento en el sistema fuente.';
COMMENT ON COLUMN DimDepartamento.NombreDepartamento IS 'Nombre del departamento: Tecnología, Finanzas, RRHH, etc.';
COMMENT ON COLUMN DimDepartamento.NombreGerente IS 'Nombre del gerente o responsable del departamento.';
COMMENT ON COLUMN DimDepartamento.DepartamentoPadre IS 'Nombre del departamento superior en la jerarquía.';
COMMENT ON COLUMN DimDepartamento.NivelOrganizacional IS 'Nivel en la jerarquía: 1 = Dirección, 2 = Gerencia, 3 = Área, 4 = Unidad.';

-- ────────────────────────────────────────────────────────────
-- DimHabilidad
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE DimHabilidad IS 'Dimensión compartida de competencias evaluables. Usada por Equipos 3 (Capacitación), 4 (Evaluación) y 8 (Sucesión). Fase 0.';
COMMENT ON COLUMN DimHabilidad.HabilidadKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN DimHabilidad.IdHabilidadNegocio IS 'Código de la habilidad en el sistema fuente.';
COMMENT ON COLUMN DimHabilidad.NombreHabilidad IS 'Nombre de la competencia: Liderazgo, Python, Negociación, etc.';
COMMENT ON COLUMN DimHabilidad.CategoriaHabilidad IS 'Clasificación: Técnica, Blanda, Gerencial, Idioma.';
COMMENT ON COLUMN DimHabilidad.NivelEsperado IS 'Nivel que la organización espera para esta habilidad (escala 1-5).';
COMMENT ON COLUMN DimHabilidad.Descripcion IS 'Descripción detallada de la competencia.';

-- ────────────────────────────────────────────────────────────
-- DimCandidato
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE DimCandidato IS 'Dimensión de módulo: postulantes a vacantes. Creada y mantenida por el Equipo 1 (Reclutamiento). Fase 1.';
COMMENT ON COLUMN DimCandidato.CandidatoKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN DimCandidato.IdCandidatoNegocio IS 'Código del candidato en el ATS o sistema fuente.';
COMMENT ON COLUMN DimCandidato.NombreCompleto IS 'Nombre completo del postulante.';
COMMENT ON COLUMN DimCandidato.CorreoElectronico IS 'Email de contacto del candidato.';
COMMENT ON COLUMN DimCandidato.Telefono IS 'Teléfono de contacto.';
COMMENT ON COLUMN DimCandidato.NivelEducativo IS 'Máximo nivel educativo: Primaria, Secundaria, Universitario, Posgrado.';
COMMENT ON COLUMN DimCandidato.AniosExperiencia IS 'Años de experiencia laboral declarados.';
COMMENT ON COLUMN DimCandidato.Ubicacion IS 'Ciudad o país de residencia del candidato.';
COMMENT ON COLUMN DimCandidato.HabilidadPrincipal IS 'Competencia principal declarada por el candidato.';
COMMENT ON COLUMN DimCandidato.EsInterno IS 'TRUE si es un candidato interno (empleado actual postulando a otra posición).';

-- ────────────────────────────────────────────────────────────
-- DimCurso
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE DimCurso IS 'Dimensión de módulo: catálogo de programas de formación. Creada y mantenida por el Equipo 3 (Capacitación). Fase 1.';
COMMENT ON COLUMN DimCurso.CursoKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN DimCurso.IdCursoNegocio IS 'Código del curso en el LMS o sistema fuente.';
COMMENT ON COLUMN DimCurso.NombreCurso IS 'Nombre del programa de formación.';
COMMENT ON COLUMN DimCurso.Modalidad IS 'Formato de impartición: Presencial, Virtual, Mixto.';
COMMENT ON COLUMN DimCurso.DuracionHoras IS 'Duración total del curso en horas.';
COMMENT ON COLUMN DimCurso.Proveedor IS 'Entidad que provee el curso: Interno, Coursera, Universidad X, etc.';
COMMENT ON COLUMN DimCurso.CategoriaCurso IS 'Clasificación temática: Técnico, Liderazgo, Cumplimiento, Soft Skills.';
COMMENT ON COLUMN DimCurso.NivelDificultad IS 'Nivel de complejidad: Básico, Intermedio, Avanzado.';

-- ────────────────────────────────────────────────────────────
-- Fact_Reclutamiento
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE Fact_Reclutamiento IS 'Tabla fact del Equipo 1: Reclutamiento y Selección. Grano: 1 candidato × 1 vacante × 1 etapa × 1 fecha. Registra el avance de cada candidato por las etapas del proceso de selección.';
COMMENT ON COLUMN Fact_Reclutamiento.FactReclutamientoKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN Fact_Reclutamiento.TiempoKey IS 'FK → DimTiempo. Fecha del evento en el proceso.';
COMMENT ON COLUMN Fact_Reclutamiento.CandidatoKey IS 'FK → DimCandidato. Postulante involucrado.';
COMMENT ON COLUMN Fact_Reclutamiento.PuestoKey IS 'FK → DimPuesto. Posición de la vacante.';
COMMENT ON COLUMN Fact_Reclutamiento.DepartamentoKey IS 'FK → DimDepartamento. Departamento solicitante.';
COMMENT ON COLUMN Fact_Reclutamiento.SucursalKey IS 'FK → DimSucursal. Sede donde se ubica la vacante.';
COMMENT ON COLUMN Fact_Reclutamiento.IdVacanteNegocio IS 'Atributo degenerado: código de la vacante en el sistema fuente.';
COMMENT ON COLUMN Fact_Reclutamiento.EtapaReclutamiento IS 'Atributo degenerado: fase del proceso (Aplicación, Filtro CV, Entrevista, Oferta, Contratación).';
COMMENT ON COLUMN Fact_Reclutamiento.FuenteReclutamiento IS 'Atributo degenerado: canal de origen (LinkedIn, Referido, Portal Empleo, Universidad, Agencia).';
COMMENT ON COLUMN Fact_Reclutamiento.DiasEnEtapa IS 'Medida: días que el candidato permaneció en esta etapa.';
COMMENT ON COLUMN Fact_Reclutamiento.DiasContratacionTotal IS 'Medida: días totales desde apertura de vacante hasta contratación. Solo se llena en la última etapa.';
COMMENT ON COLUMN Fact_Reclutamiento.CostoContratacion IS 'Medida: costo monetario asociado a esta contratación.';
COMMENT ON COLUMN Fact_Reclutamiento.CantidadCandidatos IS 'Medida aditiva: siempre 1, permite SUM para contar candidatos.';
COMMENT ON COLUMN Fact_Reclutamiento.FlagAvanceEtapa IS 'Flag: TRUE si el candidato avanzó a la siguiente etapa.';
COMMENT ON COLUMN Fact_Reclutamiento.FlagContratado IS 'Flag: TRUE si el candidato fue finalmente contratado.';

-- ────────────────────────────────────────────────────────────
-- Fact_Nomina
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE Fact_Nomina IS 'Tabla fact del Equipo 2: Gestión de Personal y Nómina. Grano: 1 empleado × 1 mes. Snapshot mensual de la situación laboral y compensación de cada colaborador.';
COMMENT ON COLUMN Fact_Nomina.FactNominaKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN Fact_Nomina.TiempoKey IS 'FK → DimTiempo. Primer día del mes al que corresponde el registro.';
COMMENT ON COLUMN Fact_Nomina.EmpleadoKey IS 'FK → DimEmpleado. Colaborador.';
COMMENT ON COLUMN Fact_Nomina.PuestoKey IS 'FK → DimPuesto. Puesto ocupado durante ese mes.';
COMMENT ON COLUMN Fact_Nomina.DepartamentoKey IS 'FK → DimDepartamento. Departamento asignado.';
COMMENT ON COLUMN Fact_Nomina.SucursalKey IS 'FK → DimSucursal. Sede de trabajo.';
COMMENT ON COLUMN Fact_Nomina.TipoContrato IS 'Atributo degenerado: tipo de contrato (Indefinido, Temporal, Por Obra, Practicante).';
COMMENT ON COLUMN Fact_Nomina.SalarioBase IS 'Medida: salario mensual base en moneda local.';
COMMENT ON COLUMN Fact_Nomina.Bono IS 'Medida: bonificaciones del mes.';
COMMENT ON COLUMN Fact_Nomina.Beneficios IS 'Medida: valor monetario de beneficios (seguro, transporte, alimentación).';
COMMENT ON COLUMN Fact_Nomina.CostoTotalNomina IS 'Medida: SalarioBase + Bono + Beneficios + cargas patronales.';
COMMENT ON COLUMN Fact_Nomina.Headcount IS 'Medida aditiva: siempre 1, permite SUM para contar plantilla.';
COMMENT ON COLUMN Fact_Nomina.AntiguedadMeses IS 'Medida calculada: meses desde FechaIngreso hasta el cierre del mes.';
COMMENT ON COLUMN Fact_Nomina.EdadActual IS 'Medida calculada: edad en años al cierre del mes.';
COMMENT ON COLUMN Fact_Nomina.FlagActivo IS 'Flag: TRUE si el empleado estaba activo durante ese mes.';
COMMENT ON COLUMN Fact_Nomina.FlagBaja IS 'Flag: TRUE si el empleado causó baja ese mes.';
COMMENT ON COLUMN Fact_Nomina.FlagNuevoIngreso IS 'Flag: TRUE si el empleado ingresó ese mes.';
COMMENT ON COLUMN Fact_Nomina.FlagJubilacionProxima IS 'Flag: TRUE si la edad del empleado supera el umbral de jubilación.';

-- ────────────────────────────────────────────────────────────
-- Fact_Capacitacion
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE Fact_Capacitacion IS 'Tabla fact del Equipo 3: Formación y Desarrollo. Grano: 1 empleado × 1 curso × 1 fecha. Registra la participación, costo y resultados de capacitación.';
COMMENT ON COLUMN Fact_Capacitacion.FactCapacitacionKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN Fact_Capacitacion.TiempoKey IS 'FK → DimTiempo. Fecha de la sesión o finalización del curso.';
COMMENT ON COLUMN Fact_Capacitacion.EmpleadoKey IS 'FK → DimEmpleado. Colaborador que tomó el curso.';
COMMENT ON COLUMN Fact_Capacitacion.CursoKey IS 'FK → DimCurso. Programa de formación.';
COMMENT ON COLUMN Fact_Capacitacion.DepartamentoKey IS 'FK → DimDepartamento. Departamento del empleado al momento del curso.';
COMMENT ON COLUMN Fact_Capacitacion.HabilidadKey IS 'FK → DimHabilidad. Competencia principal desarrollada por el curso.';
COMMENT ON COLUMN Fact_Capacitacion.HorasCapacitacion IS 'Medida: horas efectivas dedicadas al curso.';
COMMENT ON COLUMN Fact_Capacitacion.CostoCapacitacion IS 'Medida: costo del curso para este empleado.';
COMMENT ON COLUMN Fact_Capacitacion.PuntajePre IS 'Medida: evaluación de conocimiento antes del curso (0-100).';
COMMENT ON COLUMN Fact_Capacitacion.PuntajePost IS 'Medida: evaluación de conocimiento después del curso (0-100).';
COMMENT ON COLUMN Fact_Capacitacion.MejoraHabilidad IS 'Medida calculada: PuntajePost - PuntajePre.';
COMMENT ON COLUMN Fact_Capacitacion.FlagFinalizado IS 'Flag: TRUE si el empleado completó el curso.';

-- ────────────────────────────────────────────────────────────
-- Fact_Evaluacion
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE Fact_Evaluacion IS 'Tabla fact del Equipo 4: Evaluación del Desempeño. Grano: 1 empleado × 1 período de evaluación. Registra puntuaciones, cumplimiento de objetivos e identificación de talento.';
COMMENT ON COLUMN Fact_Evaluacion.FactEvaluacionKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN Fact_Evaluacion.TiempoKey IS 'FK → DimTiempo. Fecha de cierre de la evaluación.';
COMMENT ON COLUMN Fact_Evaluacion.EmpleadoKey IS 'FK → DimEmpleado. Colaborador evaluado.';
COMMENT ON COLUMN Fact_Evaluacion.PuestoKey IS 'FK → DimPuesto. Puesto al momento de la evaluación.';
COMMENT ON COLUMN Fact_Evaluacion.DepartamentoKey IS 'FK → DimDepartamento. Departamento al momento de la evaluación.';
COMMENT ON COLUMN Fact_Evaluacion.HabilidadKey IS 'FK → DimHabilidad. Competencia principal evaluada (NULL si evaluación global).';
COMMENT ON COLUMN Fact_Evaluacion.PeriodoEvaluacion IS 'Atributo degenerado: identificador del período (ej. Q1-2025, Anual-2024).';
COMMENT ON COLUMN Fact_Evaluacion.TipoEvaluacion IS 'Atributo degenerado: metodología aplicada (Trimestral, Anual, 360°).';
COMMENT ON COLUMN Fact_Evaluacion.PuntajeDesempeno IS 'Medida: calificación numérica del desempeño (escala 1-100 o 1-5).';
COMMENT ON COLUMN Fact_Evaluacion.CumplimientoObjetivos IS 'Medida: porcentaje de metas alcanzadas (0-100).';
COMMENT ON COLUMN Fact_Evaluacion.CalificacionFinal IS 'Medida categórica: Excelente, Bueno, Regular, Bajo.';
COMMENT ON COLUMN Fact_Evaluacion.FlagAltoPotencial IS 'Flag: TRUE si el empleado es identificado como talento de alto potencial.';

-- ────────────────────────────────────────────────────────────
-- Fact_Clima_Bienestar
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE Fact_Clima_Bienestar IS 'Tabla fact del Equipo 5: Clima Organizacional y Bienestar. Grano: 1 empleado × 1 medición × 1 período. Registra resultados de encuestas de clima y reportes de accidentes laborales.';
COMMENT ON COLUMN Fact_Clima_Bienestar.FactClimaBienestarKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN Fact_Clima_Bienestar.TiempoKey IS 'FK → DimTiempo. Fecha de la medición o reporte.';
COMMENT ON COLUMN Fact_Clima_Bienestar.EmpleadoKey IS 'FK → DimEmpleado. Colaborador encuestado o involucrado en el incidente.';
COMMENT ON COLUMN Fact_Clima_Bienestar.DepartamentoKey IS 'FK → DimDepartamento. Departamento del empleado al momento de la medición.';
COMMENT ON COLUMN Fact_Clima_Bienestar.SucursalKey IS 'FK → DimSucursal. Sede donde se realizó la medición o el incidente.';
COMMENT ON COLUMN Fact_Clima_Bienestar.TipoMedicion IS 'Atributo degenerado: tipo de registro (Encuesta Clima, Reporte Accidente, Encuesta Bienestar).';
COMMENT ON COLUMN Fact_Clima_Bienestar.PuntajeSatisfaccion IS 'Medida: nivel de satisfacción reportado (escala 1-5 o 1-10).';
COMMENT ON COLUMN Fact_Clima_Bienestar.PuntajeCompromiso IS 'Medida: nivel de compromiso/engagement reportado (escala 1-5 o 1-10).';
COMMENT ON COLUMN Fact_Clima_Bienestar.CantidadAccidentes IS 'Medida: número de accidentes laborales reportados (0 o más).';
COMMENT ON COLUMN Fact_Clima_Bienestar.FlagAccidente IS 'Flag: TRUE si hubo al menos un accidente en este registro.';

-- ────────────────────────────────────────────────────────────
-- Fact_Asistencia
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE Fact_Asistencia IS 'Tabla fact del Equipo 6: Gestión de Tiempos y Asistencia. Grano: 1 empleado × 1 mes. Resumen mensual de asistencia, puntualidad y ausencias, agregado desde registros diarios de control horario.';
COMMENT ON COLUMN Fact_Asistencia.FactAsistenciaKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN Fact_Asistencia.TiempoKey IS 'FK → DimTiempo. Primer día del mes al que corresponde el resumen.';
COMMENT ON COLUMN Fact_Asistencia.EmpleadoKey IS 'FK → DimEmpleado. Colaborador.';
COMMENT ON COLUMN Fact_Asistencia.PuestoKey IS 'FK → DimPuesto. Puesto ocupado durante ese mes.';
COMMENT ON COLUMN Fact_Asistencia.DepartamentoKey IS 'FK → DimDepartamento. Departamento asignado.';
COMMENT ON COLUMN Fact_Asistencia.SucursalKey IS 'FK → DimSucursal. Sede de trabajo.';
COMMENT ON COLUMN Fact_Asistencia.DiasLaboradosMes IS 'Medida: total de días efectivamente trabajados en el mes.';
COMMENT ON COLUMN Fact_Asistencia.DiasFalta IS 'Medida: días de ausencia no justificada.';
COMMENT ON COLUMN Fact_Asistencia.DiasVacacion IS 'Medida: días de vacaciones tomados en el mes.';
COMMENT ON COLUMN Fact_Asistencia.DiasPermiso IS 'Medida: días de permiso con goce de sueldo.';
COMMENT ON COLUMN Fact_Asistencia.DiasIncapacidad IS 'Medida: días de incapacidad médica.';
COMMENT ON COLUMN Fact_Asistencia.TotalHorasExtra IS 'Medida: horas trabajadas fuera del horario regular en el mes.';
COMMENT ON COLUMN Fact_Asistencia.TotalMinutosTardanza IS 'Medida: minutos acumulados de retraso en el mes.';
COMMENT ON COLUMN Fact_Asistencia.TasaPuntualidad IS 'Medida calculada: (días puntual / DiasLaboradosMes) × 100.';
COMMENT ON COLUMN Fact_Asistencia.TasaAusentismo IS 'Medida calculada: (DiasFalta / días laborables del mes) × 100.';

-- ────────────────────────────────────────────────────────────
-- Ref_Benchmark_Salarial
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE Ref_Benchmark_Salarial IS 'Tabla de referencia del Equipo 7: Compensación y Beneficios. Grano: 1 puesto × 1 fuente de mercado × 1 período. Datos de comparación salarial con el mercado externo.';
COMMENT ON COLUMN Ref_Benchmark_Salarial.BenchmarkKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN Ref_Benchmark_Salarial.TiempoKey IS 'FK → DimTiempo. Fecha o período de la referencia de mercado.';
COMMENT ON COLUMN Ref_Benchmark_Salarial.PuestoKey IS 'FK → DimPuesto. Posición a la que aplica el benchmark.';
COMMENT ON COLUMN Ref_Benchmark_Salarial.DepartamentoKey IS 'FK → DimDepartamento. Área organizacional de referencia.';
COMMENT ON COLUMN Ref_Benchmark_Salarial.FuenteMercado IS 'Origen de los datos: Glassdoor, Mercer, Payscale, Encuesta Sector.';
COMMENT ON COLUMN Ref_Benchmark_Salarial.RegionMercado IS 'País o zona geográfica de la referencia salarial.';
COMMENT ON COLUMN Ref_Benchmark_Salarial.IndustriaMercado IS 'Sector industrial de referencia: Tecnología, Banca, Retail, etc.';
COMMENT ON COLUMN Ref_Benchmark_Salarial.SalarioMercadoMin IS 'Medida: salario mínimo reportado por el mercado para este puesto.';
COMMENT ON COLUMN Ref_Benchmark_Salarial.SalarioMercadoMed IS 'Medida: salario mediano del mercado (referencia principal).';
COMMENT ON COLUMN Ref_Benchmark_Salarial.SalarioMercadoMax IS 'Medida: salario máximo reportado por el mercado.';
COMMENT ON COLUMN Ref_Benchmark_Salarial.SalarioInternoProm IS 'Medida: promedio salarial interno actual para ese puesto en la organización.';
COMMENT ON COLUMN Ref_Benchmark_Salarial.BrechaSalarial IS 'Medida calculada: SalarioInternoProm − SalarioMercadoMed. Positivo = por encima del mercado.';
COMMENT ON COLUMN Ref_Benchmark_Salarial.IndiceCompetitividad IS 'Medida calculada: SalarioInternoProm / SalarioMercadoMed. 1.0 = paridad con el mercado.';

-- ────────────────────────────────────────────────────────────
-- Fact_Sucesion
-- ────────────────────────────────────────────────────────────
COMMENT ON TABLE Fact_Sucesion IS 'Tabla fact del Equipo 8: Planificación de la Fuerza Laboral. Grano: 1 empleado-sucesor × 1 rol clave × 1 período. Registra la preparación de sucesores para posiciones críticas.';
COMMENT ON COLUMN Fact_Sucesion.FactSucesionKey IS 'Clave subrogada (PK).';
COMMENT ON COLUMN Fact_Sucesion.TiempoKey IS 'FK → DimTiempo. Fecha de la evaluación de sucesión.';
COMMENT ON COLUMN Fact_Sucesion.EmpleadoKey IS 'FK → DimEmpleado. Colaborador identificado como potencial sucesor.';
COMMENT ON COLUMN Fact_Sucesion.PuestoKey IS 'FK → DimPuesto. Puesto del rol clave al que podría suceder.';
COMMENT ON COLUMN Fact_Sucesion.DepartamentoKey IS 'FK → DimDepartamento. Departamento del rol clave.';
COMMENT ON COLUMN Fact_Sucesion.HabilidadKey IS 'FK → DimHabilidad. Competencia principal evaluada en el análisis de brecha.';
COMMENT ON COLUMN Fact_Sucesion.RolClaveCandidato IS 'Nombre del puesto crítico al que podría suceder: CEO, CFO, Gerente Ops, etc.';
COMMENT ON COLUMN Fact_Sucesion.BrechaHabilidad IS 'Medida: diferencia entre habilidades actuales y las requeridas para el rol (0-100).';
COMMENT ON COLUMN Fact_Sucesion.FlagSucesorListo IS 'Flag: TRUE si el empleado está listo para asumir el rol clave.';
COMMENT ON COLUMN Fact_Sucesion.CostoProyectadoReemplazo IS 'Medida: costo estimado en caso de tener que contratar un reemplazo externo.';

-- ────────────────────────────────────────────────────────────
-- Vistas de consolidación
-- ────────────────────────────────────────────────────────────
COMMENT ON VIEW Vista_Empleado_Mensual IS 'Vista de consolidación: une Fact_Nomina (Equipo 2) con Fact_Asistencia (Equipo 6) por empleado y mes. Proporciona visión integral de compensación + asistencia. LEFT JOIN preserva registros de nómina sin datos de asistencia.';
COMMENT ON VIEW Vista_Desempeno_Completo IS 'Vista de consolidación: une Fact_Evaluacion (Equipo 4) con Fact_Sucesion (Equipo 8) por empleado y período. Proporciona visión integral de desempeño + planificación de sucesión. LEFT JOIN preserva evaluaciones sin datos de sucesión.';
