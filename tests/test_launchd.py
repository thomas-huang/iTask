"""Tests for launchd.py - Launchd operations"""

import tempfile
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, call
from lib.launchd import LaunchdManager


class TestLaunchdManager:
    """Test suite for LaunchdManager class"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def launchd_manager(self, temp_dir):
        """Create LaunchdManager instance with temp directory"""
        return LaunchdManager(launch_agents_dir=temp_dir)

    @pytest.fixture
    def sample_plist(self, temp_dir):
        """Create a sample plist file"""
        plist_path = temp_dir / "com.itask.test.plist"
        plist_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.itask.test</string>
</dict>
</plist>'''
        plist_path.write_text(plist_content)
        return plist_path

    def test_init_creates_directory(self, temp_dir):
        """Test that initialization creates launch agents directory"""
        launch_dir = temp_dir / "LaunchAgents"
        manager = LaunchdManager(launch_agents_dir=launch_dir)
        assert launch_dir.exists()

    @patch('subprocess.run')
    def test_load_plist(self, mock_run, launchd_manager, sample_plist):
        """Test loading a plist file"""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

        launchd_manager.load(str(sample_plist))

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert 'launchctl' in args
        assert 'load' in args
        assert str(sample_plist) in args

    @patch('subprocess.run')
    def test_load_plist_failure(self, mock_run, launchd_manager, sample_plist):
        """Test that loading failure raises exception"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='Load failed: operation not permitted'
        )

        with pytest.raises(RuntimeError, match="Failed to load"):
            launchd_manager.load(str(sample_plist))

    @patch('subprocess.run')
    def test_unload_plist(self, mock_run, launchd_manager, sample_plist):
        """Test unloading a plist file"""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

        launchd_manager.unload(str(sample_plist))

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert 'launchctl' in args
        assert 'unload' in args
        assert str(sample_plist) in args

    @patch('subprocess.run')
    def test_unload_plist_not_loaded(self, mock_run, launchd_manager, sample_plist):
        """Test that unloading non-existent plist doesn't raise error"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='Could not find specified service'
        )

        # Should not raise exception for "not found" errors
        launchd_manager.unload(str(sample_plist))

    @patch('subprocess.run')
    def test_is_loaded_true(self, mock_run, launchd_manager):
        """Test checking if service is loaded (returns True)"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{\n    "Label" = "com.itask.test";\n}',
            stderr=''
        )

        result = launchd_manager.is_loaded("com.itask.test")
        assert result is True

    @patch('subprocess.run')
    def test_is_loaded_false(self, mock_run, launchd_manager):
        """Test checking if service is loaded (returns False)"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='Could not find service'
        )

        result = launchd_manager.is_loaded("com.itask.nonexistent")
        assert result is False

    @patch('subprocess.run')
    def test_start_service(self, mock_run, launchd_manager):
        """Test starting a service"""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

        launchd_manager.start("com.itask.test")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert 'launchctl' in args
        assert 'start' in args
        assert 'com.itask.test' in args

    @patch('subprocess.run')
    def test_stop_service(self, mock_run, launchd_manager):
        """Test stopping a service"""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

        launchd_manager.stop("com.itask.test")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert 'launchctl' in args
        assert 'stop' in args
        assert 'com.itask.test' in args

    @patch('subprocess.run')
    def test_list_loaded_services(self, mock_run, launchd_manager):
        """Test listing loaded services"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='123\t0\tcom.itask.test1\n456\t0\tcom.itask.test2\n',
            stderr=''
        )

        services = launchd_manager.list_loaded()

        assert 'com.itask.test1' in services
        assert 'com.itask.test2' in services

    @patch('subprocess.run')
    def test_list_loaded_filters_itask(self, mock_run, launchd_manager):
        """Test that list_loaded can filter itask services"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='123\t0\tcom.itask.test1\n456\t0\tcom.apple.test\n',
            stderr=''
        )

        services = launchd_manager.list_loaded(filter_itask=True)

        assert 'com.itask.test1' in services
        assert 'com.apple.test' not in services

    def test_get_plist_path(self, launchd_manager):
        """Test getting plist path for a label"""
        path = launchd_manager.get_plist_path("com.itask.test")
        assert "com.itask.test.plist" in str(path)

    def test_plist_exists(self, launchd_manager, sample_plist):
        """Test checking if plist file exists"""
        assert launchd_manager.plist_exists("com.itask.test") is True
        assert launchd_manager.plist_exists("com.itask.nonexistent") is False

    def test_remove_plist(self, launchd_manager, sample_plist):
        """Test removing plist file"""
        assert sample_plist.exists()

        launchd_manager.remove_plist("com.itask.test")

        assert not sample_plist.exists()

    def test_remove_nonexistent_plist(self, launchd_manager):
        """Test that removing nonexistent plist doesn't raise error"""
        # Should not raise exception
        launchd_manager.remove_plist("com.itask.nonexistent")

    @patch('subprocess.run')
    def test_reload_service(self, mock_run, launchd_manager, sample_plist):
        """Test reloading a service (unload + load)"""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

        launchd_manager.reload(str(sample_plist))

        # Should call unload then load
        assert mock_run.call_count == 2
        first_call_args = mock_run.call_args_list[0][0][0]
        second_call_args = mock_run.call_args_list[1][0][0]

        assert 'unload' in first_call_args
        assert 'load' in second_call_args
