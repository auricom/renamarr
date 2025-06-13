import os
import tempfile
from unittest.mock import patch

import pytest
from config_schema import CONFIG_SCHEMA
from main import Main
from pyconfigparser import configparser

# disable config caching
configparser.hold_an_instance = False


class TestEnvironmentVariables:
    @pytest.fixture
    def env_vars_config_content(self) -> str:
        """
        Config content with environment variables
        """
        return """
sonarr:
  - name: tv
    url: https://sonarr.tld:8989
    api_key: ${SONARR_API_KEY:-default-sonarr-key}
    renamarr:
      enabled: true
      hourly_job: false
      analyze_files: true
    series_scanner:
      enabled: false
      hourly_job: false
radarr:
  - name: movies
    url: https://radarr.tld:7878
    api_key: ${RADARR_API_KEY:-default-radarr-key}
    renamarr:
      enabled: true
      hourly_job: false
      analyze_files: false
"""

    def test_env_var_substitution_with_values(self, env_vars_config_content, mocker):
        """Test that environment variables are properly substituted when they exist"""
        # Set environment variables
        test_sonarr_key = "test-sonarr-api-key-123"
        test_radarr_key = "test-radarr-api-key-456"
        
        with patch.dict(os.environ, {
            'SONARR_API_KEY': test_sonarr_key,
            'RADARR_API_KEY': test_radarr_key
        }):
            # Create temporary config file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
                temp_file.write(env_vars_config_content)
                temp_config_path = temp_file.name

            try:
                # Mock the config file path
                mocker.patch('os.path.exists').return_value = True
                mocker.patch('builtins.open', mocker.mock_open(read_data=env_vars_config_content))
                
                # Mock configparser to use our temporary file
                def mock_get_config(schema, config_dir, file_name):
                    return configparser.get_config(schema, config_dir=os.path.dirname(temp_config_path), file_name=os.path.basename(temp_config_path))
                
                mocker.patch('pyconfigparser.configparser.get_config', side_effect=mock_get_config)
                
                # Mock the scanner classes to prevent actual API calls
                mocker.patch('main.SonarrRenamarr')
                mocker.patch('main.RadarrRenamarr')
                
                # Disable scheduler
                Main.RUN_SCHEDULER = False
                
                # Start the application
                main_instance = Main()
                main_instance.start()
                
                # Verify that the mocked scanners were called with the correct API keys
                from main import SonarrRenamarr, RadarrRenamarr
                
                SonarrRenamarr.assert_called_once()
                RadarrRenamarr.assert_called_once()
                
                # Check the arguments passed to the constructors
                sonarr_call_args = SonarrRenamarr.call_args
                radarr_call_args = RadarrRenamarr.call_args
                
                assert sonarr_call_args.kwargs['api_key'] == test_sonarr_key
                assert radarr_call_args.kwargs['api_key'] == test_radarr_key
                
            finally:
                os.unlink(temp_config_path)

    def test_env_var_substitution_with_defaults(self, env_vars_config_content, mocker):
        """Test that default values are used when environment variables don't exist"""
        # Ensure environment variables are not set
        with patch.dict(os.environ, {}, clear=True):
            # Create temporary config file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
                temp_file.write(env_vars_config_content)
                temp_config_path = temp_file.name

            try:
                # Mock the config file path
                mocker.patch('os.path.exists').return_value = True
                mocker.patch('builtins.open', mocker.mock_open(read_data=env_vars_config_content))
                
                # Mock configparser to use our temporary file
                def mock_get_config(schema, config_dir, file_name):
                    return configparser.get_config(schema, config_dir=os.path.dirname(temp_config_path), file_name=os.path.basename(temp_config_path))
                
                mocker.patch('pyconfigparser.configparser.get_config', side_effect=mock_get_config)
                
                # Mock the scanner classes to prevent actual API calls
                mocker.patch('main.SonarrRenamarr')
                mocker.patch('main.RadarrRenamarr')
                
                # Disable scheduler
                Main.RUN_SCHEDULER = False
                
                # Start the application
                main_instance = Main()
                main_instance.start()
                
                # Verify that the mocked scanners were called with the default API keys
                from main import SonarrRenamarr, RadarrRenamarr
                
                SonarrRenamarr.assert_called_once()
                RadarrRenamarr.assert_called_once()
                
                # Check the arguments passed to the constructors
                sonarr_call_args = SonarrRenamarr.call_args
                radarr_call_args = RadarrRenamarr.call_args
                
                assert sonarr_call_args.kwargs['api_key'] == "default-sonarr-key"
                assert radarr_call_args.kwargs['api_key'] == "default-radarr-key"
                
            finally:
                os.unlink(temp_config_path)

    def test_env_var_without_default_keeps_original(self, mocker):
        """Test that env vars without defaults keep original value when var doesn't exist"""
        config_content = """
sonarr:
  - name: tv
    url: https://sonarr.tld:8989
    api_key: ${SONARR_API_KEY}
    renamarr:
      enabled: true
      hourly_job: false
      analyze_files: true
    series_scanner:
      enabled: false
      hourly_job: false
"""
        
        # Ensure environment variable is not set
        with patch.dict(os.environ, {}, clear=True):
            # Create temporary config file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
                temp_file.write(config_content)
                temp_config_path = temp_file.name

            try:
                # Mock the config file path
                mocker.patch('os.path.exists').return_value = True
                mocker.patch('builtins.open', mocker.mock_open(read_data=config_content))
                
                # Mock configparser to use our temporary file
                def mock_get_config(schema, config_dir, file_name):
                    return configparser.get_config(schema, config_dir=os.path.dirname(temp_config_path), file_name=os.path.basename(temp_config_path))
                
                mocker.patch('pyconfigparser.configparser.get_config', side_effect=mock_get_config)
                
                # Mock the scanner classes to prevent actual API calls
                mocker.patch('main.SonarrRenamarr')
                
                # Mock logger to capture warning
                mock_logger_warning = mocker.patch('main.logger.warning')
                
                # Disable scheduler
                Main.RUN_SCHEDULER = False
                
                # Start the application
                main_instance = Main()
                main_instance.start()
                
                # Verify warning was logged
                mock_logger_warning.assert_called_with("Environment variable 'SONARR_API_KEY' not found, keeping original value")
                
                # Verify that the mocked scanner was called with the original ${} value
                from main import SonarrRenamarr
                SonarrRenamarr.assert_called_once()
                
                sonarr_call_args = SonarrRenamarr.call_args
                assert sonarr_call_args.kwargs['api_key'] == "${SONARR_API_KEY}"
                
            finally:
                os.unlink(temp_config_path)
