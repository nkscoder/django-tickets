# django-tickets

**Author:** [Nitesh Kumar Singh (nkscoder)](https://nkscoder.in)

Generic, open-source Django ticket system by **Nitesh Kumar Singh (nkscoder)** — for **any Django project**.  
Self-contained plugin — uses Django’s user model and standard permissions only.

| | |
|---|---|
| **Author / Maintainer** | [Nitesh Kumar Singh (nkscoder)](https://nkscoder.in) |
| **Site** | [nkscoder.in](https://nkscoder.in) |
| **Package (PyPI)** | `nkscoder-django-tickets` |
| **Django app** | `tickets` |
| **Version** | 1.0.2 |
| **License** | MIT |

---

## Features

- Create, assign, reassign, and close tickets
- Per-user questions & answers (draft / final submit)
- Status history and in-app notifications
- Soft delete (superuser)
- REST API: user search + ticket create
- Optional sign-off ranks (`Signater`)
- Configurable via `TICKETS_*` settings

---

## Requirements

| Package | Version |
|---------|---------|
| Python | 3.10+ |
| Django | 4.2+ |
| djangorestframework | 3.14+ |

---

## Project layout

Copy or clone this folder into your Django project:

```
your-django-project/
├── manage.py
├── your_project/
│   ├── settings.py
│   └── urls.py
└── tickets/                    ← this app
    ├── apps.py
    ├── conf.py
    ├── models.py
    ├── urls.py
    ├── views/
    ├── templates/tickets/
    ├── migrations/             ← run makemigrations (new installs)
    ├── migrations_legacy/      ← archived DB history only — not for fresh installs
    ├── legacy_archive/         ← old host-specific code (not loaded)
    └── README.md
```

---

## Publish to PyPI

To upload this package to [PyPI](https://pypi.org/) (account: [pypi.org/manage/account](https://pypi.org/manage/account/)):

1. Create an API token at [pypi.org/manage/account/token](https://pypi.org/manage/account/token/)
2. Build and upload — full steps in **[PUBLISHING.md](PUBLISHING.md)**

```bash
pip install build twine
python -m build
twine upload dist/*
# Username: __token__
# Password: <your-pypi-api-token>
```

---

## Setup in your Django project

### Step 1 — Add the app

**Option A — Copy the folder**

```bash
cp -r /path/to/tickets /path/to/your-django-project/tickets
```

**Option B — Install from PyPI** (after publish)

```bash
pip install nkscoder-django-tickets
```

**Option C — Install from source** (development)

```bash
git clone https://github.com/nkscoder/django-tickets.git
cd django-tickets
pip install -e .
```

Then use app label `tickets` the same way as below.

---

### Step 2 — Install dependencies

```bash
pip install "Django>=4.2" "djangorestframework>=3.14"
```

---

### Step 3 — Update `settings.py`

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "tickets.apps.TicketsConfig",   # add this
]

# Required: template variable for {% extends TICKETS_BASE_TEMPLATE %}
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "tickets.context_processors.tickets_settings",  # add this
            ],
        },
    },
]

# Auth (use your existing user model)
# AUTH_USER_MODEL = "accounts.User"   # if you use a custom user

# --- Tickets configuration (all optional) ---

# Base layout for ticket pages (use your site template or built-in)
TICKETS_BASE_TEMPLATE = "tickets/base.html"
# TICKETS_BASE_TEMPLATE = "your_project/base.html"

TICKETS_LOGIN_URL = "login"                    # URL name for @login_required
TICKETS_DB_ALIAS = "default"                   # database alias
TICKETS_CREATE_PERMISSION = "tickets.add_ticket"
TICKETS_ENABLE_SIGNATERS = True
TICKETS_ENABLE_ACTIVITY_DASHBOARD = False      # needs optional `activity` app
TICKETS_USER_SEARCH_FIELDS = ["first_name", "last_name", "email", "username"]
TICKETS_LINK_TYPES = [
    ("generic", "Generic"),
    ("external", "External record"),
]

# Media for file uploads (reports, attachments)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# REST framework (minimal)
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
```

---

### Step 4 — Update root `urls.py`

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),  # login/logout
    path("tickets/", include("tickets.urls", namespace="tickets")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

Ensure you have a **login URL** named `login` (or change `TICKETS_LOGIN_URL`).

Example minimal login in `urls.py`:

```python
from django.contrib.auth import views as auth_views

urlpatterns += [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
```

---

### Step 5 — Database migrations

**New project (empty database):**

```bash
cd your-django-project
python manage.py makemigrations tickets
python manage.py migrate
```

**Existing database** (already has ticket tables from an older custom build):

- Keep using `migrations_legacy/` only if that matches how the DB was created.
- Do **not** run a new `0001_initial` on that database without a migration plan.
- See `migrations_legacy/README.md`.

---

### Step 6 — Create permissions & superuser

```bash
python manage.py createsuperuser
```

Django creates default permissions for the `tickets` app. Grant **Can add ticket** to users who should create tickets:

- Admin → Users → Permissions → `tickets | ticket | Can add ticket`  
  **or** use a group with `tickets.add_ticket`.

---

### Step 7 — Static files (optional but recommended)

Ticket UI uses Bootstrap and icons under `static/` in your project. Either:

1. Use the built-in `tickets/base.html` (includes vendor paths), and collect static:

```bash
python manage.py collectstatic
```

2. Or set `TICKETS_BASE_TEMPLATE` to your own `base.html` that already loads Bootstrap.

Expected static paths (if using bundled layout):

```
static/vendor/bootstrap/
static/vendor/fontawesome/
static/ticket/css/
```

---

### Step 8 — Run the server

```bash
python manage.py runserver
```

Open:

| Page | URL |
|------|-----|
| Ticket list | http://127.0.0.1:8000/tickets/ |
| Create ticket | http://127.0.0.1:8000/tickets/create_ticket/ |
| Dashboard | http://127.0.0.1:8000/tickets/dashboard/ |
| Notifications | http://127.0.0.1:8000/tickets/notifications/ |
| Admin | http://127.0.0.1:8000/admin/ |

---

### Step 9 — Seed questions (optional)

In Django admin (`/admin/`) add:

1. **Categories** (e.g. `General`, `Technical`)
2. **Questions** linked to categories (status = active)

Assignees receive answer slots for selected question IDs when a ticket is created.

---

### Step 10 — Run tests

```bash
python manage.py test tickets.tests.test_notifications
```

---

## Settings reference

| Setting | Default | Description |
|---------|---------|-------------|
| `TICKETS_BASE_TEMPLATE` | `tickets/base.html` | Parent template for all ticket pages |
| `TICKETS_LOGIN_URL` | `login` | URL name for login redirect |
| `TICKETS_DB_ALIAS` | `default` | Database to use |
| `TICKETS_CREATE_PERMISSION` | `tickets.add_ticket` | Permission to create tickets |
| `TICKETS_ENABLE_SIGNATERS` | `True` | Sign-off ranks on submit form |
| `TICKETS_ENABLE_ACTIVITY_DASHBOARD` | `False` | Integrate with `activity` app if installed |
| `TICKETS_USER_SEARCH_FIELDS` | `first_name`, `last_name`, `email`, `username` | User API search columns |
| `TICKETS_LINK_TYPES` | generic, external | Choices on create form |

---

## Main URL routes

| Name | Path |
|------|------|
| `tickets:ticket_list` | `/tickets/` |
| `tickets:create_ticket` | `/tickets/create_ticket/` |
| `tickets:store_ticket` | `/tickets/create_ticket/store-create/` (POST) |
| `tickets:ticket_detail` | `/tickets/ticket_detail/<id>/` |
| `tickets:reassign_ticket` | `/tickets/reassign_ticket/<id>/` (POST JSON) |
| `tickets:ticket_notifications` | `/tickets/notifications/` |
| `tickets:user-list-search` | `/tickets/api/users/` |
| `tickets:api-ticket-create` | `/tickets/api/tickets/` |

---

## REST API examples

**Search users** (authenticated):

```http
GET /tickets/api/users/?search=john
Authorization: Session or Token
```

**Create ticket** (authenticated):

```http
POST /tickets/api/tickets/
Content-Type: application/json

{
  "title": "Support request",
  "description": "Details here",
  "link_type": "generic",
  "assignee_ids": [2, 3],
  "question_ids": [1, 2]
}
```

---

## Integrate with your site template

To use your project’s header/footer instead of `tickets/base.html`:

```python
# settings.py
TICKETS_BASE_TEMPLATE = "base.html"
```

Your `base.html` must define a `{% block content %}{% endblock %}` block (same as standard Django layouts).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `TemplateDoesNotExist` for `TICKETS_BASE_TEMPLATE` | Add context processor `tickets.context_processors.tickets_settings` |
| `No module named 'tickets'` | Ensure `tickets/` is on `PYTHONPATH` / inside project root |
| Permission denied creating ticket | Grant `tickets.add_ticket` or login as superuser |
| Redirect loop on login | Set `LOGIN_URL` / `TICKETS_LOGIN_URL` to a valid route name |
| `relation "tickets_ticket" does not exist` | Run `makemigrations` + `migrate` |
| Need custom domain features | Build a separate extension app on top of this core; see `legacy_archive/` for reference only |

---

## Archived code

Host-specific integrations (not used by this package) are stored under `legacy_archive/` for private migration reference only. They are **not** imported by URLs or `INSTALLED_APPS`.

- `legacy_archive/` — archived views and models (optional reference)
- `migrations_legacy/` — old migrations for existing databases only

---

## About the author

**Nitesh Kumar Singh (nkscoder)** maintains this package at **[nkscoder.in](https://nkscoder.in)** as a reusable Django plugin for ticket workflows (assignments, Q&A, notifications, and status tracking).

For support, custom extensions (e.g. domain-specific modules), or integration help, visit [https://nkscoder.in](https://nkscoder.in).

---

## License

Copyright © 2026 [Nitesh Kumar Singh (nkscoder)](https://nkscoder.in).

Released under the [MIT License](LICENSE). You may use, copy, modify, and distribute this software with attribution to Nitesh Kumar Singh (nkscoder).
