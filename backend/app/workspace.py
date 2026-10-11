"""Reuse Moniq's classifier while keeping private correction training separate."""
from threading import RLock

from . import config
from .ml import Classifier
from .access import hosted, private

_model_lock = RLock()


def personal_classifier(request):
    with _model_lock:
        if hosted(request):
            if not private(request):
                from fastapi import HTTPException
                raise HTTPException(403, "A private session is required.")
            store = request.app.state.identity_store
            user_id = request.state.identity.user_id
            if user_id not in store.classifiers:
                from sqlalchemy import select
                from sqlalchemy.orm import Session
                from .models import Correction
                model = Classifier(model_dir=config.RUNTIME / "hosted-models" / user_id)
                with Session(request.state.private_engine) as db:
                    model.train(list(db.scalars(select(Correction))))
                store.classifiers[user_id] = model
            return store.classifiers[user_id]
        if getattr(request.app.state, "personal_classifier", None) is None:
            request.app.state.personal_classifier = Classifier(model_dir=config.PERSONAL_MODEL_DIR)
        return request.app.state.personal_classifier


def workspace_classifier(request):
    if private(request):
        return personal_classifier(request)
    return request.app.state.classifier
