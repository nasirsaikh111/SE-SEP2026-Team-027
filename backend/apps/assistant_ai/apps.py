import os
import sys
import threading

from django.apps import AppConfig


class AssistantAIConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.assistant_ai'

    def ready(self):
        """Warm the embedding model in the background when the web server starts (avoids a slow first request)."""
        from django.conf import settings
        serving = any(x in sys.argv for x in ('runserver', 'gunicorn', 'uvicorn', 'daphne')) or 'gunicorn' in sys.argv[0]
        if getattr(settings, 'TESTING', False) or not serving or os.environ.get('RUN_MAIN') == 'false':
            return
        if getattr(settings, 'SANGAM_EMBEDDING_BACKEND', 'none') == 'minilm':
            def warm():
                from .services import get_embedder
                from .ml.embeddings import EmbeddingUnavailable
                emb = get_embedder()
                emb.timeout, old = 300, emb.timeout
                try:
                    emb.encode(['warm up'])
                except EmbeddingUnavailable:
                    pass
                emb.timeout = old
            threading.Thread(target=warm, daemon=True, name='sangam-embedding-warmup').start()
