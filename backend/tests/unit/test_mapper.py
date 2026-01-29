"""Unit tests for mapper service"""
import pytest
from app.services.mapper import (
    trim, upper, lower, to_int, to_float, to_bool,
    apply_transform, apply_transforms,
    map_row_with_column_mappings, map_rows
)
from app.db.models.column_mapping import ColumnMapping


class TestTransformFunctions:
    """Tests for individual transform functions"""
    
    def test_trim_function(self):
        """Test trim removes whitespace"""
        assert trim("  hello  ") == "hello"
        assert trim("hello") == "hello"
        assert trim(123) == 123  # Non-string returns as-is
    
    def test_upper_function(self):
        """Test upper converts to uppercase"""
        assert upper("hello") == "HELLO"
        assert upper("HELLO") == "HELLO"
        assert upper(123) == 123  # Non-string returns as-is
    
    def test_lower_function(self):
        """Test lower converts to lowercase"""
        assert lower("HELLO") == "hello"
        assert lower("hello") == "hello"
        assert lower(123) == 123  # Non-string returns as-is
    
    def test_to_int_function(self):
        """Test to_int converts to integer"""
        assert to_int("123") == 123
        assert to_int(123) == 123
        assert to_int(None) is None
        assert to_int("") is None
    
    def test_to_float_function(self):
        """Test to_float converts to float"""
        assert to_float("123.45") == 123.45
        assert to_float(123) == 123.0
        assert to_float(None) is None
        assert to_float("") is None
    
    def test_to_bool_function(self):
        """Test to_bool converts to boolean"""
        assert to_bool("true") is True
        assert to_bool("TRUE") is True
        assert to_bool("1") is True
        assert to_bool("yes") is True
        assert to_bool("false") is False
        assert to_bool("0") is False
        assert to_bool(True) is True
        assert to_bool(1) is True


class TestApplyTransform:
    """Tests for apply_transform function"""
    
    def test_apply_single_transform(self):
        """Test applying single transform"""
        assert apply_transform("  hello  ", "trim") == "hello"
        assert apply_transform("hello", "upper") == "HELLO"
    
    def test_apply_transform_none(self):
        """Test applying no transform returns original"""
        assert apply_transform("hello", None) == "hello"
    
    def test_apply_transform_unknown_raises_error(self):
        """Test unknown transform raises ValueError"""
        with pytest.raises(ValueError, match="Unknown transform"):
            apply_transform("hello", "unknown_transform")


class TestApplyTransforms:
    """Tests for apply_transforms with JSON rules"""
    
    def test_apply_transforms_dict_format(self):
        """Test applying transforms from dict format"""
        rules = '{"trim": true, "upper": true}'
        assert apply_transforms("  hello  ", rules) == "HELLO"
    
    def test_apply_transforms_list_format(self):
        """Test applying transforms from list format"""
        rules = '["trim", "upper"]'
        assert apply_transforms("  hello  ", rules) == "HELLO"
    
    def test_apply_transforms_no_rules(self):
        """Test no rules returns original value"""
        assert apply_transforms("hello", None) == "hello"
    
    def test_apply_transforms_invalid_json(self):
        """Test invalid JSON returns original value"""
        assert apply_transforms("hello", "{invalid json}") == "hello"
    
    def test_apply_transforms_chained(self):
        """Test chained transforms"""
        rules = '["trim", "lower"]'
        assert apply_transforms("  HELLO  ", rules) == "hello"
    
    def test_apply_transforms_with_dict_object(self):
        """Test applying transforms with dict object (not string)"""
        rules = {"trim": True, "upper": True}
        assert apply_transforms("  hello  ", rules) == "HELLO"


class TestMapRowWithColumnMappings:
    """Tests for map_row_with_column_mappings"""
    
    def test_map_row_simple_mapping(self):
        """Test simple field mapping"""
        source_row = {
            "customer_id": "123",
            "customer_name": "Alice"
        }
        
        mappings = [
            ColumnMapping(
                task_id=1,
                source_field="customer_id",
                dest_column="CUST_ID",
                is_active=True
            ),
            ColumnMapping(
                task_id=1,
                source_field="customer_name",
                dest_column="NAME",
                is_active=True
            )
        ]
        
        result = map_row_with_column_mappings(source_row, mappings)
        
        assert result == {
            "CUST_ID": "123",
            "NAME": "Alice"
        }
    
    def test_map_row_with_transforms(self):
        """Test mapping with transforms"""
        source_row = {
            "full_name": "  alice  "
        }
        
        mappings = [
            ColumnMapping(
                task_id=1,
                source_field="full_name",
                dest_column="NAME",
                transform_rules='["trim", "upper"]',
                is_active=True
            )
        ]
        
        result = map_row_with_column_mappings(source_row, mappings)
        
        assert result == {"NAME": "ALICE"}
    
    def test_map_row_skips_inactive_mappings(self):
        """Test inactive mappings are skipped"""
        source_row = {
            "field1": "value1",
            "field2": "value2"
        }
        
        mappings = [
            ColumnMapping(
                task_id=1,
                source_field="field1",
                dest_column="FIELD1",
                is_active=True
            ),
            ColumnMapping(
                task_id=1,
                source_field="field2",
                dest_column="FIELD2",
                is_active=False  # Inactive
            )
        ]
        
        result = map_row_with_column_mappings(source_row, mappings)
        
        assert result == {"FIELD1": "value1"}
        assert "FIELD2" not in result
    
    def test_map_row_missing_source_field(self):
        """Test mapping when source field is missing"""
        source_row = {
            "field1": "value1"
        }
        
        mappings = [
            ColumnMapping(
                task_id=1,
                source_field="field2",  # Missing in source
                dest_column="FIELD2",
                is_active=True
            )
        ]
        
        result = map_row_with_column_mappings(source_row, mappings)
        
        assert result == {"FIELD2": None}
    
    def test_map_row_no_transforms(self):
        """Test mapping without transforms"""
        source_row = {
            "email": "alice@example.com"
        }
        
        mappings = [
            ColumnMapping(
                task_id=1,
                source_field="email",
                dest_column="EMAIL",
                transform_rules=None,
                is_active=True
            )
        ]
        
        result = map_row_with_column_mappings(source_row, mappings)
        
        assert result == {"EMAIL": "alice@example.com"}


class TestMapRows:
    """Tests for map_rows batch function"""
    
    def test_map_multiple_rows(self):
        """Test mapping multiple rows"""
        source_rows = [
            {"id": "1", "name": "Alice"},
            {"id": "2", "name": "Bob"}
        ]
        
        mappings = [
            ColumnMapping(
                task_id=1,
                source_field="id",
                dest_column="ID",
                is_active=True
            ),
            ColumnMapping(
                task_id=1,
                source_field="name",
                dest_column="NAME",
                transform_rules='["upper"]',
                is_active=True
            )
        ]
        
        results = map_rows(source_rows, mappings)
        
        assert len(results) == 2
        assert results[0] == {"ID": "1", "NAME": "ALICE"}
        assert results[1] == {"ID": "2", "NAME": "BOB"}
    
    def test_map_empty_rows(self):
        """Test mapping empty list"""
        mappings = [
            ColumnMapping(
                task_id=1,
                source_field="id",
                dest_column="ID",
                is_active=True
            )
        ]
        
        results = map_rows([], mappings)
        
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
