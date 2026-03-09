import json
import os
from typing import Optional, Tuple, List

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
_DEFAULT_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
_DEFAULT_TRAINING_DATA_FILE = os.path.join(_DEFAULT_DATA_DIR, "training_data.json")
_DEFAULT_MODEL_FILE = os.path.join(_DEFAULT_DATA_DIR, "error_classifier.joblib")


def _load_training_examples(training_data_file: str) -> Tuple[List[str], List[str]]:
    with open(training_data_file, "r") as f:
        raw=json.load(f)

    messages: List[str]=[]
    labels: List[str]=[]

    if not isinstance(raw, list):
        return messages, labels

    for row in raw:
        if not isinstance(row, dict):
            continue
        msg = row.get("message")
        cat = row.get("category")
        if not msg or not cat:
            continue
        messages.append(str(msg))
        labels.append(str(cat))

    return messages, labels


class ErrorClassifier:
    def __init__(
        self,
        model_file: str = _DEFAULT_MODEL_FILE,
        training_data_file: str = _DEFAULT_TRAINING_DATA_FILE,
    ) -> None:
        self.model_file = model_file
        self.training_data_file = training_data_file
        self._pipeline: Optional[Pipeline] = None

    def is_trained(self) -> bool:
        return self._pipeline is not None or os.path.exists(self.model_file)

    def train(self) -> None:
        if not os.path.exists(self.training_data_file):
            raise FileNotFoundError(f"Training data not found: {self.training_data_file}")

        X, y = _load_training_examples(self.training_data_file)
        if len(X) < 2:
            raise ValueError("Not enough training examples to train classifier.")

        pipeline = Pipeline(
            steps=[
                (
                    "tfidf",
                    TfidfVectorizer(
                        lowercase=True,
                        ngram_range=(1, 2),
                        min_df=1,
                        token_pattern=r"(?u)\b\w+\b|[;{}()\[\]+-/*=<>]"
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight='balanced',
                        solver='lbfgs'
                    ),
                ),
            ]
        )

        pipeline.fit(X, y)
        self._pipeline = pipeline

    def save(self) -> None:
        if self._pipeline is None:
            raise ValueError("No trained model in memory to save.")
        os.makedirs(os.path.dirname(self.model_file), exist_ok=True)
        joblib.dump(self._pipeline, self.model_file)

    def load(self) -> bool:
        if self._pipeline is not None:
            return True
        if not os.path.exists(self.model_file):
            return False
        self._pipeline = joblib.load(self.model_file)
        return True

    def train_and_save(self) -> None:
        self.train()
        self.save()

    def predict(self, message: str) -> Tuple[Optional[str], float]:
        if not message:
            return None, 0.0

        if not self.load():
            if os.path.exists(self.training_data_file):
                try:
                    self.train_and_save()
                except Exception:
                    return None, 0.0

            if not self.load():
                return None, 0.0

        assert self._pipeline is not None

        try:
            proba = self._pipeline.predict_proba([message])
            pred = self._pipeline.classes_[int(proba[0].argmax())]
            confidence = float(proba[0].max())
            return str(pred), confidence
        except Exception:
            pred = self._pipeline.predict([message])[0]
            return str(pred), 0.5


_default_classifier: Optional[ErrorClassifier] = None


def get_default_classifier() -> ErrorClassifier:
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = ErrorClassifier()
    return _default_classifier





def predict_error_category(error_message: str) -> str:
    """Legacy predictor fallback; actual classification is in error_explainer.py."""
    return "unknown"


if __name__ == "__main__":
    get_default_classifier().train_and_save()
