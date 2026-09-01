import unittest


class ServiceArchitectureTests(unittest.TestCase):
    def test_core_domain_services_import(self):
        from app.services import (
            assignment_service,
            inventory_service,
            license_service,
            permissions,
            stock_service,
        )

        for module in (
            assignment_service,
            inventory_service,
            license_service,
            permissions,
            stock_service,
        ):
            self.assertIsNotNone(module)

    def test_domain_service_functions_exist(self):
        from app.services import assignment_service, inventory_service, license_service, stock_service

        self.assertTrue(hasattr(inventory_service, "create_inventory"))
        self.assertTrue(hasattr(inventory_service, "update_inventory"))
        self.assertTrue(hasattr(assignment_service, "assign_inventory"))
        self.assertTrue(hasattr(stock_service, "create_stock_entry"))
        self.assertTrue(hasattr(license_service, "create_license"))


if __name__ == "__main__":
    unittest.main()
