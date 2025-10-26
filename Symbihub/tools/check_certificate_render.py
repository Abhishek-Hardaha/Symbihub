import sys
sys.path.insert(0, r'a:\Symbihub')
from app import app

with app.test_request_context('/'):
    for name in ('certificate.html', 'Certificate.html'):
        try:
            t = app.jinja_env.get_template(name)
            print('FOUND', name)
            print(t.render(name='Test User', event_title='Demo Event', date='2025-10-26')[:400])
            break
        except Exception as e:
            print('ERR', name, type(e).__name__, str(e))
