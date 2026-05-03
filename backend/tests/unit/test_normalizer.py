"""Unit tests for normalizer service"""

import pytest

from app.services.normalizer import flatten, select_records


class TestSelectRecords:
    """Tests for select_records function"""

    def test_select_records_with_jsonpath(self):
        """Test extracting records with JSONPath"""
        payload = {"data": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}

        records = list(select_records(payload, "$.data[*]"))

        assert len(records) == 2
        assert records[0]["id"] == 1
        assert records[1]["name"] == "Bob"

    def test_select_records_without_path(self):
        """Test selecting records without JSONPath (use payload as-is)"""
        payload = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

        records = list(select_records(payload, None))

        assert len(records) == 2
        assert records[0]["id"] == 1

    def test_select_records_single_object(self):
        """Test selecting single object converts to list"""
        payload = {"data": {"id": 1, "name": "Alice"}}

        records = list(select_records(payload, "$.data"))

        assert len(records) == 1
        assert records[0]["id"] == 1

    def test_select_records_nested_path(self):
        """Test selecting from deeply nested structure"""
        payload = {"response": {"result": {"items": [{"id": 1}, {"id": 2}]}}}

        records = list(select_records(payload, "$.response.result.items[*]"))

        assert len(records) == 2

    def test_select_records_empty_result(self):
        """Test selecting with path that yields no results"""
        payload = {"data": []}

        records = list(select_records(payload, "$.data[*]"))

        assert len(records) == 0

    def test_select_records_invalid_path_raises_error(self):
        """Test that non-list, non-dict result raises error"""
        payload = {"data": "not a list"}

        with pytest.raises(ValueError, match="did not resolve to a list or object"):
            list(select_records(payload, "$.data"))


class TestFlatten:
    """Tests for flatten function"""

    def test_flatten_simple_dict(self):
        """Test flattening simple nested dictionary"""
        obj = {"name": "Alice", "age": 30}

        result = flatten(obj)

        assert result == {"name": "Alice", "age": 30}

    def test_flatten_nested_dict(self):
        """Test flattening nested dictionary"""
        obj = {
            "user": {"name": "Alice", "email": "alice@example.com"},
            "status": "active",
        }

        result = flatten(obj)

        assert result == {
            "user.name": "Alice",
            "user.email": "alice@example.com",
            "status": "active",
        }

    def test_flatten_deeply_nested(self):
        """Test flattening deeply nested structure"""
        obj = {"company": {"employee": {"personal": {"name": "Alice"}}}}

        result = flatten(obj)

        assert result == {"company.employee.personal.name": "Alice"}

    def test_flatten_with_list_values(self):
        """Test flattening keeps list values as-is"""
        obj = {"user": "Alice", "tags": ["python", "data"]}

        result = flatten(obj)

        assert result == {"user": "Alice", "tags": ["python", "data"]}

    def test_flatten_empty_dict(self):
        """Test flattening empty dictionary"""
        obj = {}

        result = flatten(obj)

        assert result == {}

    def test_flatten_with_custom_separator(self):
        """Test flattening with custom separator"""
        obj = {"user": {"name": "Alice"}}

        result = flatten(obj, sep="_")

        assert result == {"user_name": "Alice"}

    def test_flatten_preserves_none_values(self):
        """Test that None values are preserved"""
        obj = {"user": {"name": "Alice", "email": None}}

        result = flatten(obj)

        assert result == {"user.name": "Alice", "user.email": None}

    def test_flatten_mixed_nested_structure(self):
        """Test flattening complex mixed structure"""
        obj = {
            "id": 1,
            "user": {"name": "Alice", "address": {"city": "NYC", "zip": "10001"}},
            "active": True,
        }

        result = flatten(obj)

        assert result == {
            "id": 1,
            "user.name": "Alice",
            "user.address.city": "NYC",
            "user.address.zip": "10001",
            "active": True,
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
