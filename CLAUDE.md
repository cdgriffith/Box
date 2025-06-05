# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the python-box repository.

## Project Overview
Python-box is a library that provides advanced Python dictionaries with dot notation access, supporting nested structures, file loading, and optional Cython compilation for performance.

## Build Commands
- Install dependencies: `uv sync --all-extras`
- Build source distribution and wheel: `uv build`
- Build with development dependencies: `uv sync` (installs dev dependencies from pyproject.toml)
- Clean build artifacts: `rm -rf build/ dist/ *.egg-info box/*.c box/*.so`

## Testing
- Run all tests: `pytest`
- Run specific test file: `pytest test/test_notification.py`
- Run with coverage: `pytest --cov=box`
- Run notification tests specifically: `pytest test/test_notification.py -v`

## Linting and Formatting
- Format code: `black .`
- Type check: `mypy box/`

## Cython Compilation
The project supports optional Cython compilation for performance:
- Cython extensions are automatically built during `uv build`
- Manual compilation: `python setup.py build_ext --inplace`
- Cython is required in build environment (included in dev dependencies)

## Code Conventions
- Python 3.9+ required
- Use snake_case for variables/functions, PascalCase for classes
- Type annotations in .pyi stub files
- Follow existing patterns for Box/BoxList implementations
- All new features should include comprehensive tests

## Project Structure
- `box/` - Main package with core classes (Box, BoxList, ConfigBox, etc.)
- `test/` - Test suite including notification feature tests
- `pyproject.toml` - Modern Python project configuration
- `setup.py` - Minimal setup for Cython extension building

## Dependencies
- No runtime dependencies (pure Python)
- Optional extras for file format support: yaml, toml, msgpack
- Development dependencies managed via uv in pyproject.toml

## Notification Feature
The Box and BoxList classes include a notification system:
- Pass `on_change` callback to constructors
- Changes propagate up to parent objects
- Supports all modification operations (set, delete, append, etc.)
- See `test/test_notification.py` for usage examples