"""Full-page screenshots of every Vue route, per role. Needs the dev server on http://localhost:5173.
Run from repo root:  backend/.venv/Scripts/python frontend/scripts/screenshots.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = 'http://localhost:5173'
OUT = Path(__file__).resolve().parents[2] / 'ML' / 'screenshots' / 'frontend'
OUT.mkdir(parents=True, exist_ok=True)

# (role, path, file name) in the order a user would walk through the app
PAGES = [
    (None, '/', 'welcome'), (None, '/login', 'login'), (None, '/register', 'register'),
    ('student', '/student/dashboard', 'student_dashboard'), ('student', '/student/discover', 'student_discover_mentors'),
    ('student', '/student/requests', 'student_my_requests'), ('student', '/student/workspace', 'student_workspace'),
    ('mentor', '/mentor/dashboard', 'mentor_dashboard'), ('mentor', '/mentor/workspace', 'mentor_workspace'),
    ('mentor', '/mentor/profile', 'mentor_profile_setup'),
    ('admin', '/admin/insights', 'admin_insights'), ('admin', '/admin/verify', 'admin_verify_mentors'),
    ('admin', '/admin/flags', 'admin_flags'), ('admin', '/admin/audit', 'admin_audit_log'),
]

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.goto(BASE)
    page.wait_for_load_state('networkidle')
    for i, (role, path, name) in enumerate(PAGES, 1):
        # Switch role in the app's own Pinia store, then navigate inside the SPA so the state is kept
        page.evaluate("""([role, path]) => {
            const app = document.querySelector('#app').__vue_app__;
            const g = app.config.globalProperties;
            if (role) g.$pinia._s.get('auth').switchRole(role);
            return g.$router.push(path);
        }""", [role, path])
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / f'{i:02d}_{name}.png'), full_page=True)
        print('saved', name)

    # ---- Live mode: real JWT login against Django (needs the backend on :8000 and the demo accounts)
    creds_file = Path(__file__).resolve().parents[2] / 'backend' / 'demo_credentials.local.json'
    if creds_file.exists():
        import json
        creds = json.loads(creds_file.read_text())
        live = OUT.parent / 'frontend_live'
        live.mkdir(exist_ok=True)
        page.set_default_timeout(180000)

        def sign_in(email):
            page.evaluate("localStorage.clear()")
            page.goto(BASE + '/login')
            page.fill('input[type=email]', email)
            page.fill('input[type=password]', creds['password'])
            page.click('button[type=submit]')
            page.wait_for_url('**/dashboard*' if 'iic' not in email else '**/admin/insights', timeout=60000)

        def snap(name, full=True):
            page.wait_for_timeout(600)
            page.screenshot(path=str(live / f'{name}.png'), full_page=full)
            print('saved live', name)

        sign_in(creds['iic'])
        page.wait_for_selector('text=Mentorships that may be going quiet')
        snap('01_admin_live_insights')
        page.click('a[href="/admin/matching"]')
        page.wait_for_selector('text=Open requests')
        page.locator('button:has-text("#")').first.click()
        page.wait_for_selector('text=Suggested priority')
        page.wait_for_selector('text=hybrid_v1', timeout=120000)
        snap('02_admin_ai_matching')
        page.click('text=Ask Sangam')
        page.fill('input[placeholder^="Ask about"]', 'How do I log a meeting?')
        page.click('form button:has-text("Send")')
        page.wait_for_selector('text=Sources:', timeout=60000)
        page.fill('input[placeholder^="Ask about"]', 'Please approve my mentoring request')
        page.click('form button:has-text("Send")')
        page.wait_for_selector('text=I cannot approve', timeout=60000)
        snap('03_ask_sangam_chat', full=False)

        sign_in(creds['mentor'])
        page.click('a[href="/mentor/workspace"]')
        page.wait_for_selector('text=AI session summary')
        page.wait_for_timeout(1000)
        notes = json.loads((creds_file.parent / 'fixtures/synthetic/session_notes.json').read_text(encoding='utf8'))[2]['notes']
        page.fill('textarea[placeholder^="e.g."]', notes)
        page.click('button:has-text("Generate draft")')
        page.wait_for_selector('text=prompt summary_v1', timeout=120000)
        snap('04_mentor_ai_summary')
    browser.close()
