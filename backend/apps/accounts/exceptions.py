"""Standardized API error responses.

Every error body is a JSON object with ``detail`` (human-readable message) and
``code`` (machine-readable). Field validation errors are kept at the top level
(DRF's original contract) and also repeated under ``errors``.
"""
from rest_framework.views import exception_handler


def _first_message(data):
    if isinstance(data, (list, tuple)):
        return _first_message(data[0]) if data else ''
    if isinstance(data, dict):
        if 'detail' in data:
            return _first_message(data['detail'])
        for key, value in data.items():
            message = _first_message(value)
            return message if key == 'non_field_errors' else f'{key}: {message}'
        return ''
    return str(data)


def sangam_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    code = getattr(exc, 'default_code', 'error')
    if hasattr(exc, 'get_codes'):
        codes = exc.get_codes()
        if isinstance(codes, str):
            code = codes
    if isinstance(data, dict):
        body = dict(data)
        if 'detail' not in body:
            body['errors'] = data
    else:
        body = {'errors': data}
    body['detail'] = _first_message(data)
    body['code'] = code
    body['status_code'] = response.status_code
    response.data = body
    return response
