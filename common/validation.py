from django.utils.translation import gettext_lazy as _


def mandatory_validation(obj, cleaned_data, field_name, field_label):
    value = cleaned_data.get(field_name)
    if value is None:
        obj.add_error(field_name, _("%(label)s is a mandatory field.") % {"label": field_label})


def time_range_validation(obj, cleaned_data, start_field_name, end_field_name, start_field_label, end_field_label):
    start_time = cleaned_data.get(start_field_name)
    end_time = cleaned_data.get(end_field_name)
    if start_time is not None and end_time is None:
        obj.add_error(
            end_field_name,
            _("%(label)s must be provided when %(start_label)s is provided.") % {"label": end_field_label, "start_label": start_field_label},
        )
    elif start_time is None and end_time is not None:
        obj.add_error(
            start_field_name,
            _("%(label)s must be provided when %(end_label)s is provided.") % {"label": start_field_label, "end_label": end_field_label},
        )
