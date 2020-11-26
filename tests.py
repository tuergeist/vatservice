import unittest

from vatservice import _is_well_formated


class HelperTestCase(unittest.TestCase):
    def false(self, vat):
        self.assertFalse(_is_well_formated(vat), vat)

    def true(self, vat):
        self.assertTrue((_is_well_formated(vat)), vat)

    def test_vat_format_valid_AT(self):
        self.true('ATU99998888')
        self.true('ATU00000000')

    def test_var_format_invalid_AT(self):
        self.false('ATU9999888')
        self.false('ATU000000001')
        self.false('ATX00000001')
        self.false('ATUR0000001')  # char

    def test_vat_format_valid_DEEEPT(self):
        self.true('DE199998888')
        self.true('EE100000000')
        self.true('PT123456789')

    def test_var_format_invalid_DEEEPT(self):
        self.false('DE1199998888')
        self.false('EE00000000')
        self.false('PT0000000I')  # char

    def test_len_8(self):
        for cntry in ('SI', 'MT', 'LU', 'HU', 'FI', 'DK'):
            self.true(f"{cntry}12345678")
            self.false(f"{cntry}1234567")  # short
            self.false(f"{cntry}123456789")  # long
