import os
import re
import tempfile
from contextlib import contextmanager
from sys import stdout
from time import sleep

import schedule
from config_schema import CONFIG_SCHEMA
from loguru import logger
from pycliarr.api import CliArrError
from pyconfigparser import ConfigError, ConfigFileNotFoundError, configparser
from radarr_renamarr import RadarrRenamarr
from sonarr_renamarr import SonarrRenamarr
from sonarr_series_scanner import SonarrSeriesScanner as SonarrSeriesScanner


class Main:
    """
    This class handles config parsing, and job scheduling
    """

    RUN_SCHEDULER = True

    def __init__(self):
        logger_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "{extra[instance]} | "
            "{extra[item]} | "
            "<level>{message}</level>"
        )
        logger.configure(extra={"instance": "", "item": ""})  # Default values
        logger.remove()
        logger.add(stdout, format=logger_format)

    def __external_cron(self) -> bool:
        return os.getenv("EXTERNAL_CRON", "false").lower() == "true"

    def __sonarr_series_scanner_job(self, sonarr_config):
        try:
            SonarrSeriesScanner(
                name=sonarr_config.name,
                url=sonarr_config.url,
                api_key=sonarr_config.api_key,
                hours_before_air=sonarr_config.series_scanner.hours_before_air,
            ).scan()
        except CliArrError as exc:
            logger.error(exc)

    def __schedule_sonarr_series_scanner(self, sonarr_config):
        self.__sonarr_series_scanner_job(sonarr_config)

        if sonarr_config.series_scanner.hourly_job and not self.__external_cron():
            # Add a random delay of +-5 minutes between jobs
            schedule.every(55).to(65).minutes.do(
                self.__sonarr_series_scanner_job, sonarr_config=sonarr_config
            )

    def __sonarr_renamarr_job(self, sonarr_config):
        try:
            SonarrRenamarr(
                name=sonarr_config.name,
                url=sonarr_config.url,
                api_key=sonarr_config.api_key,
                analyze_files=sonarr_config.renamarr.analyze_files,
            ).scan()
        except CliArrError as exc:
            logger.error(exc)

    def __schedule_radarr_renamarr(self, radarr_config):
        self.__radarr_renamarr_job(radarr_config)

        if radarr_config.renamarr.hourly_job and not self.__external_cron():
            # Add a random delay of +-5 minutes between jobs
            schedule.every(55).to(65).minutes.do(
                self.__radarr_renamarr_job, radarr_config=radarr_config
            )

    def __radarr_renamarr_job(self, radarr_config):
        try:
            RadarrRenamarr(
                name=radarr_config.name,
                url=radarr_config.url,
                api_key=radarr_config.api_key,
                analyze_files=radarr_config.renamarr.analyze_files,
            ).scan()
        except CliArrError as exc:
            logger.error(exc)

    def __schedule_sonarr_renamarr(self, sonarr_config):
        self.__sonarr_renamarr_job(sonarr_config)

        if sonarr_config.renamarr.hourly_job and not self.__external_cron():
            # Add a random delay of +-5 minutes between jobs
            schedule.every(55).to(65).minutes.do(
                self.__sonarr_renamarr_job, sonarr_config=sonarr_config
            )

    def start(self) -> None:
        try:
            # configparser uses cwd, for file opens.
            # Change to root directory, to look for config in /config/config.yml
            with set_directory("/"):
                # Load raw YAML first to expand environment variables
                config_path = "/config/config.yml"
                if not os.path.exists(config_path):
                    config_path = "/config/config.yaml"
                
                # Read and expand environment variables in YAML content
                with open(config_path, 'r') as file:
                    yaml_content = file.read()
                
                # Pattern to match ${VAR_NAME} or ${VAR_NAME:-default}
                pattern = r'\$\{([^}]+)\}'
                
                def replace_var(match):
                    var_expr = match.group(1)
                    if ':-' in var_expr:
                        var_name, default_value = var_expr.split(':-', 1)
                        return os.getenv(var_name.strip(), default_value)
                    else:
                        var_name = var_expr.strip()
                        env_value = os.getenv(var_name)
                        if env_value is None:
                            logger.warning(f"Environment variable '{var_name}' not found, keeping original value")
                            return match.group(0)  # Return the original ${VAR_NAME} if not found
                        return env_value
                
                expanded_yaml = re.sub(pattern, replace_var, yaml_content)
                
                # Write the expanded content to a temporary file for configparser
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
                    temp_file.write(expanded_yaml)
                    temp_config_path = temp_file.name
                
                try:
                    # Use configparser with the expanded config
                    config = configparser.get_config(CONFIG_SCHEMA, config_dir=os.path.dirname(temp_config_path), file_name=os.path.basename(temp_config_path))
                finally:
                    # Clean up temporary file
                    os.unlink(temp_config_path)
                    
        except ConfigFileNotFoundError as exc:
            logger.error(
                "Unable to locate config file, please check volume mount paths, config must be mounted at /config/config.yaml"
            )
            logger.error(exc)
            exit(1)
        except ConfigError as exc:
            logger.error(
                "Unable to parse config file, Please see example config for comparison -- https://github.com/hollanbm/renamarr/blob/main/docker/config.yml.example"
            )
            logger.error(exc)
            exit(1)
        except FileNotFoundError as exc:
            logger.error(
                "Unable to read or parse config file, please check if /config/config.yml exists and is valid YAML"
            )
            logger.error(exc)
            exit(1)

        for sonarr_config in config.sonarr:
            if not sonarr_config.series_scanner.enabled and not (
                sonarr_config.renamarr.enabled or sonarr_config.existing_renamer.enabled
            ):
                with logger.contextualize(instance=sonarr_config.name):
                    logger.warning(
                        "Possible config error? -- No jobs configured for current instance"
                    )
                    logger.warning(
                        "Please see example config for comparison -- https://github.com/hollanbm/renamarr/blob/main/docker/config.yml.example"
                    )
                    continue
            if sonarr_config.series_scanner.enabled:
                self.__schedule_sonarr_series_scanner(sonarr_config)
            if sonarr_config.renamarr.enabled:
                self.__schedule_sonarr_renamarr(sonarr_config)
            elif sonarr_config.existing_renamer.enabled:
                logger.warning(
                    "sonarr[].existing_renamer config option, has been renamed to sonarr[].renamarr. Please update config, as this will stop working in future versions"
                )
                logger.warning(
                    "Please see example config for comparison -- https://github.com/hollanbm/renamarr/blob/main/docker/config.yml.example"
                )
                self.__schedule_sonarr_renamarr(sonarr_config)

        for radarr_config in config.radarr:
            if radarr_config.renamarr.enabled:
                self.__schedule_radarr_renamarr(radarr_config)
            else:
                with logger.contextualize(instance=radarr_config.name):
                    logger.warning(
                        "Possible config error? -- No jobs configured for current instance"
                    )
                    logger.warning(
                        "Please see example config for comparison -- https://github.com/hollanbm/renamarr/blob/main/docker/config.yml.example"
                    )

        if schedule.get_jobs():
            while self.RUN_SCHEDULER:
                schedule.run_pending()
                sleep(1)


@contextmanager
def set_directory(path):
    oldpwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)


if __name__ == "__main__":  # pragma nocover
    Main().start()  # pragma: no cover
