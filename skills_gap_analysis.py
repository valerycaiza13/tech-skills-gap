"""
skills_gap_analysis.py

Script para:
- Calcular brechas (gaps) de habilidades técnicas en el área de Tecnología.
- Generar resumen por rol.
- Identificar skills más críticas.
- Sugerir formaciones por empleado y skill.

Requiere los archivos CSV (en la misma carpeta o en la ruta base_path):
- empleados_tech.csv
- skills_tech_roles.csv
- skills_tech_empleados.csv
- formaciones_tech.csv
"""

from pathlib import Path
import pandas as pd


# -------------------------
# 1. Cargar datos
# -------------------------
def load_data(base_path="."):
    """
    Carga los 4 CSV necesarios desde base_path.
    """
    base = Path(base_path)

    empleados = pd.read_csv(base / "empleados_tech.csv")
    skills_roles = pd.read_csv(base / "skills_tech_roles.csv")
    skills_empleados = pd.read_csv(base / "skills_tech_empleados.csv")
    formaciones = pd.read_csv(base / "formaciones_tech.csv")

    return empleados, skills_roles, skills_empleados, formaciones


# -------------------------
# 2. Calcular gaps por empleado y skill
# -------------------------
def calcular_gaps(empleados, skills_roles, skills_empleados):
    """
    Une:
      - empleados_tech (rol_actual por employee_id)
      - skills_tech_empleados (nivel real por skill)
      - skills_tech_roles (nivel requerido por rol y skill)

    Devuelve un DataFrame con:
      employee_id, nombre, apellido, rol_actual, skill_name,
      skill_level, required_level, gap, weight, gap_severity
    """

    # Unir empleados con sus skills
    df = empleados.merge(
        skills_empleados,
        on="employee_id",
        how="left"
    )

    # Unir con el perfil ideal del rol
    df = df.merge(
        skills_roles,
        left_on=["rol_actual", "skill_name"],
        right_on=["rol", "skill_name"],
        how="left",
        suffixes=("", "_rol")
    )

    # Asegurar columnas numéricas (por si vienen como texto)
    for col in ["skill_level", "required_level", "weight"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Si falta required_level o skill_level, no podemos calcular gap -> NaN
    df["gap"] = df["required_level"] - df["skill_level"]

    # Severidad de la brecha: gap positivo * peso
    # Si falta weight, asumimos 1
    df["weight"] = df["weight"].fillna(1)

    df["gap_severity"] = df.apply(
        lambda row: (row["gap"] * row["weight"]) if pd.notna(row["gap"]) and row["gap"] > 0 else 0,
        axis=1
    )

    # Limpiar columna 'rol' duplicada (de skills_roles) si existe
    if "rol" in df.columns:
        df = df.drop(columns=["rol"])

    return df


# -------------------------
# 3. Resumen por rol y global
# -------------------------
def resumen_por_rol(df_gaps):
    """
    Crea un resumen por rol:
      - nº empleados
      - % empleados con al menos 1 gap
      - gap_severity promedio
    """

    # Empleado tiene gap si alguna de sus skills tiene gap > 0
    empleados_gap = (
        df_gaps
        .groupby("employee_id")["gap"]
        .apply(lambda x: (x > 0).any() if x.notna().any() else False)
        .reset_index(name="tiene_gap")
    )

    df_emp = df_gaps[["employee_id", "rol_actual"]].drop_duplicates()
    df_emp = df_emp.merge(empleados_gap, on="employee_id", how="left")

    resumen = (
        df_emp
        .groupby("rol_actual")
        .agg(
            n_empleados=("employee_id", "nunique"),
            n_con_gap=("tiene_gap", lambda x: (x == True).sum())
        )
        .reset_index()
    )

    resumen["porcentaje_con_gap"] = (
        resumen["n_con_gap"] / resumen["n_empleados"] * 100
    ).round(1)

    # Severidad promedio por rol
    sev_rol = (
        df_gaps.groupby("rol_actual")["gap_severity"]
        .mean()
        .reset_index(name="gap_severity_promedio")
    )

    resumen = resumen.merge(sev_rol, on="rol_actual", how="left")

    return resumen


# -------------------------
# 4. Skills más críticas
# -------------------------
def skills_mas_criticas(df_gaps, top_n=10):
    """
    Devuelve un ranking de skills con mayor severidad de brecha total.
    """
    criticas = (
        df_gaps.groupby("skill_name")["gap_severity"]
        .sum()
        .reset_index()
        .sort_values("gap_severity", ascending=False)
        .head(top_n)
    )
    return criticas


# -------------------------
# 5. Recomendaciones de formaciones
# -------------------------
def recomendaciones_formacion(df_gaps, formaciones):
    """
    Para cada empleado y skill con gap > 0,
    sugiere 1 formación (la primera que encuentre para esa skill).

    Devuelve:
      employee_id, nombre, apellido, rol_actual, skill_name,
      skill_level, required_level, gap,
      course_id, course_name, provider, duration_hours, modality
    """

    # Filtrar solo skills con gap positivo
    df_need = df_gaps[df_gaps["gap"] > 0].copy()

    if df_need.empty:
        # Devuelve un DataFrame vacío con columnas esperadas
        cols = [
            "employee_id", "nombre", "apellido", "rol_actual",
            "skill_name", "skill_level", "required_level", "gap",
            "course_id", "course_name", "provider", "duration_hours", "modality",
        ]
        return pd.DataFrame(columns=cols)

    # Asegurar duration_hours numérico (para ordenar)
    if "duration_hours" in formaciones.columns:
        formaciones["duration_hours"] = pd.to_numeric(formaciones["duration_hours"], errors="coerce")

    # Elegir una formación por skill (prioriza más corta si existe)
    if "duration_hours" in formaciones.columns:
        cursos_por_skill = (
            formaciones
            .sort_values("duration_hours", ascending=True)
            .groupby("skill_name", as_index=False)
            .head(1)
        )
    else:
        cursos_por_skill = (
            formaciones
            .groupby("skill_name", as_index=False)
            .head(1)
        )

    # Unir gaps con cursos
    df_rec = df_need.merge(
        cursos_por_skill,
        on="skill_name",
        how="left"
    )

    cols = [
        "employee_id",
        "nombre",
        "apellido",
        "rol_actual",
        "skill_name",
        "skill_level",
        "required_level",
        "gap",
        "course_id",
        "course_name",
        "provider",
        "duration_hours",
        "modality",
    ]

    # Mantener solo columnas existentes (por si un CSV no trae alguna)
    cols_exist = [c for c in cols if c in df_rec.columns]
    df_rec = df_rec[cols_exist].sort_values(["employee_id", "skill_name"])

    return df_rec


# -------------------------
# 6. Función principal (para uso como script)
# -------------------------
def main(base_path=".", output_path="./output"):
    base = Path(base_path)
    out = Path(output_path)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Cargar datos
    empleados, skills_roles, skills_empleados, formaciones = load_data(base)

    # 2. Calcular gaps
    df_gaps = calcular_gaps(empleados, skills_roles, skills_empleados)

    # 3. Resumen por rol
    resumen_rol = resumen_por_rol(df_gaps)

    # 4. Skills más críticas
    criticas = skills_mas_criticas(df_gaps, top_n=10)

    # 5. Recomendaciones de formación
    rec_formacion = recomendaciones_formacion(df_gaps, formaciones)

    # 6. Guardar resultados
    df_gaps.to_csv(out / "gaps_detalle_por_empleado_skill.csv", index=False)
    resumen_rol.to_csv(out / "resumen_gaps_por_rol.csv", index=False)
    criticas.to_csv(out / "skills_mas_criticas.csv", index=False)
    rec_formacion.to_csv(out / "recomendaciones_formacion.csv", index=False)

    print("✅ Análisis completado.")
    print(f"- Detalle de gaps: {out / 'gaps_detalle_por_empleado_skill.csv'}")
    print(f"- Resumen por rol: {out / 'resumen_gaps_por_rol.csv'}")
    print(f"- Skills críticas: {out / 'skills_mas_criticas.csv'}")
    print(f"- Recomendaciones formación: {out / 'recomendaciones_formacion.csv'}")


if __name__ == "__main__":
    main()
