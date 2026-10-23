from django.test import SimpleTestCase


class CartModuleTest(SimpleTestCase):
    def test_cart_module_is_available(self):
        import cart
        self.assertIsNotNone(cart)
