import json
from pathlib import Path
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, classification_report, mean_absolute_error,
    mean_squared_error, r2_score)
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/StudentsPerformance.csv"
OUT_DIR = ROOT / "ml/models"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FEATURES = ["study_hours", "attendance", "sleep_hours", "internet_usage", "assignments_completed", "previous_score"]
REGRESSION_FEATURES = ["study_hours", "attendance", "sleep_hours", "internet_usage", "assignments_completed"]
TARGET = "placement_status"

def main():
    if not DATA_PATH.exists(): raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    required = [*REGRESSION_FEATURES, "math score", "reading score", "writing score", TARGET]
    missing = [c for c in required if c not in df.columns]
    if missing: raise ValueError(f"Missing required columns: {missing}")
    df["previous_score"] = df[["math score", "reading score", "writing score"]].mean(axis=1)
    df["exam_score"] = df[["math score", "reading score", "writing score"]].mean(axis=1)

    # Classification: predict the historical placement label.
    X, y = df[FEATURES], df[TARGET].astype(str).str.strip()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    classifier = Pipeline([("imputer", SimpleImputer(strategy="median")), ("classifier", RandomForestClassifier(n_estimators=350, min_samples_leaf=2, class_weight="balanced", random_state=42))])
    classifier.fit(X_train, y_train)
    pred = classifier.predict(X_test)
    class_metrics = {"accuracy": round(float(accuracy_score(y_test, pred)),4), "precision_macro":round(float(precision_score(y_test,pred,average="macro",zero_division=0)),4), "recall_macro":round(float(recall_score(y_test,pred,average="macro",zero_division=0)),4), "f1_macro":round(float(f1_score(y_test,pred,average="macro",zero_division=0)),4), "confusion_matrix":confusion_matrix(y_test,pred,labels=list(classifier.classes_)).tolist(), "class_labels":list(classifier.classes_), "classification_report":classification_report(y_test,pred,output_dict=True,zero_division=0), "test_rows":int(len(y_test)), "train_rows":int(len(y_train)), "feature_names":FEATURES, "target":TARGET, "label_counts":y.value_counts().to_dict(), "dataset_rows":int(len(df))}
    if len(classifier.classes_) == 2:
        try:
            positive = "Placed" if "Placed" in classifier.classes_ else classifier.classes_[1]
            class_metrics["roc_auc"] = round(float(roc_auc_score((y_test == positive).astype(int), classifier.predict_proba(X_test)[:,list(classifier.classes_).index(positive)])),4)
        except Exception: pass
    joblib.dump(classifier, OUT_DIR / "placement_model.joblib")

    # Regression: estimate mean subject score from lifestyle/learning-routine inputs.
    # previous_score is intentionally excluded to avoid target leakage (it is derived from the same subject scores).
    RX, ry = df[REGRESSION_FEATURES], df["exam_score"]
    RX_train, RX_test, ry_train, ry_test = train_test_split(RX, ry, test_size=0.2, random_state=42)
    regressor = Pipeline([("imputer", SimpleImputer(strategy="median")), ("regressor", RandomForestRegressor(n_estimators=350, min_samples_leaf=2, random_state=42, n_jobs=-1))])
    regressor.fit(RX_train, ry_train)
    rpred = regressor.predict(RX_test)
    reg_metrics = {"mae":round(float(mean_absolute_error(ry_test,rpred)),3), "rmse":round(float(mean_squared_error(ry_test,rpred)**0.5),3), "r2":round(float(r2_score(ry_test,rpred)),4), "train_rows":int(len(ry_train)), "test_rows":int(len(ry_test)), "feature_names":REGRESSION_FEATURES, "target":"exam_score (mean of math, reading, writing)", "reliability_note":"Negative R2 means this model performed worse than predicting the test-set mean; treat its output as experimental, not a dependable forecast."}
    joblib.dump(regressor, OUT_DIR / "score_model.joblib")
    metadata = {"model_version":"rf-classifier-v2+rf-regressor-v1", "classification":{"algorithm":"RandomForestClassifier","metrics":class_metrics}, "regression":{"algorithm":"RandomForestRegressor","metrics":reg_metrics}, "trained_at_utc":pd.Timestamp.utcnow().isoformat(), "dataset_rows":int(len(df)), "notes":"Exam score is the mean of math, reading and writing. The score regressor uses lifestyle features only; previous_score is excluded to prevent leakage. Validate label provenance before real-world use."}
    (OUT_DIR / "model_metadata.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    print(json.dumps({"classification":class_metrics,"regression":reg_metrics,"saved_models":[str(OUT_DIR/"placement_model.joblib"),str(OUT_DIR/"score_model.joblib")]},indent=2))

if __name__ == "__main__": main()
