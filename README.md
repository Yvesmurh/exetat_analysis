What's this project about?
This project analyzes Exetat results and provides a Flask-based dashboard backed by local data (see `json_files/`).

How to run the app (recommended)
1. Create and activate a Python venv (optional but recommended):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # or install `pip install -e .` if available
```

2. From the project root, run the app using the module runner (this ensures `src` is importable):

```bash
./run.sh
```

Alternative approaches to avoid ModuleNotFoundError: No module named 'src'
- Run from the project root: `python -m src.app.app` (or `python src/app/app.py`) so that the project root is on `sys.path`.
- Export `PYTHONPATH` to include the project root: `export PYTHONPATH="$PWD"` and then run `python src/app/app.py`.
- Install the package in editable mode: `pip install -e .` and then run `python -m src.app.app` or `flask run`.

Why this error occurs
When you run `python app.py` from `src/app`, Python's search path does not include the repository root and therefore can't find the top-level `src` package. Running as a module from project root or installing the package resolves this.

If your workflow needs other convenience commands, you can run `FLASK_APP=src.app.app flask run` from project root after installation or setting `PYTHONPATH`.