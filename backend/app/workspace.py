"""Reuse Moniq's classifier while keeping private correction training separate."""
from threading import RLock

from . import config
from .ml import Classifier

_model_lock = RLock()


def personal_classifier(request):
    with _model_lock:
        if getattr(request.app.state, "personal_classifier", None) is None:
            request.app.state.personal_classifier = Classifier(model_dir=config.PERSONAL_MODEL_DIR)
        return request.app.state.personal_classifier


def workspace_classifier(request):
    if not request.app.state.public_demo and request.cookies.get("moniq_workspace") == "personal":
        return personal_classifier(request)
    return request.app.state.classifier
