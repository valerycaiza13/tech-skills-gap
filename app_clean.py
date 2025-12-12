import streamlit as st
from pathlib import Path

from skills_gap_analysis import load_data, calcular_gaps, resumen_por_rol, skills_mas_criticas, recomendaciones_formacion

st.set_page_config(page_title="Tech Skills Gap Dashboard", layout="wide")
st.title("📊 Tech Skills Gap Dashboard")
st.caption("Análisis de brechas de habilidades técnicas (Technology only)")

BASE_PATH = Path(".")

@st.cache_data
def run_analysis():
    empleados, skills_roles, skills_empleados, formaciones = load_data(BASE_PATH)
    df_gaps = calcular_gaps(empleados, skills_roles, skills_empleados)
    resumen = resumen_por_rol(df_gaps)
    criticas = skills_mas_criticas(df_gaps, top_n=10)
    recs = recomendaciones_formacion(df_gaps, formaciones)
    return empleados, df_gaps, resumen, criticas, recs

empleados, df_gaps, resumen, criticas, recs = run_analysis()

st.sidebar.header("Filtros")
roles = sorted(empleados["rol_actual"].dropna().unique())
rol_sel = st.sidebar.multiselect("Rol", options=roles, default=roles)

skills = sorted(df_gaps["skill_name"].dropna().unique())
skill_sel = st.sidebar.multiselect("Skills", options=skills, default=skills[: min(10, len(skills))])

df_f = df_gaps[df_gaps["rol_actual"].isin(rol_sel) & df_gaps["skill_name"].isin(skill_sel)].copy()

c1, c2, c3 = st.columns(3)
c1.metric("👥 Empleados", int(df_f["employee_id"].nunique()))
c2.metric("🧠 Skills", int(df_f["skill_name"].nunique()))
c3.metric("⚠️ Gap severity total", round(float(df_f["gap_severity"].sum()), 2))

st.divider()

left, right = st.columns([1, 1])
with left:
    st.subheader("📌 Resumen por rol")
    st.dataframe(resumen[resumen["rol_actual"].isin(rol_sel)], use_container_width=True)

with right:
    st.subheader("🔥 Skills más críticas (Top 10)")
    crit_f = (
        df_f.groupby("skill_name")["gap_severity"]
        .sum()
        .reset_index()
        .sort_values("gap_severity", ascending=False)
        .head(10)
    )
    st.dataframe(crit_f, use_container_width=True)

st.subheader("📈 Severidad de brechas por skill")
chart_df = (
    df_f.groupby("skill_name")["gap_severity"]
    .sum()
    .reset_index()
    .sort_values("gap_severity", ascending=False)
)

if chart_df.empty:
    st.info("No hay datos para el gráfico con los filtros actuales.")
else:
    st.bar_chart(chart_df.set_index("skill_name")[["gap_severity"]])

st.divider()

st.subheader("🧑‍💻 Detalle de gaps")
st.dataframe(
    df_f.sort_values(["rol_actual", "employee_id", "gap_severity"], ascending=[True, True, False]),
    use_container_width=True
)

st.subheader("🎓 Recomendaciones de formación (solo gaps > 0)")
recs_f = recs[recs["rol_actual"].isin(rol_sel) & recs["skill_name"].isin(skill_sel)].copy()
st.dataframe(recs_f, use_container_width=True)
