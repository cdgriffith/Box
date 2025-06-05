#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from box import Box, BoxList


class TestNotification:
    def test_box_on_change_callback(self):
        """Test that on_change callback is called for Box operations"""
        changes = []
        
        def on_change(box, key, value, action, is_root):
            changes.append((key, value, action, is_root))
        
        b = Box(on_change=on_change)
        
        # Test set
        b.a = 1
        assert changes == [('a', 1, 'set', True)]
        
        # Test update
        changes.clear()
        b.update({'b': 2, 'c': 3})
        assert len(changes) == 2
        assert ('b', 2, 'set', True) in changes
        assert ('c', 3, 'set', True) in changes
        
        # Test delete
        changes.clear()
        del b.a
        assert changes == [('a', None, 'delete', True)]
        
        # Test clear
        changes.clear()
        b.clear()
        assert changes == [(None, None, 'clear', True)]
        
    def test_box_nested_notification(self):
        """Test that notifications propagate from nested boxes"""
        changes = []
        
        def on_change(box, key, value, action, is_root):
            changes.append((key, value, action, is_root))
        
        b = Box({'nested': {'value': 1}}, on_change=on_change)
        changes.clear()  # Clear initial setup changes
        
        # Modify nested value
        b.nested.value = 2
        # Should get one notification from the root object about the child change
        assert len(changes) == 1
        assert changes[0][0] == 'nested'  # From parent box
        assert changes[0][2] == 'child_change'
        assert changes[0][3] is False  # This is a child change, not a root change
        
    def test_boxlist_on_change_callback(self):
        """Test that on_change callback is called for BoxList operations"""
        changes = []
        
        def on_change(boxlist, index, value, action, is_root):
            changes.append((index, value, action, is_root))
        
        bl = BoxList([1, 2, 3], on_change=on_change)
        changes.clear()  # Clear initial setup changes
        
        # Test append
        bl.append(4)
        assert changes == [(3, 4, 'append', True)]
        
        # Test insert
        changes.clear()
        bl.insert(1, 5)
        assert changes == [(1, 5, 'insert', True)]
        
        # Test setitem
        changes.clear()
        bl[0] = 10
        assert changes == [(0, 10, 'set', True)]
        
        # Test pop
        changes.clear()
        bl.pop()
        assert len(changes) == 1
        assert changes[0][1] is None
        assert changes[0][2] == 'pop'
        
        # Test remove
        changes.clear()
        bl.remove(5)
        assert len(changes) == 1
        assert changes[0][1] is None
        assert changes[0][2] == 'remove'
        
        # Test clear
        changes.clear()
        bl.clear()
        assert changes == [(None, None, 'clear', True)]
        
    def test_mixed_nested_notification(self):
        """Test notifications with mixed Box and BoxList nesting"""
        changes = []
        
        def on_change(obj, key_or_index, value, action, is_root):
            changes.append((type(obj).__name__, key_or_index, action, is_root))
        
        b = Box({
            'my_items': [
                {'name': 'item1'},
                {'name': 'item2'}
            ]
        }, on_change=on_change)
        changes.clear()
        
        # Modify item in list
        b.my_items[0].name = 'updated'
        # Should get one notification from the root Box about the final change
        # The change propagates: nested Box -> BoxList -> root Box
        assert len(changes) == 1
        assert changes[0] == ('Box', 'my_items', 'child_change', False)  # From root Box, but it's a child change
        
    def test_parent_references_set_correctly(self):
        """Test that parent references are set correctly"""
        b = Box({'nested': {'value': 1}, 'list': [1, 2, 3]})
        
        # Check nested box parent reference
        assert b.nested._parent_ref is b
        assert b.nested._parent_key == 'nested'
        
        # Check list parent reference
        assert b.list._parent_ref is b
        assert b.list._parent_key == 'list'
        
    def test_parent_references_update_on_reassignment(self):
        """Test that parent references update when values are reassigned"""
        b1 = Box()
        b2 = Box()
        
        # Create nested box by assignment
        b1.nested = {'value': 1}
        nested = b1.nested
        assert nested._parent_ref is b1
        assert nested._parent_key == 'nested'
        
        # Reassign the same data to b2
        b2.nested = b1.nested
        # The new box created in b2 should have b2 as parent
        assert b2.nested._parent_ref is b2
        assert b2.nested._parent_key == 'nested'
        
    def test_callback_error_handling(self):
        """Test that errors in callbacks don't disrupt operations"""
        def bad_callback(box, key, value, action, is_root):
            raise RuntimeError("Callback error")
        
        b = Box(on_change=bad_callback)
        
        # Should not raise an error
        b.a = 1
        assert b.a == 1
        
        # Operations should complete successfully despite callback errors
        b.update({'b': 2})
        assert b.b == 2
        
        del b.a
        assert 'a' not in b
        
    def test_notification_with_box_dots(self):
        """Test notifications work with box_dots enabled"""
        changes = []
        
        def on_change(box, key, value, action, is_root):
            changes.append((key, value, action, is_root))
        
        b = Box(box_dots=True, default_box=True, on_change=on_change)
        
        # Set nested value using dots
        b['a.b.c'] = 1
        # Should create intermediate boxes and notify for each
        assert len(changes) >= 1
        assert any(c[0] == 'c' and c[1] == 1 for c in changes)
        
    def test_frozen_box_no_notifications(self):
        """Test that frozen boxes don't allow changes and thus no notifications"""
        changes = []
        
        def on_change(box, key, value, action, is_root):
            changes.append((key, value, action, is_root))
        
        b = Box({'a': 1}, frozen_box=True, on_change=on_change)
        changes.clear()  # Clear initial setup
        
        # Should raise error and not notify
        with pytest.raises(Exception):  # BoxError
            b.a = 2
        assert len(changes) == 0

    def test_is_root_parameter_functionality(self):
        """Test that is_root parameter correctly identifies root vs child changes"""
        root_changes = []
        child_changes = []
        
        def on_change(obj, key, value, action, is_root):
            if is_root:
                root_changes.append((key, value, action))
            else:
                child_changes.append((key, value, action))
        
        # Test with nested Box structure
        b = Box({'level1': {'level2': {'value': 1}}}, on_change=on_change)
        root_changes.clear()
        child_changes.clear()
        
        # Change at root level
        b.root_key = 'test'
        assert len(root_changes) == 1
        assert root_changes[0] == ('root_key', 'test', 'set')
        assert len(child_changes) == 0
        
        # Change at nested level
        root_changes.clear()
        child_changes.clear()
        b.level1.level2.value = 42
        
        # Should get one child notification indicating a nested change occurred
        assert len(child_changes) == 1  # One child change notification
        assert len(root_changes) == 0   # No direct root changes
        
        # The change should be a child_change notification about level1
        assert child_changes[0] == ('level1', b.level1, 'child_change')
        
    def test_boxlist_is_root_parameter(self):
        """Test is_root parameter with BoxList at root level"""
        root_changes = []
        child_changes = []
        
        def on_change(obj, index, value, action, is_root):
            if is_root:
                root_changes.append((index, value, action))
            else:
                child_changes.append((index, value, action))
        
        # BoxList at root level
        bl = BoxList([1, 2, 3], on_change=on_change)
        root_changes.clear()
        child_changes.clear()
        
        # Change at root level
        bl.append(4)
        assert len(root_changes) == 1
        assert root_changes[0] == (3, 4, 'append')
        assert len(child_changes) == 0
        
    def test_mixed_nesting_is_root_parameter(self):
        """Test is_root parameter with mixed Box/BoxList nesting"""
        all_changes = []
        
        def on_change(obj, key_or_index, value, action, is_root):
            all_changes.append((type(obj).__name__, key_or_index, action, is_root))
        
        # Complex nested structure
        b = Box({
            'my_items': [
                {'name': 'item1', 'data': {'score': 100}},
                {'name': 'item2', 'data': {'score': 200}}
            ]
        }, on_change=on_change)
        all_changes.clear()
        
        # Deep nested change
        b.my_items[0].data.score = 150
        
        # Check that we get notifications with correct is_root values
        # With our new logic, we should only get one notification at the root level
        # indicating that a child change occurred
        assert len(all_changes) == 1
        assert all_changes[0][0] == 'Box'  # Root object type
        assert all_changes[0][1] == 'my_items'  # Key that changed
        assert all_changes[0][2] == 'child_change'  # Action type
        assert all_changes[0][3] is False  # This is a child change, not a direct root change