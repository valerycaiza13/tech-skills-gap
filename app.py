
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from pathlib import Path

from skills_gap_analysis import load_data, calcular_gaps, resumen_por_rol, skills_mas_criticas, recomendaciones_formacion

st.set_page_config(page_title="Tech Skills Gap Dashboard", layout="wide")

st.title("📊 Tech Skills Gap Dashboard")
st.caption("Brechas de habilidades técnicas (Technology only) usando CSV demo.")

BASE_PATH = Path(".")  # tus CSV están en la misma carpeta

@st.cache_data
def run_analysis():
    empleados, skills_roles, skills_empleados, formaciones = load_data(BASE_PATH)
    df_gaps = calcular_gaps(empleados, skills_roles, skills_empleados)
    resumen = resumen_por_rol(df_gaps)
    criticas = skills_mas_criticas(df_gaps, top_n=10)
    recs = recomendaciones_formacion(df_gaps, formaciones)
    return empleados, df_gaps, resumen, criticas, recs

try:
    empleados, df_gaps, resumen, criticas, recs = run_analysis()
except Exception as e:
    st.error("No pude cargar/analizar los datos. Revisa que los CSV estén en la misma carpeta que app.py.")
    st.exception(e)
    st.stop()

# Sidebar filtros
st.sidebar.header("Filtros")
roles = sorted(empleados["rol_actual"].dropna().unique())
rol_sel = st.sidebar.multiselect("Rol", options=roles, default=roles)

skills = sorted(df_gaps["skill_name"].dropna().unique())
skill_sel = st.sidebar.multiselect("Skills", options=skills, default=skills[:min(10, len(skills))])

df_f = df_gaps[
    df_gaps["rol_actual"].isin(rol_sel) &
    df_gaps["skill_name"].isin(skill_sel)
].copy()

# KPIs
col1, col2, col3 = st.columns(3)
col1.metric("Empleados (filtrado)", int(df_f["employee_id"].nunique()))
col2.metric("Skills (filtrado)", int(df_f["skill_name"].nunique()))
col3.metric("Gap severity total", float(df_f["gap_severity"].sum().round(2)))

st.divider()

left, right = st.columns([1, 1])

with left:
    st.subheader("📌 Resumen por rol")
    st.dataframe(resumen[resumen["rol_actual"].isin(rol_sel)], use_container_width=True)

    st.subheader("🔥 Skills más críticas (Top 10)")
    crit_f = (
        df_f.groupby("skill_name")["gap_severity"].sum()
        .reset_index()
        .sort_values("gap_severity", ascending=False)
        .head(10)
    )
    st.dataframe(crit_f, use_container_width=True)

with right:
    st.subheader("📈 Severidad por skill (gap severity)")
    chart_df = (
        df_f.groupby("skill_name")["gap_severity"].sum()
        .reset_index()
        .sort_values("gap_severity", ascending=True)
    )
    fig = plt.figure()
    plt.barh(chart_df["skill_name"], chart_df["gap_severity"])
    plt.xlabel("Gap Severity (sum)")
    plt.ylabel("Skill")
    st.pyplot(fig, clear_figure=True)

st.divider()

st.subheader("🧑‍💻 Detalle de gaps (filtrado)")
st.dataframe(
    df_f.sort_values(["rol_actual", "employee_id", "gap_severity"], ascending=[True, True, False]),
    use_container_width=True
)

st.subheader("🎓 Recomendaciones de formación (solo gaps > 0)")
recs_f = recs[recs["rol_actual"].isin(rol_sel) & recs["skill_name"].isin(skill_sel)].copy()
st.dataframe(recs_f, use_container_width=True)
