import importlib
import copy
from rest_framework import serializers
from rest_framework.relations import SlugRelatedField
from rest_flex_fields import split_list, split_levels


class SafeSlugRelatedField(SlugRelatedField):
    def to_representation(self, obj):
        try:
            return super().to_representation(obj)
        except AttributeError:
            return 'Unknown identifier'


class FlexFieldsSerializerMixin:
    """
    A Serializer that takes additional arguments for "fields", "omit" and
    "expand" in order to control which fields are displayed, and whether to
    replace simple values with complex, nested serializations.
    """
    is_flex_field = True

    def __init__(self, *args, **kwargs):
        passed = {
            'expand': kwargs.pop('expand', None),
            'fields': kwargs.pop('fields', None),
            'omit': kwargs.pop('omit', []),
            'parent': kwargs.pop('parent', ''),
            'identifier': kwargs.pop('identifier', None)
        }

        # add excludes from expandable_fields to those on query params
        passed['omit'] += kwargs.pop('exclude', [])

        super(FlexFieldsSerializerMixin, self).__init__(*args, **kwargs)
        expand = self._get_expand_input(passed)
        fields = self._get_fields_input(passed)
        omit = self._get_omit_input(passed)
        expand_field_names, next_expand_field_names = split_levels(expand)
        sparse_field_names, next_sparse_field_names = split_levels(fields)
        omit_field_names, next_omit_field_names = split_levels(omit)
        omit_field_names = set(omit_field_names) - next_omit_field_names.keys()

        expandable_fields_names = self._get_expandable_names(sparse_field_names, omit_field_names)
        forced_expands = [name for name, field in self.fields.items() if isinstance(field, serializers.Serializer)]
        identifier = passed['identifier']

        if identifier or self._can_access_request:
            url_specific_fields = ('view_name', 'lookup_field', 'lookup_url_kwarg', 'format')
            identifier = identifier or self.context['request'].query_params.get('identifier') or self.context['request'].data.get('identifier')
            if identifier in ('id', 'name', 'reference'):
                for name in self.related_fields:
                    kwargs = {k: v for k, v in self.fields[name]._kwargs.items() if k not in url_specific_fields}
                    new_related_field = serializers.PrimaryKeyRelatedField(**kwargs) if identifier == 'id' else SafeSlugRelatedField(identifier, **kwargs)
                    self.fields[name] = new_related_field
                for name in self.many_related_fields:
                    kwargs = {k: v for k, v in self.fields[name].child_relation._kwargs.items() if k not in url_specific_fields}
                    new_related_field = serializers.PrimaryKeyRelatedField(**kwargs) if identifier == 'id' else SafeSlugRelatedField(identifier, **kwargs)
                    self.fields[name].child_relation = new_related_field
                self.fields.pop('url', None)
                self.fields.pop('verbose_url', None)

        if '*' in expand_field_names:
            expand_field_names = self.expandable_fields.keys()

        for name in set(expand_field_names) | set(forced_expands):
            if name not in expandable_fields_names:
                continue

            self.fields[name] = self._make_expanded_field_serializer(
                name, next_expand_field_names, next_sparse_field_names, next_omit_field_names, identifier
            )

    @property
    def related_fields(self):
        return [k for k, v in self.fields.items() if isinstance(v, serializers.HyperlinkedRelatedField) and not isinstance(v, serializers.HyperlinkedIdentityField)]

    @property
    def many_related_fields(self):
        return [k for k, v in self.fields.items() if isinstance(v, serializers.ManyRelatedField) and isinstance(v.child_relation, serializers.HyperlinkedRelatedField)]

    def _make_expanded_field_serializer(self, name, nested_expands, nested_includes, nested_omits, identifier):
        """
        Returns an instance of the dynamically created nested serializer. 
        """
        field_options = self.expandable_fields[name]
        serializer_class = field_options[0]
        serializer_settings = copy.deepcopy(field_options[1])
        serializer_settings['parent'] = name

        if name in nested_expands:
            serializer_settings['expand'] = nested_expands[name]

        if name in nested_includes:
            serializer_settings['fields'] = nested_includes[name]

        if name in nested_omits:
            serializer_settings['omit'] = nested_omits[name]

        if serializer_settings.get('source') == name:
            del serializer_settings['source']

        serializer_settings['identifier'] = identifier
        serializer_class = import_serializer_class(serializer_class)
        assert getattr(serializer_class, 'is_flex_field', False), '{} does not support being an expandable_field; try inheriting from FlexFieldsSerializerMixin'.format(serializer_class)
        return serializer_class(**serializer_settings)

    def _get_expandable_names(self, sparse_field_names, omit_field_names):
        field_names = set(self.fields.keys())
        expandable_field_names = set(self.expandable_fields.keys())

        if not sparse_field_names or '*' in sparse_field_names:
            sparse_field_names = field_names

        allowed_field_names = set(sparse_field_names) - set(omit_field_names)

        for field_name in field_names - allowed_field_names:
            self.fields.pop(field_name)

        return list(expandable_field_names & allowed_field_names)

    @property
    def expandable_fields(self):
        return getattr(getattr(self, 'Meta', None), "expandable_fields", {})

    @property
    def _can_access_request(self):
        return not self.parent and hasattr(self, 'context') and self.context.get('request', None)

    def _get_sparse_input(self, passed_settings, param):
        value = passed_settings.get(param)

        if value:
            return value

        if not self._can_access_request:
            return None

        fields = self.context['request'].query_params.get(param)
        return [f for f in split_list(fields) if f.startswith(passed_settings['parent'])] if fields else None

    def _get_omit_input(self, passed_settings):
        return self._get_sparse_input(passed_settings, 'omit')

    def _get_fields_input(self, passed_settings):
        return self._get_sparse_input(passed_settings, 'fields')

    def _get_expand_input(self, passed_settings):
        return self._get_sparse_input(passed_settings, 'expand')


def import_serializer_class(location):
    """
    Resolves a dot-notation string to serializer class.
    <app>.<SerializerName> will automatically be interpreted as:
    <app>.serializers.<SerializerName>
    """
    if not isinstance(location, str):
        return location

    pieces = location.split('.')
    class_name = pieces.pop()

    if not pieces:
        raise ValueError('Please ensure class string is fully qualified with its containing module')

    if pieces[ len(pieces)-1 ] != 'serializers':
        pieces.append('serializers')

    module = importlib.import_module( '.'.join(pieces) )
    return getattr(module, class_name)


class FlexFieldsModelSerializer(FlexFieldsSerializerMixin, serializers.ModelSerializer):
    pass
