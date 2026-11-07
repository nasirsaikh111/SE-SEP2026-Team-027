from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class SangamPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


def list_response(request, queryset_or_list, serialize, legacy_limit=200):
    """Return a plain list (legacy contract) unless ``?page`` or ``?page_size`` is supplied.

    With either parameter the response is the paginated envelope
    ``{count, next, previous, results}`` so existing clients keep working.
    """
    if 'page' in request.query_params or 'page_size' in request.query_params:
        paginator = SangamPagination()
        page = paginator.paginate_queryset(queryset_or_list, request)
        return paginator.get_paginated_response(serialize(page))
    return Response(serialize(queryset_or_list[:legacy_limit]))
