"""Trusted-code tool registration with per-request views and live revocation.

This is a capability catalog, not a Python sandbox or a full JSON Schema engine.
Handlers retain domain/type checks; the registry checks top-level contracts.
"""
import json
import math
import re
from dataclasses import dataclass
from decimal import Decimal
from threading import RLock
from types import MappingProxyType


RESERVED = {'confirm', 'reconcile', 'create_document', 'cancel_document',
            'execute_sql', 'shell', 'http_get', 'set_endpoint'}


@dataclass(frozen=True)
class _Tool:
    definition_json: str
    handler: object
    effect: str
    version: str
    decimal_arguments: bool

    def definition(self):
        return json.loads(self.definition_json)


def _check_arguments(parameters, args):
    if not isinstance(args, dict):
        raise ValueError('Tool arguments must be a JSON object')
    if any(not isinstance(key, str) for key in args):
        raise ValueError('Tool argument names must be strings')
    missing = set(parameters.get('required', [])) - args.keys()
    if missing:
        raise ValueError('Missing required tool arguments: ' + ', '.join(sorted(missing)))
    properties = parameters.get('properties', {})
    if parameters.get('additionalProperties') is False and args.keys() - properties.keys():
        raise ValueError('Unknown tool arguments: ' + ', '.join(sorted(args.keys() - properties.keys())))
    for name, value in args.items():
        kind = properties.get(name, {}).get('type')
        valid = {'string': lambda: isinstance(value, str),
                 'array': lambda: isinstance(value, list),
                 'object': lambda: isinstance(value, dict),
                 'null': lambda: value is None,
                 'boolean': lambda: type(value) is bool,
                 'integer': lambda: type(value) is int,
                 'number': lambda: (type(value) in (int, float, Decimal)
                                    and (not isinstance(value, float) or math.isfinite(value))
                                    and (not isinstance(value, Decimal) or value.is_finite()))}
        if kind in valid and not valid[kind]():
            raise ValueError(f'Tool argument {name} must have type {kind}')


def _reject_constant(value):
    raise ValueError(f'Non-finite JSON constant is not supported: {value}')


class ToolView:
    def __init__(self, owner, tools):
        self._owner = owner
        self._tools = MappingProxyType(tools)

    def definitions(self):
        return [tool.definition() for tool in self._tools.values()]

    def metadata(self, name):
        tool = self._tools.get(name)
        return None if tool is None else {'version': tool.version, 'effect': tool.effect,
                                          'decimal_arguments': tool.decimal_arguments}

    def invoke(self, name, args, context):
        tool = self._tools.get(name)
        # The lock establishes when a call starts. Revocation blocks later
        # calls; it cannot cancel a handler/network operation already started.
        with self._owner._lock:
            if (tool is None or name not in self._owner._enabled
                    or self._owner._tools.get(name) is not tool):
                raise ValueError(f'Tool not available: {name}')
            parameters = tool.definition()['function']['parameters']
            _check_arguments(parameters, args)
        return tool.handler(context, args)

    def invoke_json(self, name, raw_args, context):
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f'Tool not available: {name}')
        if not isinstance(raw_args, str):
            raise ValueError('Tool arguments must be encoded as JSON text')
        options = {'parse_constant': _reject_constant}
        if tool.decimal_arguments:
            options['parse_float'] = Decimal
        return self.invoke(name, json.loads(raw_args or '{}', **options), context)


class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._enabled = set()
        self._lock = RLock()

    def register(self, definition, handler, *, effect='read', version='1', decimal_arguments=False):
        # Copy schema ownership. Callers cannot mutate a registered contract.
        definition = json.loads(json.dumps(definition, allow_nan=False))
        if not isinstance(definition, dict) or not isinstance(definition.get('function'), dict):
            raise ValueError('A function tool definition object is required')
        function = definition.get('function', {})
        name = function.get('name')
        if definition.get('type') != 'function' or not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}', name):
            raise ValueError('A named function tool definition is required')
        if name in RESERVED or effect not in ('read', 'prepare'):
            raise ValueError('Model tools may only read or prepare; privileged actions stay outside the registry')
        parameters = function.get('parameters')
        if not isinstance(parameters, dict) or parameters.get('type') != 'object':
            raise ValueError('Tool parameters must describe an object')
        properties = parameters.get('properties', {})
        required = parameters.get('required', [])
        if (not isinstance(properties, dict) or not isinstance(required, list)
                or any(not isinstance(key, str) or key not in properties for key in required)):
            raise ValueError('Tool required arguments must be declared properties')
        kinds = {'string', 'number', 'integer', 'boolean', 'object', 'array', 'null'}
        for parameter in properties.values():
            if not isinstance(parameter, dict):
                raise ValueError('Each tool parameter must describe a schema object')
            kind = parameter.get('type')
            if kind is not None and (not isinstance(kind, str) or kind not in kinds):
                raise ValueError('Registry supports simple top-level schema types; adapt complex contracts in trusted code')
        parameters.setdefault('additionalProperties', False)
        if not callable(handler) or not isinstance(version, str) or not version:
            raise ValueError('A callable handler and nonempty version are required')
        tool = _Tool(json.dumps(definition, allow_nan=False), handler, effect, version, bool(decimal_arguments))
        with self._lock:
            if name in self._tools:
                raise ValueError(f'Tool already registered: {name}')
            self._tools[name] = tool
            self._enabled.add(name)
        return handler

    def tool(self, definition, **options):
        def decorate(handler):
            return self.register(definition, handler, **options)
        return decorate

    def set_enabled(self, name, enabled):
        if type(enabled) is not bool:
            raise ValueError('enabled must be a boolean')
        with self._lock:
            if name not in self._tools:
                raise ValueError(f'Tool not registered: {name}')
            if enabled:
                self._enabled.add(name)
            else:
                self._enabled.discard(name)

    def unregister(self, name):
        with self._lock:
            if name not in self._tools:
                raise ValueError(f'Tool not registered: {name}')
            del self._tools[name]
            self._enabled.discard(name)

    def snapshot(self):
        with self._lock:
            return ToolView(self, {name: tool for name, tool in self._tools.items() if name in self._enabled})

    def definitions(self):
        return self.snapshot().definitions()

    def describe(self):
        with self._lock:
            return [{'name': name, 'version': tool.version, 'effect': tool.effect,
                     'enabled': name in self._enabled} for name, tool in self._tools.items()]

    def clone(self):
        other = ToolRegistry()
        with self._lock:
            other._tools = self._tools.copy()
            other._enabled = self._enabled.copy()
        return other
