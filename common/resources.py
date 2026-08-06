from import_export import resources
from .models import Municipality

class MunicipalityResource(resources.ModelResource):
    class Meta:
        model = Municipality
        fields = (
            "id",
            "name",
            "province__name",
            "province__code",
            "province__region__name",
            "province__region__code",
        )