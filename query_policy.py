"""Constrained query parameters, not SQL expressions or a permission system."""
import math
import re


OPERATORS = {'=', '!=', '<>', '>', '>=', '<', '<=', 'like', 'not like',
             'in', 'not in', 'between', 'is', 'descendants of', 'ancestors of',
             'not descendants of', 'not ancestors of'}


def validate_doctype(doctype):
    if not isinstance(doctype, str) or not re.fullmatch(r'[\w][\w -]{0,139}', doctype):
        raise ValueError('DocType must be a plain name of at most 140 characters')
    return doctype


def validate_field(field):
    if not isinstance(field, str) or not 1 <= len(field) <= 280:
        raise ValueError('Query fields must be plain field names, optionally qualified')
    parts = field.split('.')
    if len(parts) == 2:
        validate_doctype(parts[0])
    if len(parts) not in (1, 2) or not parts[-1].isidentifier():
        raise ValueError('Query fields cannot contain expressions, aliases or SQL syntax')
    return field


def validate_fields(fields):
    if fields is None:
        return None
    if not isinstance(fields, list) or not 1 <= len(fields) <= 50:
        raise ValueError('fields must contain 1 to 50 plain field names; read a named parent for full details')
    for field in fields:
        validate_field(field)
    return fields


def validate_order_by(order_by):
    if order_by is None:
        return None
    if not isinstance(order_by, str) or not 1 <= len(order_by) <= 500:
        raise ValueError('order_by must be a bounded field/direction list')
    terms = order_by.split(',')
    if len(terms) > 3:
        raise ValueError('order_by supports at most three fields')
    for term in terms:
        pieces = term.strip().rsplit(None, 1)
        field = pieces[0] if len(pieces) == 2 and pieces[1].lower() in ('asc', 'desc') else term.strip()
        validate_field(field)
    return order_by


def _scalar(value):
    if value is None or type(value) in (bool, int):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    if isinstance(value, str) and len(value) <= 4096:
        return
    raise ValueError('Filter values must be bounded strings or finite scalar values')


def _condition(field, operator, value):
    validate_field(field)
    if not isinstance(operator, str) or operator.lower() not in OPERATORS:
        raise ValueError('Unsupported filter operator')
    operator = operator.lower()
    if operator in ('in', 'not in', 'between'):
        if not isinstance(value, list) or not 1 <= len(value) <= 1000:
            raise ValueError('Membership/range filters require a bounded array')
        if operator == 'between' and len(value) != 2:
            raise ValueError('between requires exactly two values')
        for item in value:
            _scalar(item)
    else:
        _scalar(value)


def normalize_filters(filters):
    if filters is None:
        return None
    if isinstance(filters, dict):
        if len(filters) > 100:
            raise ValueError('At most 100 filter conditions are supported')
        for field, value in filters.items():
            if isinstance(value, list) and len(value) == 2:
                _condition(field, value[0], value[1])
            else:
                _condition(field, '=', value)
        return filters
    if not isinstance(filters, list):
        raise ValueError('filters must be an array of [field, operator, value] conditions')
    if filters and isinstance(filters[0], str):
        filters = [filters]
    if len(filters) > 100:
        raise ValueError('At most 100 filter conditions are supported')
    for condition in filters:
        if not isinstance(condition, list) or len(condition) not in (3, 4):
            raise ValueError('Each filter must be [field, operator, value] or [doctype, field, operator, value]')
        if len(condition) == 4:
            validate_doctype(condition[0])
        _condition(*condition[-3:])
    return filters
