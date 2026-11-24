"""Saisie de nouvelles données pour l'Energy Management System.

Ce module ne contient AUCUN code Streamlit : il complète les relevés saisis
(colonnes calculées), les ajoute à data/clean_data.csv et recalcule les anomalies.
Il est appelé par la page « 5. Nouvelles données » de app.py.

Colonnes à fournir (le reste est calculé automatiquement) :
    obligatoires : date, Usage_kWh
    optionnelles : Lagging_Current_Reactive.Power_kVarh, Leading_Current_Reactive_Power_kVarh
                   (0 par défaut), CO2(tCO2) (estimé si absent), Load_Type (déduit si absent)
"""
import importlib.util
import shutil
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier

KWH = "Usage_kWh"
LAG_Q = "Lagging_Current_Reactive.Power_kVarh"
LEAD_Q = "Leading_Current_Reactive_Power_kVarh"
CO2 = "CO2(tCO2)"
PF_LAG = "Lagging_Current_Power_Factor"
PF_LEAD = "Leading_Current_Power_Factor"
LOAD_TYPES = ["Light_Load", "Medium_Load", "Maximum_Load"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Ordre exact des colonnes de clean_data.csv
CLEAN_COLS = ["date", KWH, LAG_Q, LEAD_Q, CO2, PF_LAG, PF_LEAD, "NSM", "WeekStatus",
              "Day_of_week", "Load_Type", "hour", "minute", "dayofweek", "month", "is_weekend"]
INPUT_COLS = ["date", KWH, LAG_Q, LEAD_Q, CO2, "Load_Type"]
DATE_FMT = "%Y-%m-%d %H:%M"


# --------------------------------------------------------------------------- #
# Complétion des colonnes calculées
# --------------------------------------------------------------------------- #
def _power_factor(kwh, kvarh):
    """Facteur de puissance en % : 100 * kWh / sqrt(kWh² + kVarh²) (formule du jeu de données)."""
    den = np.sqrt(kwh ** 2 + kvarh ** 2)
    return np.where(den > 0, 100.0 * kwh / np.where(den > 0, den, 1), 100.0)


def emission_factor(ref: pd.DataFrame, min_kwh: float = 40.0) -> float:
    """tCO2 par kWh, estimé sur les relevés >= 40 kWh (là où l'arrondi à 0,01 t est négligeable)."""
    big = ref[ref[KWH] >= min_kwh]
    return float((big[CO2] / big[KWH]).median())


def _load_type_model(ref: pd.DataFrame):
    X = _lt_features(ref)
    return DecisionTreeClassifier(max_depth=6, min_samples_leaf=30, random_state=0).fit(X, ref["Load_Type"])


def _lt_features(df: pd.DataFrame) -> pd.DataFrame:
    d = pd.to_datetime(df["date"])
    return pd.DataFrame({KWH: df[KWH].values, "hour": d.dt.hour.values,
                         "weekend": (d.dt.dayofweek >= 5).astype(int).values,
                         "pf": df[PF_LAG].values})


def complete(raw: pd.DataFrame, ref: pd.DataFrame):
    """Transforme des relevés saisis en lignes au format clean_data.csv.

    Retourne (lignes_completes, liste_de_messages). Lève ValueError si le fichier est inutilisable.
    """
    notes = []
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in ("date", KWH) if c not in df.columns]
    if missing:
        raise ValueError("Colonne(s) obligatoire(s) manquante(s) : " + ", ".join(missing))

    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True).dt.floor("min")
    kwh = pd.to_numeric(df[KWH], errors="coerce")
    bad = df["date"].isna() | kwh.isna()
    if bad.any():
        notes.append(f"{int(bad.sum())} ligne(s) ignorée(s) (date ou {KWH} illisible).")
    df = df[~bad].copy()
    df[KWH] = kwh[~bad]
    if df.empty:
        raise ValueError("Aucune ligne valide.")
    if (df[KWH] < 0).any():
        raise ValueError(f"{KWH} ne peut pas être négatif.")
    if not (df["date"].dt.minute % 15 == 0).all():
        notes.append("Certaines heures ne tombent pas sur un quart d'heure (00, 15, 30, 45) : "
                     "le jeu de données de départ est à pas de 15 min.")

    for col in (LAG_Q, LEAD_Q):
        if col not in df.columns:
            df[col] = 0.0
            notes.append(f"{col} absente : mise à 0.")
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df[PF_LAG] = np.round(_power_factor(df[KWH].values, df[LAG_Q].values), 2)
    df[PF_LEAD] = np.round(_power_factor(df[KWH].values, df[LEAD_Q].values), 2)

    # CO2 : valeur fournie sinon estimation (facteur d'émission du jeu de données, arrondi à 0,01)
    ef = emission_factor(ref)
    est = np.round(df[KWH] * ef, 2)
    if CO2 in df.columns:
        given = pd.to_numeric(df[CO2], errors="coerce")
        df[CO2] = given.where(given.notna(), est)
    else:
        df[CO2] = est
        notes.append(f"{CO2} estimé à partir de la consommation ({ef * 1000:.3f} kgCO₂/kWh).")

    d = df["date"]
    df["NSM"] = d.dt.hour * 3600 + d.dt.minute * 60
    df["hour"], df["minute"] = d.dt.hour, d.dt.minute
    df["dayofweek"], df["month"] = d.dt.dayofweek, d.dt.month
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)
    df["WeekStatus"] = np.where(df["is_weekend"] == 1, "Weekend", "Weekday")
    df["Day_of_week"] = df["dayofweek"].map(dict(enumerate(DAYS)))

    # Type de charge : valeur fournie sinon déduite par un petit arbre de décision appris sur vos données
    if "Load_Type" in df.columns:
        lt = df["Load_Type"].astype(str).str.strip()
        lt = lt.where(lt.isin(LOAD_TYPES))
    else:
        lt = pd.Series(np.nan, index=df.index, dtype=object)
    if lt.isna().any():
        pred = _load_type_model(ref).predict(_lt_features(df))
        lt = lt.where(lt.notna(), pd.Series(pred, index=df.index))
        notes.append("Load_Type absent ou invalide : déduit automatiquement (arbre de décision).")
    df["Load_Type"] = lt

    return df[CLEAN_COLS].sort_values("date").reset_index(drop=True), notes


# --------------------------------------------------------------------------- #
# Écriture dans clean_data.csv (avec sauvegardes)
# --------------------------------------------------------------------------- #
def _paths(clean_path: Path):
    return (clean_path.with_name("clean_data_origine.csv"),
            clean_path.with_name("clean_data_avant_ajout.csv"))


def append_rows(clean_path: Path, new_rows: pd.DataFrame):
    """Ajoute (ou remplace, si la date existe déjà) les lignes. Retourne (ajoutées, remplacées)."""
    origin, previous = _paths(clean_path)
    if not origin.exists():
        shutil.copy2(clean_path, origin)          # copie des données de départ, une seule fois
    shutil.copy2(clean_path, previous)            # pour « annuler le dernier ajout »

    cur = pd.read_csv(clean_path, parse_dates=["date"])
    replaced = int(new_rows["date"].isin(cur["date"]).sum())
    out = (pd.concat([cur[~cur["date"].isin(new_rows["date"])], new_rows])
           .sort_values("date").reset_index(drop=True))
    out[CLEAN_COLS].to_csv(clean_path, index=False, date_format=DATE_FMT)
    return len(new_rows) - replaced, replaced


def archive_dir(clean_path: Path) -> Path:
    d = clean_path.parent / "archives"
    d.mkdir(exist_ok=True)
    return d


def archive_current(clean_path: Path, name: str = "") -> Path:
    """Enregistre une copie des données actuelles dans data/archives/ (ne les modifie pas)."""
    import re
    from datetime import datetime
    n = len(pd.read_csv(clean_path, usecols=["date"]))
    label = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = archive_dir(clean_path) / f"archive_{stamp}_{n}releves{'_' + label if label else ''}.csv"
    shutil.copy2(clean_path, dst)
    return dst


def list_archives(clean_path: Path):
    return sorted(archive_dir(clean_path).glob("archive_*.csv"), reverse=True)


def load_archive(clean_path: Path, archive: Path) -> int:
    """Remet une archive comme données actuelles (les données actuelles sont d'abord archivées)."""
    archive_current(clean_path, "avant_rechargement")
    shutil.copy2(archive, clean_path)
    return len(pd.read_csv(clean_path, usecols=["date"]))


def replace_all(clean_path: Path, rows: pd.DataFrame) -> int:
    """Remplace tout clean_data.csv par `rows` (fichier importé au démarrage)."""
    origin, previous = _paths(clean_path)
    if not origin.exists():
        shutil.copy2(clean_path, origin)          # données de départ gardées une seule fois
    shutil.copy2(clean_path, previous)
    out = rows.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    out[CLEAN_COLS].to_csv(clean_path, index=False, date_format=DATE_FMT)
    return len(out)


def restore(clean_path: Path, which: str) -> bool:
    """which = 'previous' (annule le dernier ajout) ou 'origin' (données de départ)."""
    origin, previous = _paths(clean_path)
    src = previous if which == "previous" else origin
    if not src.exists():
        return False
    shutil.copy2(src, clean_path)
    return True


def gaps(clean_path: Path) -> int:
    """Nombre d'intervalles différents de 15 min (les retards/lags du modèle supposent un pas régulier)."""
    d = pd.read_csv(clean_path, usecols=["date"], parse_dates=["date"])["date"].sort_values().diff().dropna()
    return int((d != pd.Timedelta(minutes=15)).sum())


def template_csv() -> bytes:
    ex = pd.DataFrame({
        "date": ["2019-01-01 00:15", "2019-01-01 00:30"],
        KWH: [3.5, 3.8], LAG_Q: [3.1, 3.3], LEAD_Q: [0.0, 0.0], CO2: ["", ""], "Load_Type": ["", ""],
    })
    return ex.to_csv(index=False).encode("utf-8")


# --------------------------------------------------------------------------- #
# Recalcul des anomalies (Isolation Forest déjà entraîné, non ré-entraîné)
# --------------------------------------------------------------------------- #
def _find(root: Path, name: str):
    hits = [p for p in root.rglob(name) if p.is_file()]
    return min(hits, key=lambda p: len(p.parts)) if hits else None


def refresh_anomalies(root: Path, clean_path: Path) -> str:
    """Reconstruit anomaly_results.csv à partir de clean_data.csv. Retourne un message d'état."""
    needed = {n: _find(root, n) for n in ("feature_engineering.py", "isolation_forest.pkl",
                                          "scaler_anomaly.pkl", "anomaly_features.pkl",
                                          "anomaly_reference.pkl", "anomaly_results.csv")}
    lacks = [n for n, p in needed.items() if p is None]
    if lacks:
        return "Anomalies non recalculées : fichier(s) introuvable(s) : " + ", ".join(lacks)

    # copie unique des anomalies d'origine (dossier detection-classification), jamais écrasée
    orig_copy = needed["anomaly_results.csv"].with_name("anomaly_results_origine.csv")
    if not orig_copy.exists():
        shutil.copy2(needed["anomaly_results.csv"], orig_copy)

    spec = importlib.util.spec_from_file_location("fe_tmp", needed["feature_engineering.py"])
    fe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fe)

    feat = fe.build_features(pd.read_csv(clean_path, parse_dates=["date"]))
    model, scaler = joblib.load(needed["isolation_forest.pkl"]), joblib.load(needed["scaler_anomaly.pkl"])
    cols, ref = joblib.load(needed["anomaly_features.pkl"]), float(joblib.load(needed["anomaly_reference.pkl"]))

    X = scaler.transform(feat[cols])
    feat["is_anomaly"] = (model.predict(X) == -1).astype(int)
    feat["anomaly_score"] = -model.score_samples(X)
    feat["type_anomaly"] = "Normal"
    feat.loc[(feat["is_anomaly"] == 1) & (feat[KWH] > ref), "type_anomaly"] = "Hausse"
    feat.loc[(feat["is_anomaly"] == 1) & (feat[KWH] <= ref), "type_anomaly"] = "Baisse"
    feat.to_csv(needed["anomaly_results.csv"], index=False)
    return f"Anomalies recalculées ({int(feat['is_anomaly'].sum())} détectées sur {len(feat):,} relevés)."
