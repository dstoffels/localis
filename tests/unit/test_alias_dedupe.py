from ingest.utils.strings import dedupe, name_key


def test_name_key_folds_spelling_variants():
    """variants that only differ in accents, case, punctuation, abbreviations or filler words share a key"""
    assert name_key("St. Barthélemy") == name_key("Saint-Barthelemy") == name_key("saint barthélémy")
    assert name_key("Dem. Rep. Congo") == name_key("Democratic Republic of the Congo")
    assert name_key("Farre Is.") == name_key("Farre Islands")
    assert name_key("St. Kitts & Nevis") == name_key("Saint Kitts and Nevis")
    assert name_key("Saint Barts") != name_key("Saint Barths")


def test_dedupe_keeps_fullest_variant_and_drops_name_variants():
    """one alias per key, the fullest written form, with variants of the record's own name removed"""
    aliases = [
        "Saint Barthelemy", "St. Barthélemy", "St barthelemy", "Saint-Barthélémy",
        "St. Barts", "St barts", "Saint Barts", "St. Barths", "Saint Barths",
        "Collectivite de Saint-Barthelemy", "Collectivité de Saint-Barthélemy",
    ]
    assert dedupe(aliases, exclude=("Saint Barthélemy",)) == [
        "Collectivité de Saint-Barthélemy",
        "Saint Barths",
        "Saint Barts",
    ]
