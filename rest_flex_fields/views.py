""" 
This class determines how to optimize ViewSet queries when expanding fields.
"""
from django.db.models import ForeignKey, ManyToManyField, ManyToOneRel, OneToOneRel
from django.core.exceptions import FieldDoesNotExist
from rest_framework import viewsets
from .serializers import import_serializer_class
from .utils import split_list


class FlexFieldsMixin:
    def expand_field(self, field, queryset, serializer=None, query_parts=None, sluggify_fields=False):
        field_parts = field.split('.') if field else []
        serializer = serializer or self.get_serializer()
        simple_slugs = serializer.related_fields if sluggify_fields else []
        many_slugs = serializer.many_related_fields if sluggify_fields else []
        query_parts = query_parts or []
        django_obj = queryset
        select_related_type = None

        queryset = queryset.select_related(*simple_slugs)
        queryset = queryset.prefetch_related(*many_slugs)

        for idx, field in enumerate(field_parts):
            if field == '*':
                for f in serializer.expandable_fields.keys():
                    queryset = self.expand_field(f, queryset, serializer, query_parts, sluggify_fields)

            if field not in serializer.expandable_fields:
                break

            source_field = serializer[field].source
            serializer_class, serializer_settings = serializer.expandable_fields[field]
            serializer_class = import_serializer_class(serializer_class)
            serializer = import_serializer_class(serializer_settings.get('base_serializer_class', serializer_class))()

            try:
                django_obj = django_obj.related_model._meta.get_field(source_field) if idx else django_obj.model._meta.get_field(source_field)
            except FieldDoesNotExist:
                break
            else:
                query_parts.append(field)
                if isinstance(django_obj, (ManyToOneRel, ManyToManyField)):
                    select_related_type = 'prefetch_related'
                elif isinstance(django_obj, (OneToOneRel, ForeignKey)) and not select_related_type:
                    select_related_type = 'select_related'

        related_field = '__'.join(query_parts)
        if select_related_type:
            queryset = getattr(queryset, select_related_type)(related_field)
        return queryset

    def get_queryset(self):
        queryset = super().get_queryset()
        expand = self.request.query_params.get('expand', '')
        sluggify_fields = self.request.query_params.get('identifier') in ('name', 'reference')
        force_sluggify_list = [None] if sluggify_fields else []

        for field in split_list(expand) + force_sluggify_list:
            queryset = self.expand_field(field, queryset, sluggify_fields=sluggify_fields)

        return queryset


class FlexFieldsModelViewSet(FlexFieldsMixin, viewsets.ModelViewSet):
    pass
