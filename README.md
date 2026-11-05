# ASSAS — Automated Student Subject Allocation System

ASSAS assigns subjects to students automatically each semester for the Faculty of Information Technology at City University Malaysia. A rule engine checks prerequisites, credit caps, repeat subjects, probation limits, timetable clashes and class capacity. Anything it can't resolve on its own is flagged as an exception for an administrator to review. Students can see their subjects, progress and timetable, and submit add/drop requests.

The interface follows the look of the CityU student portal: a crimson top bar, a folder-style sidebar and red and navy table headers.

## Features

**Administrators**
- **Dashboard:** student, subject and pending-item counts, plus faculty and programme management.
- **Assign Subjects:** runs the rule engine for every eligible student, or one faculty or programme. The semester defaults to the current intake, and its length (19 or 12 weeks) and subject limit come from the semester code.
- **Exceptions:** review flagged subjects. Approve or reject them, pick a clash-free replacement, or undo a decision.
- **Add/Drop Requests:** approve, reject, edit or undo student requests.
- **Records:** students (with photos), subjects and prerequisites, master timetables and time slots, and venues with seat capacity.

**Students**
- **My Subjects:** current and previous semesters, credits used against their cap, and repeat subjects.
- **Academic Progress:** credits earned and subjects completed towards the programme.
- **Add/Drop Request:** a numbered rules panel built from the student's own record (credit cap, credits used, subject limit, pending requests) above the request form.
- **Class Schedule:** a weekly grid of the student's own classes, plus the programme's master timetables. These open on today's day.
- **My Profile:** a read-only view of the student's record.

**Built-in automation**
- **Live pending counts.** Sidebar badges refresh every 45 seconds, when you return to the tab, and immediately after any decision.
- **Context-aware shortcut.** The teal block in the top bar offers the most likely next step: "Review N pending", "Run Assignment" or "New Add/Drop".
- **Re-runs only top up.** Running assignment again for a semester counts subjects a student already has towards their limits. It only adds what's still missing, and never more than the cap.
- **Tidy feedback.** Toasts that dismiss themselves and in-app confirm dialogs replace the browser's alert and confirm popups.

## Tech stack

| Part | Technology |
|---|---|
| Backend | Python, Django 6, Django REST Framework, SQLite |
| Frontend | React 19, React Router 7, Vite 8 |
| Tests | Django `TestCase` (backend), Vitest + Testing Library (frontend) |

## Project structure

```
ASSAS/
├── backend/
│   ├── assas_backend/        # Django settings and root URLs
│   ├── core/
│   │   ├── models.py         # Students, subjects, enrolments, exceptions, timetables...
│   │   ├── rule_engine.py    # Subject assignment rules
│   │   ├── views.py          # REST API
│   │   ├── urls.py           # API routes (mounted at /api/)
│   │   ├── auth_backend.py   # Student ID + IC/Passport login
│   │   ├── tests.py
│   │   └── management/commands/seed_data.py
│   └── requirements.txt
├── frontend/
│   ├── public/               # Logo, crest, campus background
│   └── src/
│       ├── components/       # Layout (top bar, sidebar), route guards
│       ├── context/          # Auth, toasts and confirm dialogs
│       ├── pages/            # Home, Login, admin/*, student/*
│       ├── utils/            # API client, semester helpers
│       └── index.css         # Styles for the whole app
├── Media/                    # Source images
└── ASSAS_*.png / .svg / .mmd # ERD and activity diagrams
```

## Getting started

You'll need **Python 3.12+** and **Node.js 20.19+ or 22.12+**.

### 1. Backend (Django API on port 8000)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # first admin: asks for a Student ID (e.g. ADMIN001), full name and password
python manage.py runserver 8000
```

### 2. Frontend (Vite dev server on port 3000)

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The frontend calls the API at `http://localhost:8000/api`, as set in `frontend/src/utils/api.js`. The backend accepts requests from ports 3000 and 5173 on `localhost` and `127.0.0.1`.

### Signing in

Users sign in with their **Student ID** and, in the second field, their **IC/Passport number**, which is stored hashed as the password.

- **Administrator:** the Student ID and password you gave `createsuperuser`. Type the password into the IC/Passport field.
- **Students:** an administrator creates students under **Records → Students**. Each one signs in with their Student ID and IC/Passport number. If an administrator changes a student's IC/Passport number, that student's password is reset to the new number.

Faculties, programmes, subjects, venues and timetables are all set up from the admin screens. Assignment needs at least one timetable with time slots for the semester.

## Running tests

```bash
# Backend
cd backend && source venv/bin/activate
python manage.py test core

# Frontend
cd frontend
npm test            # single run
npm run lint        # oxlint
```

## How subject assignment works

When an administrator runs **Assign Subjects** for a semester code such as `202609`:

1. **Check the semester.** The code must be valid, and that semester must already have started. Every programme involved must have time slots registered for it.
2. **Gather candidates.** For each active or probation student, the candidates are subjects from their current curriculum semester that have a time slot. Failed subjects due for a repeat come first.
3. **Apply the rules in order:**
   1. Already passed: skip the subject.
   2. Prerequisites: flag it if one hasn't been passed.
   3. Credit limit: flag it if adding it would go over the student's cap.
   4. Repeat subjects: these were already put first, and are recorded as repeats.
   5. Probation: a probation student's cap is the lower probation cap.
   6. Timetable clashes: when two subjects clash, the one with more credit hours is kept.
   7. Class capacity: flag the subject if its venue is full.
4. **Try a replacement.** A subject that loses a clash or is full is swapped automatically for a clash-free one, as long as the replacement has no prerequisite links, isn't a semester 7–9 subject, and still fits within the student's limits.
5. **Flag the rest.** Everything left is recorded as a pending exception for review.

Each semester's subject limit depends on its intake: January and May are 19-week semesters with 5–7 subjects, and September is a 12-week semester with 3 subjects. Subjects a student already holds for the semester count towards both the credit cap and the subject limit, so running assignment again only fills the gaps.

## Notes

- **`seed_data` is out of date.** The `python manage.py seed_data` command fails on the current database schema: it still sets the old `Subject.programme` and `year` fields that later migrations removed. Don't use it until it's updated.
- **Development settings only.** `backend/assas_backend/settings.py` has `DEBUG = True`, a hard-coded `SECRET_KEY` and `ALLOWED_HOSTS = ['*']`. Change all three before deploying anywhere public.
- **Local data stays out of Git.** `db.sqlite3` and uploaded files in `backend/media/` are excluded by `.gitignore`. The committed `db.sqlite3.bak-*` files are database snapshots: they contain student IC/Passport numbers in plain text, so keep this repository private.
- **Icon font.** Material Symbols is loaded with only the weights the app uses. If you add an icon with a different weight or fill, widen the font range in `frontend/index.html`.
