import gzip
import struct
import pytest
from ingest.shared.models import CurrencyModel, ScriptModel, SubdivisionModel
from ingest.utils import index


def _read(path) -> str:
    return gzip.decompress(path.read_bytes()).decode("utf-8")


class TestDump:
    """DUMP"""

    def test_writes_quotes_unquoted(self, tmp_path):
        """should write a value holding a quote as it is, since the runtime splits rows on tabs rather than parsing csv"""
        index.dump_data([CurrencyModel(id=1, name='The "Peso"', alpha3="XPS", numeric=None)], tmp_path / "demo.tsv.gz")

        assert _read(tmp_path / "demo.tsv.gz") == 'The "Peso"\tXPS\t\n'

    @pytest.mark.parametrize("name", ["Tab\tName", "Line\nName", "Return\rName"])
    def test_raises_on_row_breaking_value(self, tmp_path, name):
        """should raise on a value holding a tab or line break, which would split its row"""
        with pytest.raises(ValueError):
            index.dump_data([CurrencyModel(id=1, name=name, alpha3="XPS", numeric=None)], tmp_path / "demo.tsv.gz")

    def test_raises_on_separator_in_cell_value(self):
        """should raise on a multi-value cell's value holding "|", which the runtime would split in two"""
        with pytest.raises(ValueError):
            ScriptModel(id=1, name="Demo", alpha4="Dmoo", numeric=None, aliases=["a|b"]).to_row()

    def test_row_fields_skip_unshipped(self):
        """should leave a model's UNSHIPPED_FIELDS out of its row, keeping the rest in field order"""
        assert SubdivisionModel.row_fields()[0] == "name"
        assert not {"id", "hashid", "parent_iso_code"} & set(SubdivisionModel.row_fields())

    def test_lookup_splits_keys(self, tmp_path):
        """should write all-digit keys to the integer index and the rest to the string index, each sorted"""
        index.dump_lookup_index([CurrencyModel(id=1, name="B", alpha3="BBB", numeric=8), CurrencyModel(id=2, name="A", alpha3="AAA", numeric=4)], tmp_path)

        assert _read(tmp_path / "lookup_index_str.tsv.gz") == "aaa\t2\nbbb\t1\n"
        assert _read(tmp_path / "lookup_index_int.tsv.gz") == "4\t2\n8\t1\n"

    def test_lookup_raises_on_shared_key(self, tmp_path):
        """should raise on a lookup key two records hold, writing no index"""
        currencies = [CurrencyModel(id=1, name="A", alpha3="AAA", numeric=None), CurrencyModel(id=2, name="B", alpha3="AAA", numeric=None)]

        with pytest.raises(ValueError):
            index.dump_lookup_index(currencies, tmp_path)
        assert not (tmp_path / "lookup_index_str.tsv.gz").exists()

    def test_postings_little_endian(self, tmp_path):
        """should pack each key's sorted ids as little-endian uint32, with its offset and count"""
        index._dump_inverted_index({("b",): [9], ("a",): [2, 1]}, tmp_path / "demo")

        assert gzip.decompress((tmp_path / "demo.bin.gz").read_bytes()) == struct.pack("<3I", 1, 2, 9)
        assert _read(tmp_path / "demo_offsets.tsv.gz") == "a\t0\t2\nb\t2\t1\n"

    def test_gzip_deterministic(self, tmp_path):
        """should write byte-identical files for identical data, with no timestamp in the gzip header"""
        currencies = [CurrencyModel(id=1, name="A", alpha3="AAA", numeric=None)]
        index.dump_data(currencies, tmp_path / "a.tsv.gz")
        index.dump_data(currencies, tmp_path / "b.tsv.gz")

        assert (tmp_path / "a.tsv.gz").read_bytes() == (tmp_path / "b.tsv.gz").read_bytes()

    def test_registry_numbers_ids_by_row(self, monkeypatch, tmp_path):
        """should number a registry's records by row before writing them, whatever ids they held"""
        monkeypatch.setattr(index, "STAGED_DATA_PATH", tmp_path)
        currencies = [CurrencyModel(id=7, name="B", alpha3="BBB", numeric=None), CurrencyModel(name="A", alpha3="AAA", numeric=None)]

        index.dump_registry("demo", currencies, queryable=False)

        assert [c.id for c in currencies] == [1, 2]
        assert _read(tmp_path / "demo" / "lookup_index_str.tsv.gz") == "aaa\t2\nbbb\t1\n"
