import unicodedata
import pytest
from localis.utils.strings import normalize


class TestNormalize:
    """NORMALIZE"""

    @pytest.mark.parametrize(
        "s, expected",
        [
            ("São Paulo", "sao paulo"),
            ("Łódź", "lodz"),
            ("Straße", "strasse"),
            ("Ærøskøbing", "aeroskobing"),
            ("Þórshöfn", "thorshofn"),
            ("Diyarbakır", "diyarbakir"),
            ("İzmir", "izmir"),
            ("Gəncə", "ganca"),
            ("Əli Bayramlı", "ali bayramli"),
            ("ǝǝ", "aa"),
            ("Hawaiʻi", "hawai`i"),
            ("O’Higgins", "o'higgins"),
            ("ＴＯＫＹＯ", "tokyo"),
            ("  Saint   Barthélemy ", "saint barthelemy"),
        ],
    )
    def test_latin(self, s, expected):
        """should fold Latin text to lowercase ASCII."""
        assert normalize(s) == expected

    @pytest.mark.parametrize("s", ["Москва", "Київ", "Αθήνα", "القاهرة", "北京市", "서울특별시", "मुंबई", "กรุงเทพมหานคร"])
    def test_other_scripts(self, s):
        """should keep other scripts as written, casefolded."""
        assert normalize(s) == unicodedata.normalize("NFC", s.casefold())

    def test_mixed_scripts(self):
        """should fold only the Latin part of mixed-script text."""
        assert normalize("Sidi Sénoussi سيدي سنوسي") == "sidi senoussi سيدي سنوسي"
