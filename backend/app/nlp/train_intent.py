"""
Trains and evaluates the intent classifier.
Run from the backend folder:   python -m app.nlp.train_intent
"""
import joblib
import matplotlib

matplotlib.use("Agg")  # draw to a file, no window needed
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score,
                             classification_report, f1_score)
from sklearn.model_selection import StratifiedGroupKFold, cross_val_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from app.config import INTENT_DATASET_PATH, INTENT_MODEL_PATH, REPORTS_DIR
from app.nlp.preprocessor import preprocess


def build_pipeline(classifier) -> Pipeline:
    """TF-IDF turns text into numbers; the classifier learns from those numbers."""
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ("clf", classifier),
    ])


CANDIDATES = {
    "Logistic Regression": LogisticRegression(max_iter=1000, C=10, class_weight="balanced"),
    "Naive Bayes": MultinomialNB(alpha=0.3),
    "Linear SVM": LinearSVC(class_weight="balanced"),
}


def main() -> None:
    # 1. Load + preprocess
    df = pd.read_csv(INTENT_DATASET_PATH)
    print(f"Loaded {len(df)} sentences. Preprocessing...")
    df["clean"] = df["requirement"].apply(lambda t: preprocess(t)["cleaned"])
    X, y, groups = df["clean"], df["intent"], df["pattern_id"]

    # 2. Split 75% train / 25% test.
    #    All sentences from one pattern stay on the SAME side, so the test
    #    set only contains phrasings the model has never seen.
    splitter = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    print(f"Train: {len(X_train)} sentences | Test: {len(X_test)} sentences\n")

    # 3. Compare three algorithms
    lines = [f"{'Model':<22}{'Accuracy':>10}{'Macro F1':>10}{'5-fold CV':>11}"]
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    for name, clf in CANDIDATES.items():
        model = build_pipeline(clf).fit(X_train, y_train)
        pred = model.predict(X_test)
        cv_acc = cross_val_score(build_pipeline(clf), X, y, groups=groups, cv=cv).mean()
        lines.append(f"{name:<22}{accuracy_score(y_test, pred):>10.3f}"
                     f"{f1_score(y_test, pred, average='macro'):>10.3f}{cv_acc:>11.3f}")
    comparison = "\n".join(lines)
    print(comparison)

    # 4. Detailed report for the model we deploy.
    #    Logistic Regression gives probabilities, and the agent needs those
    #    later: low confidence -> ask the user a clarification question.
    final = build_pipeline(CANDIDATES["Logistic Regression"]).fit(X_train, y_train)
    pred = final.predict(X_test)
    report = classification_report(y_test, pred, digits=3)
    print("\nLogistic Regression - detailed report\n")
    print(report)

    (REPORTS_DIR / "intent_metrics.txt").write_text(
        comparison + "\n\nLogistic Regression\n\n" + report, encoding="utf-8")

    fig, ax = plt.subplots(figsize=(9, 8))
    ConfusionMatrixDisplay.from_predictions(
        y_test, pred, ax=ax, cmap="Blues", xticks_rotation=45, colorbar=False)
    ax.set_title("Intent classifier - confusion matrix (test set)")
    fig.tight_layout()
    fig.savefig(REPORTS_DIR / "intent_confusion_matrix.png", dpi=150)

    # 5. Evaluation is finished, so now train on ALL the data and save
    final.fit(X, y)
    joblib.dump(final, INTENT_MODEL_PATH)
    print(f"Model saved   -> {INTENT_MODEL_PATH}")
    print(f"Reports saved -> {REPORTS_DIR}")


if __name__ == "__main__":
    main()