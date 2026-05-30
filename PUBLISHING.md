# Publish django-tickets to PyPI

Package: **django-tickets**  
PyPI account: [pypi.org/manage/account](https://pypi.org/manage/account/)

---

## 1. Create a PyPI account

1. Register at [pypi.org/account/register](https://pypi.org/account/register/)
2. Verify your email
3. Open [pypi.org/manage/account](https://pypi.org/manage/account/)

---

## 2. Create an API token (recommended)

1. Go to [pypi.org/manage/account/token](https://pypi.org/manage/account/token/)
2. Click **Add API token**
3. Scope: **Entire account** (first time) or limit to project `django-tickets` after first upload
4. Copy the token (`pypi-...`) — you will not see it again

Save the token locally (password manager). Do not commit it to Git.

---

## Link GitHub → PyPI (automatic publish)

PyPI does **not** have a “connect repository” button. You link them with **GitHub Actions**:

### A. Add token to GitHub (one time)

1. Open your repo: https://github.com/nkscoder/django-tickets  
2. **Settings** → **Secrets and variables** → **Actions**  
3. **New repository secret**  
   - Name: `PYPI_API_TOKEN`  
   - Value: your PyPI token (`pypi-...` from [manage account/token](https://pypi.org/manage/account/token/))  
4. Save  

### B. Push the workflow (included in this repo)

File: `.github/workflows/publish-pypi.yml`

```bash
git add .github/workflows/publish-pypi.yml pyproject.toml
git commit -m "Add GitHub Actions PyPI publish workflow"
git push origin main
```

### C. First upload OR publish via release

**Option 1 — Manual first upload** (so PyPI shows the project once):

```bash
python -m build
twine upload dist/*
```

**Option 2 — Publish from GitHub** (after secret is set):

1. On GitHub: **Releases** → **Create a new release**  
2. Tag: `v1.0.0` (must match `version` in `pyproject.toml`)  
3. Title: `v1.0.0` → **Publish release**  
4. **Actions** tab → workflow **Publish to PyPI** should run green  
5. Check https://pypi.org/project/django-tickets/

**Option 3 — Run workflow manually**

**Actions** → **Publish to PyPI** → **Run workflow** (uses `main` branch)

### Do NOT re-run release v1.0.0

Tag `v1.0.0` still has PyPI name `django-tickets` (already taken on PyPI).  
Always publish **v1.0.1** or newer from `main` (`nkscoder-django-tickets`).

### Project URLs on PyPI

After upload, PyPI reads links from `pyproject.toml`:

- Homepage → GitHub repo  
- Repository → GitHub repo  

No extra linking step on pypi.org.

---

## 3. Install build tools

```bash
cd /path/to/django-tickets
pip install --upgrade build twine
```

---

## 4. Build the package

```bash
python -m build
```

This creates:

- `dist/django_tickets-1.0.0.tar.gz` (source)
- `dist/django_tickets-1.0.0-py3-none-any.whl` (wheel)

Test the wheel locally (optional):

```bash
pip install dist/django_tickets-1.0.0-py3-none-any.whl
python -c "import tickets; print(tickets.__version__)"
```

---

## 5. Upload to PyPI

**TestPyPI first (recommended):**

```bash
python -m twine upload --repository testpypi dist/*

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ django-tickets
```

**Production PyPI:**

```bash
python -m twine upload dist/*
```

When prompted:

- **Username:** `__token__`
- **Password:** your API token (`pypi-AgEIc...`)

Or use environment variable (no prompt):

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR_TOKEN_HERE
python -m twine upload dist/*
```

---

## 6. Configure `~/.pypirc` (optional)

```ini
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE

[testpypi]
username = __token__
password = pypi-YOUR_TESTPYPI_TOKEN_HERE
```

Then:

```bash
twine upload dist/*
```

---

## 7. Install in a Django project

After publish:

```bash
pip install django-tickets
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "tickets.apps.TicketsConfig",
]
```

See [README.md](README.md) for full setup.

---

## 8. Release a new version

1. Bump version in `pyproject.toml` and `tickets/__init__.py` (root `__init__.py`)
2. Update `CHANGELOG.md` (optional)
3. Rebuild and upload:

```bash
rm -rf dist/ build/ *.egg-info
python -m build
twine upload dist/*
```

4. Tag in Git:

```bash
git tag v1.0.1
git push origin v1.0.1
```

---

## Notes

- Project name on PyPI: `django-tickets` (hyphen)
- Import / Django app name: `tickets` (underscore in Python imports)
- First upload: name `django-tickets` must be available on PyPI
