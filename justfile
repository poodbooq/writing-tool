venv := "./.venv"
bin := venv + "/bin"
python := bin + "/python"
pip := bin + "/pip"
wt := bin + "/wt"
ruff := bin + "/ruff"
mypy := bin + "/mypy"
pytest := bin + "/pytest"
local_bin := "/home/" + env("USER", "ykostr") + "/.local/bin"

setup:
    python3 -m venv {{venv}}
    {{pip}} install -e ".[dev]"

install: setup
    mkdir -p {{local_bin}}
    ln -sf "$(realpath {{wt}})" "{{local_bin}}/wt"
    @echo "wt installed to {{local_bin}}/wt (make sure it's in your PATH)"

run *ARGS:
    {{wt}} {{ARGS}}

test:
    {{pytest}} -xvs

coverage:
    {{pytest}} --cov=writing_tool --cov-report=term-missing -xvs

lint:
    {{ruff}} check .

typecheck:
    {{mypy}} writing_tool/

check: lint typecheck test
