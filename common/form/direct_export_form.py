# app_name/forms.py
from import_export.forms import ExportForm


class DirectExportForm(ExportForm):
    """
    Export form that completely removes the field-selection checkboxes,
    forcing django-import-export to use the resource's predefined fields.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the export_fields selection box
        if "export_fields" in self.fields:
            del self.fields["export_fields"]
