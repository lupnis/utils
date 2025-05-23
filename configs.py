# -*- coding: utf-8 -*-
import json
import yaml
import toml
import configparser
import aiofiles
from filelock import AsyncFileLock
from pathlib import Path
from typing import Dict, Any, Optional, Union


class ConfigUtils:
    """
    Asynchronous configuration file utility that supports reading and writing configurations
    in multiple formats with file locking for multi-process safety.
    """

    def __init__(self, config_path: Union[str, Path], template: Optional[Dict[str, Any]] = None):
        """
        Initialize the config utility.

        Args:
            config_path: Path to the configuration file
            template: Optional template for initializing new config files
        """
        self.config_path = Path(config_path)
        self.template = template or {}
        self.config = {}
        self.lock_path = str(self.config_path) + ".lock"
        self.lock = AsyncFileLock(
            self.lock_path, timeout=10)  # 10 seconds timeout

    def _get_format(self) -> str:
        """Determine the file format from extension."""
        ext = self.config_path.suffix.lower()
        match ext:
            case '.ini' | '.inf':
                return 'ini'
            case '.json':
                return 'json'
            case '.yaml' | '.yml':
                return 'yaml'
            case '.toml':
                return 'toml'
            case _:
                raise ValueError(f"Unsupported file format: {ext}")

    async def _read_ini(self) -> Dict[str, Any]:
        """Read INI format configuration."""
        config = configparser.ConfigParser()
        async with aiofiles.open(self.config_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        config.read_string(content)
        result = {}
        for section in config.sections():
            result[section] = dict(config[section])
        return result

    async def _read_json(self) -> Dict[str, Any]:
        """Read JSON format configuration."""
        async with aiofiles.open(self.config_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        return dict(json.loads(content))

    async def _read_yaml(self) -> Dict[str, Any]:
        """Read YAML format configuration."""
        async with aiofiles.open(self.config_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        return yaml.safe_load(content)

    async def _read_toml(self) -> Dict[str, Any]:
        """Read TOML format configuration."""
        async with aiofiles.open(self.config_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        return toml.loads(content)

    async def _write_ini(self, config: Dict[str, Any]) -> None:
        """Write configuration in INI format."""
        parser = configparser.ConfigParser()
        for section, values in config.items():
            if not isinstance(values, dict):
                # Handle non-dict values at root level
                if 'DEFAULT' not in parser:
                    parser['DEFAULT'] = {}
                parser['DEFAULT'][section] = str(values)
                continue

            parser[section] = {}
            for key, value in values.items():
                parser[section][key] = str(value)

        async with aiofiles.open(self.config_path, 'w', encoding='utf-8') as f:
            content = ""
            for section in parser.sections():
                content += f"[{section}]\n"
                for key, value in parser[section].items():
                    content += f"{key} = {value}\n"
                content += "\n"
            await f.write(content)

    async def _write_json(self, config: Dict[str, Any]) -> None:
        """Write configuration in JSON format."""
        async with aiofiles.open(self.config_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(config, indent=2))

    async def _write_yaml(self, config: Dict[str, Any]) -> None:
        """Write configuration in YAML format."""
        async with aiofiles.open(self.config_path, 'w', encoding='utf-8') as f:
            await f.write(yaml.dump(config))

    async def _write_toml(self, config: Dict[str, Any]) -> None:
        """Write configuration in TOML format."""
        async with aiofiles.open(self.config_path, 'w', encoding='utf-8') as f:
            await f.write(toml.dumps(config))

    async def read(self) -> Dict[str, Any]:
        """
        Read configuration from file with proper locking.
        If file doesn't exist but template is provided, initializes with template.
        """
        async with self.lock:
            if not self.config_path.exists():
                if self.template:
                    await self.save(self.template)
                    return self.template.copy()
                else:
                    return {}

            file_format = self._get_format()
            try:
                if file_format == 'ini':
                    self.config = await self._read_ini()
                elif file_format == 'json':
                    self.config = await self._read_json()
                elif file_format == 'yaml':
                    self.config = await self._read_yaml()
                elif file_format == 'toml':
                    self.config = await self._read_toml()
                return self.config.copy()
            except Exception as e:
                raise RuntimeError(
                    f"Failed to read config file {self.config_path}: {str(e)}")

    async def save(self, config: Dict[str, Any]) -> None:
        """Save configuration to file with proper locking."""
        self.config = config
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        async with self.lock:
            file_format = self._get_format()
            try:
                if file_format == 'ini':
                    await self._write_ini(config)
                elif file_format == 'json':
                    await self._write_json(config)
                elif file_format == 'yaml':
                    await self._write_yaml(config)
                elif file_format == 'toml':
                    await self._write_toml(config)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to save config to {self.config_path}: {str(e)}")

    async def update(self, new_config: Dict[str, Any]) -> None:
        """Update configuration with new values and save to file."""
        current = await self.read()
        self._deep_update(current, new_config)
        await self.save(current)

    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Recursively update nested dictionary."""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
