from rest_flex_fields import FlexFieldsModelViewSet
from tests.testapp.serializers import PetSerializer
from tests.testapp.models import Pet


class PetViewSet(FlexFieldsModelViewSet):
    serializer_class = PetSerializer
    queryset = Pet.objects.all()
