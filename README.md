## hakken : deep agent 

> to add hakken pakage 
```bash
# backup current pyproject.toml (if present), replace with a valid one, install editable, and verify import
cp pyproject.toml pyproject.toml.bak 2>/dev/null || true

cat > pyproject.toml <<'EOF'
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "hakken"
version = "0.1.0"
description = "Deep Agent framework"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.64.0",
    "python-dotenv>=0.9.9",
    "setuptools>=80.9.0",
    "tavily-python>=0.7.11",
]

[tool.setuptools.packages.find]
where = ["."]
EOF

pip3 install -e . && python3 - <<'PY'
try:
    import hakken
    print("OK —", getattr(hakken, "__file__", "(no __file__)"))
except Exception as e:
    import traceback, sys
    print("IMPORT FAILED:", e, file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
PY
```