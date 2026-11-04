Contributing to Box
===================

Thank you for looking into supporting Box. Any constructive input
is greatly appreciated!

Questions and Ideas
-------------------

Even if you don't have code contributions, but just an idea, or a question about
Box, please feel free to open an issue!

Reporting Bugs
--------------

- Please include sample code and traceback (or unexpected behavior)
  of the error you are experiencing.

- Also include Python version and Operating System.

Development Setup
-----------------

Box uses `uv <https://docs.astral.sh/uv/>`_ to manage the development environment, and
`ruff <https://docs.astral.sh/ruff/>`_ for linting and formatting (line length 120, Black compatible style).
All project metadata and tool configuration lives in ``pyproject.toml``.

.. code:: bash

        # create the environment (all test dependencies plus the dev tools)
        uv sync --group dev

        # run the tests
        uv run pytest

        # lint, format and type check
        uv run ruff check --fix .
        uv run ruff format .
        uv run mypy box

        # optional: run the checks automatically before each commit
        uv run pre-commit install

To test the Cython compiled version, install the package in the environment without build isolation
(so the Cython from the ``dev`` group is used), then run the tests again:

.. code:: bash

        uv pip install -e . --no-build-isolation
        uv run --no-sync pytest

Build the (pure Python) source distribution and wheel with ``uv build``, or the compiled wheel for your
platform with ``uv build --no-build-isolation``.

When you change dependencies in ``pyproject.toml`` run ``uv lock`` and commit the updated ``uv.lock``.

Pull Requests
-------------

- Follow PEP8 (``ruff check`` and ``ruff format --check`` should pass)

- Select to merge into `develop` branch, NOT `master`

- New features should have
    - Reasoning for addition in pull request
    - Docstring with code block example and parameters
    - Tests with as much coverage as reasonable
    - Tests should go through both sad and happy paths

- Bug fixes should include
    - Explain under which circumstances the bug occurs in the pull request
    - Tests for new happy and sad paths
    - Test proving error without new code

- Update CHANGES.rst to include new feature or fix

- Add yourself to AUTHORS.rst!
