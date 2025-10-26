import sys
sys.path.insert(0, r'a:\Symbihub')
from app import app

with app.test_client() as c:
    r = c.get('/admin')
    print('ADMIN GET', r.status_code)
    text = r.get_data(as_text=True)
    print('LENGTH:', len(text))
    print(text[:800])

    # Also try certificate preview rendering using template route if any registration id exists
    # We'll just try to render certificate template via jinja env to avoid DB dependence
    try:
        tpl = app.jinja_env.get_template('certificate.html')
        preview = tpl.render(name='Smoke Tester', event_title='Smoke Event', date='2025-10-26')
        print('\nCERTIFICATE RENDER OK, length:', len(preview))
    except Exception as e:
        print('\nCERTIFICATE RENDER ERROR', type(e).__name__, e)
