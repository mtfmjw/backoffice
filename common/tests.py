from django.test import TestCase

from backoffice.admin import admin_site
from common.admin import PrefectureAdmin
from common.models import Prefecture


class PrefectureAdminImportExportTests(TestCase):
    def test_prefecture_admin_uses_import_export_resource(self):
        admin = PrefectureAdmin(model=Prefecture, admin_site=admin_site)

        self.assertIsNotNone(admin.resource_class)
        self.assertEqual(admin.resource_class.__name__, "PrefectureResource")
