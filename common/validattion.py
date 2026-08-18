from django.utils.translation import gettext_lazy as _


def mandattory_validation(obj, cleaned_data, field_name, field_label):
    value = cleaned_data.get(field_name)
    if value is None:
        obj.add_error(field_name, _("%(label)s is a mandatory field.") % {"label": field_label})
