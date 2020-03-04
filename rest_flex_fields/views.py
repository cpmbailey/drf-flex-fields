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
        field_parts = field.split('.')
        serializer = serializer or self.get_serializer()
        simple_slugs = serializer.related_fields if sluggify_fields else []
        many_slugs = serializer.many_related_fields if sluggify_fields else []
        query_parts = query_parts or []
        django_obj = queryset

        for slug in simple_slugs:
            queryset = queryset.select_related(slug)
        for slug in many_slugs:
            queryset = queryset.prefetch_related(slug)

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

        related_field = '__'.join(query_parts)
        if isinstance(django_obj, (OneToOneRel, ForeignKey)):
            queryset = queryset.select_related(related_field)
        elif isinstance(django_obj, (ManyToOneRel, ManyToManyField)):
            queryset = queryset.prefetch_related(related_field)
        return queryset

    def get_queryset(self):
        queryset = super().get_queryset()
        expand = self.request.query_params.get('expand', '')
        sluggify_fields = self.request.query_params.get('identifier') in ('name', 'reference')

        for field in split_list(expand):
            queryset = self.expand_field(field, queryset, sluggify_fields=sluggify_fields)

        return queryset


class FlexFieldsModelViewSet(FlexFieldsMixin, viewsets.ModelViewSet):
    pass
