"""Partie 4 : Application & Interface (Streamlit) - Energy Management System.

Lancer :  streamlit run app.py

L'application regroupe les 5 parties du projet :
1. Données & EDA        (clean_data.csv)
2. Prévision            (models/forecast_h15.joblib, forecast_h24.joblib)
3. Anomalies & profils  (anomaly_results.csv, random_forest_optimized.pkl)
4. Optimisation & CO2   (energy_optimization.py, paramètres modifiables)

Les fichiers sont cherchés automatiquement dans le dossier du projet, donc
l'application fonctionne même si l'arborescence n'est pas parfaite.
"""
import importlib.util
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
LOAD_ORDER = ["Light_Load", "Medium_Load", "Maximum_Load"]
LOAD_FR = {"Light_Load": "Charge légère", "Medium_Load": "Charge moyenne",
           "Maximum_Load": "Charge max."}
CLASS_NAMES = {0: "Light_Load", 1: "Medium_Load", 2: "Maximum_Load"}

# Thème glassmorphism sombre (voir theme.py)
from theme import TEAL, VIOLET, CYAN, RED, apply_theme, brand
from auth import login_gate, logout_button
px.defaults.template = "ems_glass"
px.defaults.color_discrete_sequence = [TEAL, VIOLET, CYAN, "#f5b94a", RED, "#6c7a89"]


# --------------------------------------------------------------------------- #
# Utilitaires : retrouver les fichiers et importer les modules du projet
# --------------------------------------------------------------------------- #
def locate(*names):
    """Retourne le premier fichier trouvé (le moins profond) parmi `names`."""
    found = []
    for name in names:
        found += [p for p in ROOT.rglob(name) if p.is_file()]
    return min(found, key=lambda p: len(p.parts)) if found else None


@st.cache_resource(show_spinner=False)
def import_project_module(alias, *filenames):
    path = locate(*filenames)
    if path is None:
        return None
    spec = importlib.util.spec_from_file_location(alias, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def need(path, label):
    """Arrête la page avec un message clair si un fichier manque."""
    if path is None:
        st.error(f"Fichier introuvable : {label}. Vérifie qu'il est dans le dossier du projet.")
        st.stop()
    return path


@st.cache_data(show_spinner="Chargement des données...")
def load_clean(path):
    return pd.read_csv(path, parse_dates=["date"])


@st.cache_data(show_spinner="Chargement des anomalies...")
def load_anomalies(path):
    return pd.read_csv(path, parse_dates=["date"])


@st.cache_resource(show_spinner=False)
def load_model(path):
    return joblib.load(path)


def show_image(*names, caption=None):
    p = locate(*names)
    if p:
        st.image(str(p), caption=caption, use_container_width=True)


# --------------------------------------------------------------------------- #
# Page 1 : Données & EDA (Partie 1)
# --------------------------------------------------------------------------- #
def page_data():
    st.header("1. Données & analyse exploratoire")
    df = load_clean(need(locate("clean_data.csv"), "clean_data.csv"))

    d0, d1 = df["date"].min().date(), df["date"].max().date()
    c1, c2 = st.columns([2, 2])
    rng = c1.date_input("Période", value=(d0, d1), min_value=d0, max_value=d1)
    loads = c2.multiselect("Type de charge", LOAD_ORDER, default=LOAD_ORDER,
                           format_func=lambda x: LOAD_FR[x])
    if isinstance(rng, (tuple, list)) and len(rng) == 2:
        df = df[(df["date"].dt.date >= rng[0]) & (df["date"].dt.date <= rng[1])]
    df = df[df["Load_Type"].isin(loads)]
    if df.empty:
        st.warning("Aucune donnée pour ce filtre.")
        return

    k = st.columns(4)
    k[0].metric("Consommation totale", f"{df['Usage_kWh'].sum() / 1000:,.0f} MWh")
    k[1].metric("Moyenne / 15 min", f"{df['Usage_kWh'].mean():.1f} kWh")
    k[2].metric("Pic / 15 min", f"{df['Usage_kWh'].max():.1f} kWh")
    k[3].metric("CO₂ enregistré", f"{df['CO2(tCO2)'].sum():,.0f} t")

    st.subheader("Consommation dans le temps")
    freq = st.radio("Agrégation", ["15 min", "Heure", "Jour"], index=2, horizontal=True)
    rule = {"15 min": None, "Heure": "h", "Jour": "D"}[freq]
    s = df.set_index("date")["Usage_kWh"]
    s = s if rule is None else s.resample(rule).sum()
    fig = go.Figure(go.Scattergl(x=s.index, y=s.values, mode="lines", line=dict(color=TEAL, width=2),
                                fill="tozeroy", fillcolor="rgba(46,230,166,.10)"))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="kWh")
    st.plotly_chart(fig, use_container_width=True, theme=None)

    a, b = st.columns(2)
    with a:
        st.subheader("Profil horaire moyen")
        prof = df.groupby(["hour", "WeekStatus"])["Usage_kWh"].mean().reset_index()
        fig = px.line(prof, x="hour", y="Usage_kWh", color="WeekStatus",
                      labels={"Usage_kWh": "kWh / 15 min", "hour": "Heure"})
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True, theme=None)
    with b:
        st.subheader("Répartition des types de charge")
        rep = df["Load_Type"].value_counts().reindex(LOAD_ORDER).dropna().reset_index()
        rep.columns = ["Load_Type", "intervalles"]
        rep["Load_Type"] = rep["Load_Type"].map(LOAD_FR)
        fig = px.pie(rep, names="Load_Type", values="intervalles", hole=0.4)
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    st.subheader("Corrélations")
    num = ["Usage_kWh", "Lagging_Current_Reactive.Power_kVarh", "Leading_Current_Reactive_Power_kVarh",
           "CO2(tCO2)", "Lagging_Current_Power_Factor", "Leading_Current_Power_Factor", "NSM"]
    corr = df[num].corr().round(2)
    fig = px.imshow(corr, text_auto=True, color_continuous_scale=[[0, VIOLET], [0.5, "#0d1424"], [1, TEAL]], zmin=-1, zmax=1, aspect="auto")
    fig.update_layout(height=450, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True, theme=None)

    with st.expander("Aperçu des données"):
        st.dataframe(df.head(500), use_container_width=True)


# --------------------------------------------------------------------------- #
# Page 2 : Prévision (Partie 2)
# --------------------------------------------------------------------------- #
def page_forecast():
    st.header("2. Prévision de la consommation")
    fc = import_project_module("forecasting", "forecasting.py")
    metrics_path = locate("forecast_metrics.json")
    if fc is None or metrics_path is None:
        st.error("forecasting.py ou forecast_metrics.json introuvable. "
                 "Lance d'abord : python modules/forecasting.py data/clean_data.csv models results")
        st.stop()
    met = json.loads(metrics_path.read_text(encoding="utf-8"))

    horizon = st.radio("Horizon de prévision", ["15 min", "24 h"], horizontal=True)
    key = "H15" if horizon == "15 min" else "H24"
    m = met[key]

    rows = [{"Modèle": "Random Forest", **m["random_forest"]},
            {"Modèle": f"Naïf ({m['naif_definition']})", **m["naif"]}]
    st.dataframe(pd.DataFrame(rows).set_index("Modèle"), use_container_width=True)
    gain = (1 - m["random_forest"]["MAE"] / m["naif"]["MAE"]) * 100
    st.caption(f"Erreur (MAE) réduite de {gain:.0f} % par rapport au modèle naïf. "
               f"Test : {m['test_start'][:10]} → {m['test_end'][:10]} ({m['n_test']} points).")

    model = load_model(need(locate(f"forecast_{key.lower()}.joblib"), f"forecast_{key.lower()}.joblib"))
    raw = load_clean(need(locate("clean_data.csv"), "clean_data.csv")).sort_values("date")
    feats = m["features"]
    data = fc.add_features(raw).dropna(subset=feats + [fc.TARGET])
    data = data[data["date"] >= pd.Timestamp(m["test_start"])].reset_index(drop=True)

    t0, t1 = data["date"].min().date(), data["date"].max().date()
    day = st.date_input("Choisir un jour à prévoir", value=t0, min_value=t0, max_value=t1)
    nd = st.slider("Nombre de jours affichés", 1, 7, 2)
    start = pd.Timestamp(day)
    sel = data[(data["date"] >= start) & (data["date"] < start + pd.Timedelta(days=nd))].copy()
    if sel.empty:
        st.warning("Pas de données pour cette période.")
        return
    sel["pred"] = model.predict(sel[feats])
    mae = float(np.abs(sel[fc.TARGET] - sel["pred"]).mean())

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sel["date"], y=sel[fc.TARGET], name="Réel", line=dict(color=TEAL)))
    fig.add_trace(go.Scatter(x=sel["date"], y=sel["pred"], name="Prévu", line=dict(color=VIOLET)))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), yaxis_title="kWh / 15 min",
                      title=f"Réel vs prévu : MAE sur la période = {mae:.2f} kWh")
    st.plotly_chart(fig, use_container_width=True, theme=None)

    st.subheader("Variables les plus importantes")
    imp = pd.Series(m["importances"]).sort_values()
    fig = px.bar(imp, orientation="h", labels={"value": "Importance", "index": ""})
    fig.update_layout(height=320, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True, theme=None)

    if "modele_initial_P2" in met:
        r = met["modele_initial_P2"]["random_forest"]
        st.info(f"Modèle initial (mesures électriques simultanées) : R² = {r['R2']}. "
                "Score très élevé car il utilise le CO₂ et la puissance réactive du même "
                "intervalle : c'est une estimation, pas une vraie prévision. "
                "Les modèles ci-dessus n'utilisent que des informations disponibles à l'avance.")
    show_image("forecast_actual_vs_pred.png")


# --------------------------------------------------------------------------- #
# Page 3 : Anomalies & classification (Partie 3)
# --------------------------------------------------------------------------- #
def page_anomalies():
    st.header("3. Détection d'anomalies & classification des profils")
    an = load_anomalies(need(locate("anomaly_results.csv"), "anomaly_results.csv"))
    tab1, tab2 = st.tabs(["Anomalies (Isolation Forest)", "Classification des profils"])

    with tab1:
        total = len(an)
        n_h = int((an["type_anomaly"] == "Hausse").sum())
        n_b = int((an["type_anomaly"] == "Baisse").sum())
        k = st.columns(4)
        k[0].metric("Relevés analysés", f"{total:,}")
        k[1].metric("Anomalies", f"{n_h + n_b:,}", f"{(n_h + n_b) / total * 100:.1f} %", delta_color="off")
        k[2].metric("Hausses", f"{n_h:,}")
        k[3].metric("Baisses", f"{n_b:,}")

        types = st.multiselect("Types d'anomalies affichés", ["Hausse", "Baisse"], default=["Hausse", "Baisse"])
        d0, d1 = an["date"].min().date(), an["date"].max().date()
        rng = st.date_input("Période", value=(d0, d1), min_value=d0, max_value=d1, key="anom_rng")
        view = an
        if isinstance(rng, (tuple, list)) and len(rng) == 2:
            view = an[(an["date"].dt.date >= rng[0]) & (an["date"].dt.date <= rng[1])]

        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=view["date"], y=view["Usage_kWh"], mode="lines", name="Consommation",
                                   line=dict(color="rgba(232,238,248,.35)", width=1)))
        colors = {"Hausse": RED, "Baisse": TEAL}
        for t in types:
            sub = view[view["type_anomaly"] == t]
            fig.add_trace(go.Scattergl(x=sub["date"], y=sub["Usage_kWh"], mode="markers", name=t,
                                       marker=dict(color=colors[t], size=6)))
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="kWh / 15 min")
        st.plotly_chart(fig, use_container_width=True, theme=None)

        a, b = st.columns(2)
        with a:
            st.subheader("Anomalies par heure")
            byh = an[an["type_anomaly"] != "Normal"].groupby(["hour", "type_anomaly"]).size().reset_index(name="n")
            fig = px.bar(byh, x="hour", y="n", color="type_anomaly", color_discrete_map=colors,
                         labels={"n": "Nombre", "hour": "Heure", "type_anomaly": ""})
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True, theme=None)
        with b:
            st.subheader("Top 15 des anomalies les plus fortes")
            top = an[an["type_anomaly"] != "Normal"].nlargest(15, "anomaly_score")
            st.dataframe(top[["date", "Usage_kWh", "anomaly_score", "type_anomaly"]].round(3),
                         use_container_width=True, hide_index=True)

        # Livrables d'origine du dossier detection-classification (inchangés)
        st.subheader("Résultats de la détection (dossier detection-classification)")
        g1, g2 = st.columns(2)
        with g1:
            show_image("graphe_1_timeline.png", caption="Timeline des anomalies")
            show_image("graphe_3_baisse_par_heure.png", caption="Anomalies de baisse par heure")
        with g2:
            show_image("graphe_2_hausse_par_heure.png", caption="Anomalies de hausse par heure")
            show_image("graphe4_distribution.png", caption="Distribution normal / hausse / baisse")

    with tab2:
        model_p = locate("random_forest_optimized.pkl")
        feats_p = locate("classification_features.pkl")
        if model_p is None or feats_p is None:
            st.warning("Modèle de classification introuvable.")
        else:
            clf, feats = load_model(model_p), load_model(feats_p)
            st.write("Choisis un relevé : le modèle prédit son profil de charge "
                     "(légère, moyenne ou maximale) et on compare avec la vraie valeur.")
            c1, c2 = st.columns(2)
            day = c1.date_input("Jour", value=an["date"].iloc[500].date(),
                                min_value=an["date"].min().date(), max_value=an["date"].max().date(),
                                key="clf_day")
            day_df = an[an["date"].dt.date == day]
            if day_df.empty:
                st.warning("Pas de données ce jour-là.")
            else:
                pred = clf.predict(day_df[feats])
                out = pd.DataFrame({
                    "Heure": day_df["date"].dt.strftime("%H:%M").values,
                    "Consommation (kWh)": day_df["Usage_kWh"].values,
                    "Profil réel": day_df["Load_Type_encoded"].map(CLASS_NAMES).values,
                    "Profil prédit": [CLASS_NAMES[int(p)] for p in pred],
                })
                acc = float((out["Profil réel"] == out["Profil prédit"]).mean() * 100)
                c2.metric("Précision ce jour-là", f"{acc:.1f} %")
                fig = px.scatter(out, x="Heure", y="Consommation (kWh)", color="Profil prédit",
                                 category_orders={"Profil prédit": LOAD_ORDER})
                fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True, theme=None)
                st.dataframe(out, use_container_width=True, hide_index=True)
            a, b = st.columns(2)
            with a:
                show_image("confusion_matrix_classification.png")
            with b:
                show_image("classification_metrics.png")
            c, d = st.columns(2)
            with c:
                show_image("feature_importance_optimized.png")
            with d:
                show_image("distribution_profiles.png")


# --------------------------------------------------------------------------- #
# Page 4 : Optimisation & CO2 (Partie 5)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Calcul des scénarios...")
def run_scenarios(path, tariffs, shift_share, standby_thr, standby_red, eff_gain, pf_target):
    eo = import_project_module("energy_optimization", "energy_optimization.py", "energy_optimization (1).py")
    df = eo.load_data(str(path))
    p = eo.Params(price=dict(zip(LOAD_ORDER, tariffs)), shift_share=shift_share,
                  standby_threshold_kwh=standby_thr, standby_reduction=standby_red,
                  efficiency_gain=eff_gain, pf_target=pf_target)
    res = eo.run_all(df, p, with_drivers=False, with_sensitivity=False)
    res.pop("params", None)
    return res


def page_optimization():
    st.header("4. Optimisation énergétique & analyse CO₂")  # (4 pages + saisie en bas du menu)
    path = need(locate("clean_data.csv"), "clean_data.csv")
    if import_project_module("energy_optimization", "energy_optimization.py",
                             "energy_optimization (1).py") is None:
        st.error("energy_optimization.py introuvable.")
        st.stop()

    with st.sidebar:
        st.markdown("### Hypothèses")
        t_l = st.number_input("Prix Light_Load (€/kWh)", 0.01, 1.0, 0.06, 0.01)
        t_m = st.number_input("Prix Medium_Load (€/kWh)", 0.01, 1.0, 0.09, 0.01)
        t_x = st.number_input("Prix Maximum_Load (€/kWh)", 0.01, 1.0, 0.13, 0.01)
        shift = st.slider("Part de charge déplaçable (%)", 0, 30, 10) / 100
        sb_thr = st.slider("Seuil de consommation à vide (kWh/15 min)", 1.0, 12.0, 6.0, 0.5)
        sb_red = st.slider("Réduction de la consommation à vide (%)", 0, 50, 20) / 100
        eff = st.slider("Gain d'efficacité des process (%)", 0, 10, 3) / 100
        pf_t = st.slider("Facteur de puissance cible (%)", 90, 100, 95)
        st.caption("Les tarifs et pourcentages sont des hypothèses illustratives.")

    r = run_scenarios(str(path), (t_l, t_m, t_x), shift, sb_thr, sb_red, eff, float(pf_t))
    scen = {"Décalage de charge": r["shift"], "Efficacité process": r["efficiency"],
            "Facteur de puissance": r["power_factor"], "Consommation à vide": r["standby"]}
    tot_cost = sum(v["cost_saved"] for v in scen.values())
    tot_kwh = sum(v["kwh_saved"] for v in scen.values())
    tot_co2 = sum(v["co2_saved_t"] for v in scen.values())

    k = st.columns(4)
    k[0].metric("Coût énergie actuel", f"{r['baseline_cost']:,.0f} €")
    k[1].metric("Gain total estimé", f"{tot_cost:,.0f} €", f"{tot_cost / r['baseline_cost'] * 100:.1f} %", delta_color="off")
    k[2].metric("Énergie évitée", f"{tot_kwh / 1000:,.1f} MWh")
    k[3].metric("CO₂ évité", f"{tot_co2:,.1f} t")
    st.caption("Total approximatif : les scénarios sont supposés indépendants.")

    st.subheader("Actions recommandées")
    st.dataframe(r["recommendations"], use_container_width=True, hide_index=True)

    gains = pd.DataFrame({"Scénario": list(scen.keys()),
                          "Gain (€/an)": [v["cost_saved"] for v in scen.values()]})
    fig = px.bar(gains.sort_values("Gain (€/an)"), x="Gain (€/an)", y="Scénario", orientation="h")
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True, theme=None)

    st.subheader("Analyse du CO₂")
    c = st.columns(3)
    c[0].metric("CO₂ enregistré", f"{r['co2']['co2_recorded_t']:,.0f} t")
    c[1].metric("CO₂ estimé", f"{r['co2']['co2_estimated_t']:,.0f} t")
    c[2].metric("Facteur d'émission", f"{r['co2']['ef_kg_per_kwh']:.3f} kgCO₂/kWh")

    a, b = st.columns(2)
    with a:
        g = r["co2_load"].reset_index()
        g["Load_Type"] = g["Load_Type"].map(LOAD_FR)
        fig = px.bar(g, x="Load_Type", y=["time_share_pct", "co2_share_pct"], barmode="group",
                     labels={"value": "%", "Load_Type": "", "variable": ""},
                     title="Part du temps vs part du CO₂")
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True, theme=None)
    with b:
        h = r["co2_hour"].reset_index()
        fig = px.line(h, x="hour", y=[c for c in h.columns if c != "hour"],
                      labels={"value": "kgCO₂ / h", "hour": "Heure", "variable": ""},
                      title="CO₂ moyen par heure")
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True, theme=None)

    m = r["co2_month"].reset_index()
    fig = px.bar(m, x="month", y="co2_t", labels={"co2_t": "tCO₂", "month": "Mois"},
                 title="CO₂ par mois")
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True, theme=None)

    with st.expander("Graphiques du rapport (Partie 5)"):
        show_image("co2_analysis.png")
        show_image("drivers.png")
        show_image("optimization.png")


# --------------------------------------------------------------------------- #
# Page 5 : Nouvelles données (saisie manuelle / import de fichier)
# --------------------------------------------------------------------------- #
def _commit_rows(clean_path, rows):
    """Ajoute les lignes, vide les caches et recalcule les anomalies."""
    import data_entry as de
    added, replaced = de.append_rows(clean_path, rows)
    with st.spinner("Recalcul des anomalies..."):
        try:
            msg = de.refresh_anomalies(ROOT, clean_path)
        except Exception as e:  # le modèle d'anomalies ne doit pas bloquer l'ajout
            msg = f"Anomalies non recalculées : {e}"
    st.cache_data.clear()
    st.session_state["entry_msg"] = (
        f"{added} relevé(s) ajouté(s), {replaced} remplacé(s) (même date). {msg}")
    st.rerun()


def page_new_data():
    import data_entry as de
    st.header("➕ Entrer de nouvelles données")
    clean_path = need(locate("clean_data.csv"), "clean_data.csv")
    cur = pd.read_csv(clean_path, usecols=["date", "Usage_kWh"], parse_dates=["date"])
    ref = load_clean(clean_path)

    if "entry_msg" in st.session_state:
        st.success(st.session_state.pop("entry_msg"))

    k = st.columns(3)
    k[0].metric("Relevés dans l'application", f"{len(cur):,}")
    k[1].metric("Premier relevé", cur["date"].min().strftime("%d/%m/%Y %H:%M"))
    k[2].metric("Dernier relevé", cur["date"].max().strftime("%d/%m/%Y %H:%M"))
    n_gaps = de.gaps(clean_path)
    if n_gaps:
        st.warning(f"{n_gaps} intervalle(s) différent(s) de 15 min dans les données. "
                   "La prévision et les anomalies utilisent des retards (15 min, 1 h, 24 h) "
                   "et sont moins fiables autour de ces trous.")

    tab1, tab2, tab3 = st.tabs(["Saisir un relevé", "Importer un fichier", "Gérer les données"])

    # ---- Saisie manuelle -------------------------------------------------- #
    with tab1:
        st.caption("Un relevé = 15 minutes. Les autres colonnes (facteurs de puissance, NSM, jour, "
                   "CO₂, type de charge...) sont calculées automatiquement.")
        nxt = cur["date"].max() + pd.Timedelta(minutes=15)
        with st.form("form_releve", clear_on_submit=False):
            c1, c2 = st.columns(2)
            day = c1.date_input("Date", value=nxt.date())
            hour = c2.time_input("Heure", value=nxt.time(), step=900)
            c3, c4, c5 = st.columns(3)
            kwh = c3.number_input("Consommation Usage_kWh", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            lag = c4.number_input("Réactif inductif (kVarh)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            lead = c5.number_input("Réactif capacitif (kVarh)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
            c6, c7 = st.columns(2)
            co2 = c6.number_input("CO₂ (tCO₂), 0 = estimer automatiquement", min_value=0.0, value=0.0, step=0.01, format="%.2f")
            lt = c7.selectbox("Type de charge", ["Automatique"] + LOAD_ORDER,
                              format_func=lambda x: x if x == "Automatique" else LOAD_FR[x])
            ok = st.form_submit_button("Ajouter ce relevé", type="primary")
        if ok:
            row = pd.DataFrame([{
                "date": pd.Timestamp.combine(day, hour), "Usage_kWh": kwh,
                "Lagging_Current_Reactive.Power_kVarh": lag, "Leading_Current_Reactive_Power_kVarh": lead,
                "CO2(tCO2)": co2 if co2 > 0 else np.nan,
                "Load_Type": None if lt == "Automatique" else lt}])
            try:
                full, notes = de.complete(row, ref)
            except ValueError as e:
                st.error(str(e))
            else:
                for n in notes:
                    st.info(n)
                _commit_rows(clean_path, full)

    # ---- Import de fichier ------------------------------------------------ #
    with tab2:
        st.write("Colonnes : **date** et **Usage_kWh** obligatoires ; optionnelles : "
                 "`Lagging_Current_Reactive.Power_kVarh`, `Leading_Current_Reactive_Power_kVarh`, "
                 "`CO2(tCO2)`, `Load_Type`. Un fichier au format complet de `clean_data.csv` fonctionne aussi.")
        st.download_button("Télécharger un modèle CSV", de.template_csv(), "modele_nouvelles_donnees.csv", "text/csv")
        up = st.file_uploader("Fichier CSV ou Excel", type=["csv", "xlsx"])
        if up is not None:
            try:
                raw = pd.read_excel(up) if up.name.lower().endswith(".xlsx") else pd.read_csv(up, sep=None, engine="python")
                full, notes = de.complete(raw, ref)
            except Exception as e:
                st.error(f"Fichier inutilisable : {e}")
            else:
                for n in notes:
                    st.info(n)
                overl = int(full["date"].isin(cur["date"]).sum())
                st.write(f"**{len(full):,} relevé(s)** du {full['date'].min():%d/%m/%Y %H:%M} "
                         f"au {full['date'].max():%d/%m/%Y %H:%M}"
                         + (f" dont {overl} remplaceront des relevés existants." if overl else "."))
                st.dataframe(full.head(200), use_container_width=True, hide_index=True)
                if st.button("Ajouter ces relevés à l'application", type="primary"):
                    _commit_rows(clean_path, full)

    # ---- Gestion ---------------------------------------------------------- #
    with tab3:
        origin, previous = de._paths(clean_path)
        st.write("Chaque ajout garde une copie de sécurité.")
        a, b = st.columns(2)
        if a.button("Annuler le dernier ajout", disabled=not previous.exists()):
            de.restore(clean_path, "previous")
            de.refresh_anomalies(ROOT, clean_path)
            st.cache_data.clear()
            st.session_state["entry_msg"] = "Dernier ajout annulé."
            st.rerun()
        if b.button("Revenir aux données d'origine", disabled=not origin.exists()):
            de.restore(clean_path, "origin")
            de.refresh_anomalies(ROOT, clean_path)
            st.cache_data.clear()
            st.session_state["entry_msg"] = "Données d'origine restaurées."
            st.rerun()
        st.caption("Les modèles de prévision (forecast_h15 / h24) ne sont pas ré-entraînés : "
                   "ils prévoient à partir des nouvelles données. Pour les ré-entraîner : "
                   "python modules/forecasting.py data/clean_data.csv models results")


# --------------------------------------------------------------------------- #
# Écran de démarrage : importer le fichier de données (juste après la connexion)
# --------------------------------------------------------------------------- #
MIN_ROWS = 100  # les lags (jusqu'à 24 h = 96 relevés) exigent un minimum de données


def page_start():
    import data_entry as de
    clean_path = need(locate("clean_data.csv"), "clean_data.csv")
    st.header("📂 Importer votre fichier de données")
    st.write("Charge le fichier qui contient tes données : toutes les pages "
             "(données, prévision, anomalies, optimisation) s'afficheront à partir de ce fichier.")
    st.caption("Colonnes : **date** et **Usage_kWh** obligatoires ; optionnelles : "
               "`Lagging_Current_Reactive.Power_kVarh`, `Leading_Current_Reactive_Power_kVarh`, "
               "`CO2(tCO2)`, `Load_Type`. Un fichier au format de `clean_data.csv` fonctionne aussi. "
               f"Minimum {MIN_ROWS} relevés (un relevé = 15 min).")
    st.download_button("Télécharger un modèle CSV", de.template_csv(), "modele_nouvelles_donnees.csv", "text/csv")

    n_cur = len(pd.read_csv(clean_path, usecols=["date"]))
    mode = st.radio("Que faire des données ?",
                    ["Remplacer toutes les données par ce fichier",
                     f"Ajouter ce fichier aux données existantes ({n_cur:,} relevés)"],
                    key="start_mode")
    replace = mode.startswith("Remplacer")
    save_old = False
    if replace:
        save_old = st.checkbox("Enregistrer les données actuelles avant de les remplacer", value=True,
                               help="Une copie est gardée dans data/archives/ et tu peux la recharger plus tard.")
        arch_name = st.text_input("Nom de cette sauvegarde (facultatif)", placeholder="ex: janvier_2019",
                                  disabled=not save_old)

    up = st.file_uploader("Fichier CSV ou Excel", type=["csv", "xlsx"], key="start_upload")
    if up is not None:
        ref = load_clean(clean_path)
        try:
            raw = pd.read_excel(up) if up.name.lower().endswith(".xlsx") else pd.read_csv(up, sep=None, engine="python")
            full, notes = de.complete(raw, ref)
            if replace and len(full) < MIN_ROWS:
                raise ValueError(f"Seulement {len(full)} relevé(s) : il en faut au moins {MIN_ROWS}.")
        except Exception as e:
            st.error(f"Fichier inutilisable : {e}")
        else:
            for n in notes:
                st.info(n)
            st.write(f"**{len(full):,} relevé(s)** du {full['date'].min():%d/%m/%Y %H:%M} "
                     f"au {full['date'].max():%d/%m/%Y %H:%M}.")
            st.dataframe(full.head(100), use_container_width=True, hide_index=True)
            if st.button("Charger ces données et ouvrir l'application", type="primary"):
                with st.spinner("Chargement et calcul des anomalies..."):
                    if replace:
                        if save_old:
                            de.archive_current(clean_path, arch_name)
                        de.replace_all(clean_path, full)
                    else:
                        de.append_rows(clean_path, full)
                    try:
                        msg = de.refresh_anomalies(ROOT, clean_path)
                    except Exception as e:
                        msg = f"Anomalies non recalculées : {e}"
                st.cache_data.clear()
                st.session_state["data_ready"] = True
                st.session_state["entry_msg"] = f"{len(full):,} relevés chargés depuis « {up.name} ». {msg}"
                st.rerun()

    archives = de.list_archives(clean_path)
    if archives:
        st.divider()
        st.subheader("Données enregistrées")
        pick = st.selectbox("Recharger une sauvegarde", archives, format_func=lambda p: p.name[len("archive_"):-4])
        if st.button("Recharger cette sauvegarde"):
            with st.spinner("Rechargement et calcul des anomalies..."):
                n = de.load_archive(clean_path, pick)
                try:
                    msg = de.refresh_anomalies(ROOT, clean_path)
                except Exception as e:
                    msg = f"Anomalies non recalculées : {e}"
            st.cache_data.clear()
            st.session_state["data_ready"] = True
            st.session_state["entry_msg"] = f"Sauvegarde rechargée ({n:,} relevés). {msg}"
            st.rerun()

    st.divider()
    if st.button("Utiliser les données déjà dans l'application"):
        st.session_state["data_ready"] = True
        st.rerun()


# --------------------------------------------------------------------------- #
# Navigation
# --------------------------------------------------------------------------- #
PAGES = {
    "📊  Données & EDA": page_data,
    "📈  Prévision": page_forecast,
    "🚨  Anomalies & profils": page_anomalies,
    "🌱  Optimisation & CO₂": page_optimization,
}


def main():
    st.set_page_config(page_title="Energy Management System", page_icon="⚡", layout="wide")
    login_gate(apply_theme)
    apply_theme()
    brand()

    # Après la connexion : d'abord importer le fichier de données
    if not st.session_state.get("data_ready"):
        logout_button()
        page_start()
        st.stop()

    st.session_state.setdefault("view", "main")
    # Les 4 pages principales apparaissent dès la connexion ; choisir l'une d'elles quitte la saisie.
    choice = st.sidebar.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed",
                              key="nav_main", on_change=lambda: st.session_state.update(view="main"))
    # « Nouvelles données » : en dessous des 4 pages
    st.sidebar.divider()
    st.sidebar.button("➕  Entrer de nouvelles données", use_container_width=True,
                      type="primary" if st.session_state["view"] == "new" else "secondary",
                      on_click=lambda: st.session_state.update(view="new"))
    st.sidebar.button("📂  Changer de fichier", use_container_width=True,
                      on_click=lambda: st.session_state.update(data_ready=False, view="main"))
    logout_button()

    if "entry_msg" in st.session_state and st.session_state["view"] != "new":
        st.success(st.session_state.pop("entry_msg"))
    if st.session_state["view"] == "new":
        page_new_data()
    else:
        PAGES[choice]()


if __name__ == "__main__":
    main()
