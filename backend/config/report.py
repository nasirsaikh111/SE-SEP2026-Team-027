"""/project-report/: the project documentation in docs/*.md plus a live endpoint index.

The endpoint index is generated from the OpenAPI schema at request time, so it always
matches the deployed code.
"""
from functools import lru_cache

import markdown
from django.conf import settings
from django.shortcuts import render

HTTP_METHODS = ('get', 'post', 'put', 'patch', 'delete')


@lru_cache(maxsize=1)
def endpoint_index():
    from drf_spectacular.generators import SchemaGenerator
    schema = SchemaGenerator().get_schema(request=None, public=True)
    rows = []
    for path, operations in schema.get('paths', {}).items():
        for method in HTTP_METHODS:
            op = operations.get(method)
            if op:
                rows.append({'method': method.upper(), 'path': path, 'tag': (op.get('tags') or ['other'])[0],
                             'summary': op.get('summary', '')})
    return sorted(rows, key=lambda r: (r['tag'], r['path'], HTTP_METHODS.index(r['method'].lower())))


def load_sections():
    sections = []
    docs_dir = settings.SANGAM_DOCS_DIR
    if not docs_dir.is_dir():
        return sections
    for path in sorted(docs_dir.glob('*.md')):
        text = path.read_text(encoding='utf8')
        md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'sane_lists'])
        html = md.convert(text)
        title = next((line.lstrip('# ').strip() for line in text.splitlines() if line.startswith('# ')), path.stem)
        sections.append({'id': path.stem, 'title': title, 'html': html})
    return sections


def project_report(request):
    return render(request, 'sangam/project_report.html', {
        'sections': load_sections(), 'endpoints': endpoint_index(), 'docs_dir_found': settings.SANGAM_DOCS_DIR.is_dir(),
    })
