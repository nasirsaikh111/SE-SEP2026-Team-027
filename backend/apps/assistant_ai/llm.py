"""The ONLY module that talks to an LLM (Gemini or local Ollama). Chosen by settings.AI_PROVIDER.

- generate(prompt) -> str | None        (None => caller uses its rule-based fallback)
- generate_detailed(prompt) -> LLMResult (adds provider + error kind: timeout / unavailable / error)
- embed(texts) -> list[list[float]] | None   (Gemini embeddings, optional)

Gemini keys: settings.GEMINI_API_KEYS may hold several keys; when a call fails with a quota / expired /
invalid-key error the client rotates to the next key and retries. Errors are logged without content.
"""
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
from dataclasses import dataclass
from urllib.request import Request, urlopen

from django.conf import settings

from .ml.text import strip_pii

logger = logging.getLogger(__name__)
_pool = ThreadPoolExecutor(max_workers=4)
_lock = threading.Lock()
_state = {'key_index': 0, 'clients': {}, 'dead_keys': set()}

# Error text that means this key is used up or invalid, so try the next key
KEY_ERRORS = ('quota', 'exhausted', 'rate limit', '429', 'expired', 'api key not valid', 'api_key_invalid', 'permission_denied',
              '401', '403', 'invalid api key', 'billing', 'all models')


@dataclass
class LLMResult:
    text: str | None
    provider: str
    error: str | None = None   # None | 'timeout' | 'unavailable' | 'error'


def provider():
    return (getattr(settings, 'AI_PROVIDER', 'none') or 'none').lower()


# ------------------------------------------------------------------ Gemini with key rotation
def _keys():
    return list(getattr(settings, 'GEMINI_API_KEYS', []) or ([settings.GEMINI_API_KEY] if getattr(settings, 'GEMINI_API_KEY', '') else []))


# One client per key, kept alive; a throwaway client gets closed mid-request
def _client(key):
    c = _state['clients'].get(key)
    if c is None:
        from google import genai
        c = genai.Client(api_key=key)
        _state['clients'][key] = c
    return c


def _is_key_error(exc):
    msg = f'{type(exc).__name__} {exc}'.lower()
    return any(k in msg for k in KEY_ERRORS)


# Try the current key, rotate to the next one when it is exhausted or expired
def _with_gemini_key(fn):
    """Run fn(client) with the current key; on quota/expiry errors rotate through the remaining keys."""
    keys = _keys()
    if not keys:
        raise RuntimeError('no gemini key configured')
    last_exc = None
    for _ in range(len(keys)):
        with _lock:
            idx = _state['key_index'] % len(keys)
        key = keys[idx]
        try:
            return fn(_client(key))
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if _is_key_error(exc):
                logger.warning('Gemini key #%d unusable (%s); rotating to next key', idx + 1, type(exc).__name__)
                with _lock:
                    _state['dead_keys'].add(idx)
                    _state['key_index'] = idx + 1
                continue
            raise
    raise last_exc


# Model missing for this key (404) or overloaded (503): try the next model before giving up on the key
MODEL_ERRORS = ('404', 'not_found', '503', 'unavailable', 'overloaded', 'high demand')


def _models():
    models = list(getattr(settings, 'GEMINI_MODELS', []) or [])
    return models or [settings.GEMINI_MODEL]


def _gemini_generate(prompt, system=None):
    def call(client):
        cfg = None
        if system:
            from google.genai import types
            cfg = types.GenerateContentConfig(system_instruction=system, temperature=0.2)
        last = None
        # Walk the model list for this key; a quota or expiry error bubbles up so the key rotates
        for model in _models():
            try:
                return client.models.generate_content(model=model, contents=prompt, config=cfg).text
            except Exception as exc:  # noqa: BLE001
                msg = f'{type(exc).__name__} {exc}'.lower()
                if any(k in msg for k in MODEL_ERRORS) and not any(k in msg for k in ('429', 'quota', 'exhausted')):
                    last = exc
                    continue
                raise
        # Every model failed on this key: treat it like an unusable key so we rotate
        raise RuntimeError(f'quota/unavailable on all models: {type(last).__name__}')
    return _with_gemini_key(call)


def _gemini_embed(texts):
    def call(client):
        resp = client.models.embed_content(model=settings.GEMINI_EMBED_MODEL, contents=list(texts))
        return [e.values for e in resp.embeddings]
    return _with_gemini_key(call)


# ------------------------------------------------------------------ Ollama (local only)
# Local model only; refuses any non-local URL so data cannot leak by mistake
def _ollama_generate(prompt, system=None, timeout=15):
    url = getattr(settings, 'SANGAM_OLLAMA_URL', 'http://127.0.0.1:11434/api/chat')
    if not url.startswith(('http://127.0.0.1:', 'http://localhost:')):
        raise RuntimeError('ollama url must be local')
    msgs = ([{'role': 'system', 'content': system}] if system else []) + [{'role': 'user', 'content': prompt}]
    body = json.dumps({'model': getattr(settings, 'SANGAM_OLLAMA_MODEL', 'qwen3:8b'), 'messages': msgs, 'stream': False,
                       'options': {'temperature': 0.1, 'num_predict': 400}}).encode('utf8')
    req = Request(url, body, headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(req, timeout=timeout) as r:
        return str(json.load(r).get('message', {}).get('content', ''))[:4000]


# ------------------------------------------------------------------ public API
# Returns text plus why it failed, so callers can pick the right fallback
def generate_detailed(prompt, system=None, timeout=None, retries=1):
    prov = provider()
    if prov not in ('gemini', 'ollama'):
        return LLMResult(None, prov, 'unavailable')
    if prov == 'gemini' and not _keys():
        return LLMResult(None, prov, 'unavailable')
    timeout = timeout or getattr(settings, 'AI_LLM_TIMEOUT_SECONDS', 15)
    # Belt and braces: strip personal data again just before sending
    prompt, _ = strip_pii(prompt)          # defensive: callers strip already
    if system:
        system, _ = strip_pii(system)
    fn = _gemini_generate if prov == 'gemini' else (lambda p, s: _ollama_generate(p, s, timeout))
    error = 'error'
    for _attempt in range(1 + retries):
        fut = _pool.submit(fn, prompt, system)
        try:
            text = fut.result(timeout=timeout)
            if text:
                return LLMResult(text, prov, None)
        except FutTimeout:
            logger.warning('LLM %s timed out after %ss', prov, timeout)
            return LLMResult(None, prov, 'timeout')
        except Exception as exc:  # noqa: BLE001
            logger.warning('LLM %s call failed: %s', prov, type(exc).__name__)
            error = 'unavailable' if isinstance(exc, (OSError, RuntimeError)) else 'error'
    return LLMResult(None, prov, error)


def generate(prompt, system=None, timeout=None):
    return generate_detailed(prompt, system, timeout).text


def embed(texts):
    if provider() != 'gemini' or not _keys():
        return None
    try:
        return _pool.submit(_gemini_embed, texts).result(timeout=getattr(settings, 'AI_LLM_TIMEOUT_SECONDS', 15))
    except Exception as exc:  # noqa: BLE001
        logger.warning('Gemini embed failed: %s', type(exc).__name__)
        return None


# Small live check used by the /ai/health/ endpoint and the demo scripts
def health():
    prov = provider()
    info = {'provider': prov, 'available': False}
    if prov == 'gemini':
        info['keys_configured'] = len(_keys())
        info['keys_marked_unusable'] = len(_state['dead_keys'])
    if prov in ('gemini', 'ollama'):
        r = generate_detailed('Reply with the single word OK.', timeout=25, retries=0)
        info['available'] = bool(r.text)
        info['error'] = r.error
    return info
