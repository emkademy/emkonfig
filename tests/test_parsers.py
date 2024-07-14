from emkonfig.parsers import ReferenceKeyParser


class TestReferenceKeyParser:
    def test_is_reference_key(self):
        assert ReferenceKeyParser.is_reference_key("${key}")
        assert ReferenceKeyParser.is_reference_key("${key[0].some_other_key}")
        assert not ReferenceKeyParser.is_reference_key("${key.yaml}")
        assert not ReferenceKeyParser.is_reference_key("key")
        assert not ReferenceKeyParser.is_reference_key("${key")
        assert not ReferenceKeyParser.is_reference_key("key}")
