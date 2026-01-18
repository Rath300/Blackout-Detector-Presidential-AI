import os
from datetime import datetime

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    auc,
    confusion_matrix,
    precision_recall_curve,
    roc_curve,
    brier_score_loss,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier

from core.services import ml_risk


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "report_charts")
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "risk_model.pkl")


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _load_model_bundle():
    if not os.path.exists(MODEL_PATH):
        ml_risk.train_and_cache_model()
    return joblib.load(MODEL_PATH)


def _bootstrap_ci(values, n=500, alpha=0.05):
    if len(values) == 0:
        return (0.0, 0.0)
    samples = []
    values = np.array(values)
    for _ in range(n):
        resample = np.random.choice(values, size=len(values), replace=True)
        samples.append(np.mean(resample))
    lower = np.percentile(samples, 100 * alpha / 2)
    upper = np.percentile(samples, 100 * (1 - alpha / 2))
    return lower, upper


def _temporal_split(df, test_frac=0.2):
    years = np.sort(df["YEAR"].unique())
    split_idx = max(1, int(len(years) * (1 - test_frac)))
    train_years = years[:split_idx]
    test_years = years[split_idx:]
    return train_years, test_years


def _strip_leakage_features(X):
    leakage_cols = {
        "DAMAGE_PROPERTY_NUM",
        "DAMAGE_CROPS_NUM",
        "INJURIES",
        "DEATHS",
    }
    event_cols = [col for col in X.columns if col.startswith("event_")]
    drop_cols = list(leakage_cols.intersection(set(X.columns))) + event_cols
    return X.drop(columns=drop_cols, errors="ignore")


def _state_name_to_abbr():
    return {
        "ALABAMA": "AL",
        "ALASKA": "AK",
        "ARIZONA": "AZ",
        "ARKANSAS": "AR",
        "CALIFORNIA": "CA",
        "COLORADO": "CO",
        "CONNECTICUT": "CT",
        "DELAWARE": "DE",
        "FLORIDA": "FL",
        "GEORGIA": "GA",
        "HAWAII": "HI",
        "IDAHO": "ID",
        "ILLINOIS": "IL",
        "INDIANA": "IN",
        "IOWA": "IA",
        "KANSAS": "KS",
        "KENTUCKY": "KY",
        "LOUISIANA": "LA",
        "MAINE": "ME",
        "MARYLAND": "MD",
        "MASSACHUSETTS": "MA",
        "MICHIGAN": "MI",
        "MINNESOTA": "MN",
        "MISSISSIPPI": "MS",
        "MISSOURI": "MO",
        "MONTANA": "MT",
        "NEBRASKA": "NE",
        "NEVADA": "NV",
        "NEW HAMPSHIRE": "NH",
        "NEW JERSEY": "NJ",
        "NEW MEXICO": "NM",
        "NEW YORK": "NY",
        "NORTH CAROLINA": "NC",
        "NORTH DAKOTA": "ND",
        "OHIO": "OH",
        "OKLAHOMA": "OK",
        "OREGON": "OR",
        "PENNSYLVANIA": "PA",
        "RHODE ISLAND": "RI",
        "SOUTH CAROLINA": "SC",
        "SOUTH DAKOTA": "SD",
        "TENNESSEE": "TN",
        "TEXAS": "TX",
        "UTAH": "UT",
        "VERMONT": "VT",
        "VIRGINIA": "VA",
        "WASHINGTON": "WA",
        "WEST VIRGINIA": "WV",
        "WISCONSIN": "WI",
        "WYOMING": "WY",
        "DISTRICT OF COLUMBIA": "DC",
    }


def main():
    _ensure_output_dir()

    df = ml_risk._load_storm_events()
    if df.empty:
        raise SystemExit("No StormEvents data found. Add StormEvents_details-*.csv.gz to project root.")

    X, y, df_full = ml_risk._prepare_training_data(df)
    X_eval = _strip_leakage_features(X)
    model = GradientBoostingClassifier(random_state=42)

    # Random split (baseline) + temporal split (realistic).
    X_train, X_test, y_train, y_test = train_test_split(
        X_eval, y, test_size=0.2, random_state=42, stratify=y
    )
    train_years, test_years = _temporal_split(df_full, test_frac=0.2)
    temporal_train = df_full[df_full["YEAR"].isin(train_years)]
    temporal_test = df_full[df_full["YEAR"].isin(test_years)]
    X_time = X_eval.loc[temporal_test.index]
    y_time = y.loc[temporal_test.index]
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    probas = model.predict_proba(X_test)[:, 1]

    # 01 ROC curve (random split)
    fpr, tpr, _ = roc_curve(y_test, probas)
    roc_auc = auc(fpr, tpr)
    plt.figure(figsize=(6, 4))
    plt.plot(fpr, tpr, label=f"AUC={roc_auc:.3f}", color="#16a34a")
    plt.plot([0, 1], [0, 1], "--", color="#94a3b8")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "01_roc_curve.png"), dpi=200)
    plt.close()

    # 02 Precision-Recall curve (random split)
    precision, recall, _ = precision_recall_curve(y_test, probas)
    pr_auc = auc(recall, precision)
    plt.figure(figsize=(6, 4))
    plt.plot(recall, precision, color="#15803d", label=f"PR AUC={pr_auc:.3f}")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "02_precision_recall.png"), dpi=200)
    plt.close()

    # 03 Calibration curve (random split)
    cal_true, cal_pred = calibration_curve(y_test, probas, n_bins=10, strategy="uniform")
    plt.figure(figsize=(6, 4))
    plt.plot(cal_pred, cal_true, marker="o", color="#22c55e")
    plt.plot([0, 1], [0, 1], "--", color="#94a3b8")
    plt.xlabel("Predicted Probability")
    plt.ylabel("Observed Frequency")
    plt.title("Calibration Curve")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "03_calibration.png"), dpi=200)
    plt.close()

    # 04 Confusion matrix (random split)
    cm = confusion_matrix(y_test, preds)
    plt.figure(figsize=(5, 4))
    plt.imshow(cm, cmap="Greens")
    plt.colorbar()
    plt.title("Confusion Matrix")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    for (i, j), val in np.ndenumerate(cm):
        plt.text(j, i, int(val), ha="center", va="center", color="#0f172a")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "04_confusion_matrix.png"), dpi=200)
    plt.close()

    # 05 Stability over time (yearly mean pred vs actual)
    df_full["OUTAGE_PROB"] = model.predict_proba(X_eval)[:, 1]
    stability = (
        df_full.groupby("YEAR")
        .agg(mean_pred=("OUTAGE_PROB", "mean"), mean_actual=("POWER_OUTAGE_LIKELY", "mean"))
        .reset_index()
        .sort_values("YEAR")
    )
    plt.figure(figsize=(7, 4))
    plt.plot(stability["YEAR"], stability["mean_pred"], label="Predicted", color="#22c55e")
    plt.plot(stability["YEAR"], stability["mean_actual"], label="Actual", color="#f97316")
    plt.xlabel("Year")
    plt.ylabel("Rate")
    plt.title("Yearly Stability")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "05_yearly_stability.png"), dpi=200)
    plt.close()

    # 06 Stability confidence intervals
    ci_rows = []
    for year, subset in df_full.groupby("YEAR"):
        pred_ci = _bootstrap_ci(subset["OUTAGE_PROB"].values)
        actual_ci = _bootstrap_ci(subset["POWER_OUTAGE_LIKELY"].values)
        ci_rows.append(
            {
                "YEAR": year,
                "pred_lower": pred_ci[0],
                "pred_upper": pred_ci[1],
                "actual_lower": actual_ci[0],
                "actual_upper": actual_ci[1],
                "pred_mean": subset["OUTAGE_PROB"].mean(),
                "actual_mean": subset["POWER_OUTAGE_LIKELY"].mean(),
            }
        )
    ci_df = pd.DataFrame(ci_rows).sort_values("YEAR")
    plt.figure(figsize=(7, 4))
    plt.fill_between(ci_df["YEAR"], ci_df["pred_lower"], ci_df["pred_upper"], color="#bbf7d0", alpha=0.5)
    plt.plot(ci_df["YEAR"], ci_df["pred_mean"], color="#16a34a", label="Predicted mean")
    plt.plot(ci_df["YEAR"], ci_df["actual_mean"], color="#f97316", label="Actual mean")
    plt.xlabel("Year")
    plt.ylabel("Rate")
    plt.title("Stability Confidence Intervals")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "06_stability_ci.png"), dpi=200)
    plt.close()

    # 07 Residual distribution
    residuals = y_test.values - probas
    plt.figure(figsize=(6, 4))
    plt.hist(residuals, bins=30, color="#86efac", edgecolor="#14532d")
    plt.xlabel("Actual - Predicted")
    plt.ylabel("Count")
    plt.title("Residual Distribution")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "07_residuals.png"), dpi=200)
    plt.close()

    # 08 Feature importance (model-based)
    importances = model.feature_importances_
    top_idx = np.argsort(importances)[-12:]
    plt.figure(figsize=(7, 4))
    plt.barh(range(len(top_idx)), importances[top_idx], color="#4ade80")
    plt.yticks(range(len(top_idx)), [X_eval.columns[i] for i in top_idx])
    plt.title("Top Feature Importances")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "08_feature_importance.png"), dpi=200)
    plt.close()

    # 09 Risk distribution across counties
    county_df = ml_risk.get_county_risk()
    plt.figure(figsize=(6, 4))
    plt.hist(county_df["risk"].fillna(0), bins=30, color="#22c55e", edgecolor="#14532d")
    plt.xlabel("County Risk Score")
    plt.ylabel("Counties")
    plt.title("County Risk Distribution")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "09_county_risk_distribution.png"), dpi=200)
    plt.close()

    # 10 AUC bootstrap confidence interval
    auc_samples = []
    idx = np.arange(len(y_test))
    for _ in range(300):
        sample_idx = np.random.choice(idx, size=len(idx), replace=True)
        sample_auc = auc(
            *roc_curve(y_test.iloc[sample_idx], probas[sample_idx])[:2]
        )
        auc_samples.append(sample_auc)
    plt.figure(figsize=(6, 4))
    plt.hist(auc_samples, bins=20, color="#86efac", edgecolor="#14532d")
    plt.axvline(np.mean(auc_samples), color="#16a34a", linestyle="--", label="Mean AUC")
    plt.xlabel("AUC")
    plt.ylabel("Frequency")
    plt.title("AUC Bootstrap Distribution")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "10_auc_bootstrap.png"), dpi=200)
    plt.close()

    # 11 SVI vs risk scatter
    if "svi" in county_df.columns:
        plt.figure(figsize=(6, 4))
        plt.scatter(county_df["svi"], county_df["risk"], alpha=0.3, color="#16a34a")
        plt.xlabel("SVI")
        plt.ylabel("Risk")
        plt.title("SVI vs County Risk")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "11_svi_vs_risk.png"), dpi=200)
        plt.close()

    # 12 Brier score summary
    brier = brier_score_loss(y_test, probas)
    plt.figure(figsize=(5, 3))
    plt.bar(["Brier"], [brier], color="#22c55e")
    plt.title("Brier Score (Lower is Better)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "12_brier_score.png"), dpi=200)
    plt.close()

    # 13 ROC curve (temporal split)
    if len(X_time) > 0:
        probas_time = model.predict_proba(X_time)[:, 1]
        fpr_t, tpr_t, _ = roc_curve(y_time, probas_time)
        auc_t = roc_auc_score(y_time, probas_time)
        plt.figure(figsize=(6, 4))
        plt.plot(fpr_t, tpr_t, label=f"AUC={auc_t:.3f}", color="#0ea5e9")
        plt.plot([0, 1], [0, 1], "--", color="#94a3b8")
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title("ROC Curve (Temporal Split)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "13_roc_curve_temporal.png"), dpi=200)
        plt.close()

        # 14 Calibration curve (temporal split)
        cal_true_t, cal_pred_t = calibration_curve(y_time, probas_time, n_bins=10, strategy="uniform")
        plt.figure(figsize=(6, 4))
        plt.plot(cal_pred_t, cal_true_t, marker="o", color="#0ea5e9")
        plt.plot([0, 1], [0, 1], "--", color="#94a3b8")
        plt.xlabel("Predicted Probability")
        plt.ylabel("Observed Frequency")
        plt.title("Calibration (Temporal Split)")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "14_calibration_temporal.png"), dpi=200)
        plt.close()

        # 15 Residuals (temporal)
        residuals_t = y_time.values - probas_time
        plt.figure(figsize=(6, 4))
        plt.hist(residuals_t, bins=30, color="#bae6fd", edgecolor="#0f172a")
        plt.xlabel("Actual - Predicted")
        plt.ylabel("Count")
        plt.title("Residuals (Temporal Split)")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "15_residuals_temporal.png"), dpi=200)
        plt.close()

    # 16 Permutation importance (robust)
    perm = permutation_importance(model, X_test, y_test, n_repeats=10, random_state=42)
    perm_idx = np.argsort(perm.importances_mean)[-12:]
    plt.figure(figsize=(7, 4))
    plt.barh(range(len(perm_idx)), perm.importances_mean[perm_idx], color="#60a5fa")
    plt.yticks(range(len(perm_idx)), [X_eval.columns[i] for i in perm_idx])
    plt.title("Permutation Importance")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "16_permutation_importance.png"), dpi=200)
    plt.close()

    # 17 Performance by event type (top 12)
    df_eval = df_full.loc[X_test.index].copy()
    df_eval["prob"] = probas
    df_eval["actual"] = y_test.values
    event_perf = (
        df_eval.groupby("EVENT_TYPE")
        .agg(count=("actual", "size"), actual_rate=("actual", "mean"), pred_rate=("prob", "mean"))
        .reset_index()
        .sort_values("count", ascending=False)
        .head(12)
    )
    plt.figure(figsize=(7, 4))
    plt.plot(event_perf["EVENT_TYPE"], event_perf["actual_rate"], marker="o", label="Actual")
    plt.plot(event_perf["EVENT_TYPE"], event_perf["pred_rate"], marker="o", label="Predicted")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Rate")
    plt.title("Actual vs Predicted by Event Type")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "17_event_type_comparison.png"), dpi=200)
    plt.close()

    # 18 State-year predicted vs OE-417 outage counts (external validation)
    oe_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "oe-417-annual-summaries.csv",
    )
    if os.path.exists(oe_path):
        oe = pd.read_csv(oe_path)
        oe["YEAR"] = pd.to_datetime(oe["Date Event Began"], errors="coerce").dt.year
        oe["STATE_NAME"] = oe["Area Affected"].str.split(":").str[0].str.strip().str.upper()
        mapping = _state_name_to_abbr()
        oe["STATE"] = oe["STATE_NAME"].map(mapping)
        oe = oe.dropna(subset=["YEAR", "STATE"])
        oe_summary = (
            oe.groupby(["STATE", "YEAR"])
            .agg(outage_events=("Event Type", "count"), customers=("Number of Customers Affected", "sum"))
            .reset_index()
        )

        df_full["STATE_ABBR"] = df_full["STATE"].str.upper().map(mapping)
        pred_state_year = (
            df_full.groupby(["STATE_ABBR", "YEAR"])
            .agg(pred_rate=("OUTAGE_PROB", "mean"))
            .reset_index()
            .rename(columns={"STATE_ABBR": "STATE"})
        )

        merged = oe_summary.merge(pred_state_year, on=["STATE", "YEAR"], how="inner")
        if not merged.empty:
            plt.figure(figsize=(6, 4))
            plt.scatter(merged["pred_rate"], merged["outage_events"], alpha=0.6, color="#16a34a")
            plt.xlabel("Predicted Outage Rate (Storm Events)")
            plt.ylabel("OE-417 Outage Event Count")
            plt.title("Predicted vs OE-417 Outage Counts")
            plt.tight_layout()
            plt.savefig(os.path.join(OUTPUT_DIR, "18_pred_vs_oe417.png"), dpi=200)
            plt.close()

    # 19 ANOVA-style variance by event type (no leakage features)
    top_event_types = df_full["EVENT_TYPE"].value_counts().head(8).index.tolist()
    groups = [df_full.loc[df_full["EVENT_TYPE"] == event, "OUTAGE_PROB"].values for event in top_event_types]
    group_means = [np.mean(g) for g in groups]
    overall_mean = np.mean(np.concatenate(groups)) if groups else 0
    ss_between = sum(len(g) * (m - overall_mean) ** 2 for g, m in zip(groups, group_means))
    ss_within = sum(np.sum((g - np.mean(g)) ** 2) for g in groups)
    df_between = max(len(groups) - 1, 1)
    df_within = max(sum(len(g) for g in groups) - len(groups), 1)
    f_stat = (ss_between / df_between) / (ss_within / df_within) if ss_within > 0 else 0

    plt.figure(figsize=(7, 4))
    plt.boxplot(groups, labels=top_event_types, showfliers=False)
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Predicted Outage Probability")
    plt.title(f"ANOVA-style Event Type Variance (F={f_stat:.2f})")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "19_event_type_anova.png"), dpi=200)
    plt.close()

    print(f"Charts generated in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
