"""Check that edit form fields are prefilled in the HTML for given technician IDs."""
import re
from app import app

TEST_IDS = [2, 6]
FIELDS = ['name', 'email', 'specialization', 'certification_level', 'experience_years', 'hourly_rate', 'zone', 'max_weekly_hours', 'active', 'on_call']

app.config['TESTING'] = True
client = app.test_client()

for tid in TEST_IDS:
    print(f"\n--- Technician {tid} ---")
    res = client.get(f'/technicians/{tid}/edit')
    html = res.data.decode('utf-8')
    if res.status_code != 200:
        print('GET returned', res.status_code)
        continue

    for f in FIELDS:
        # look for form fields rendered either as WTForms inputs or plain inputs/selects
        # pattern: name="<f>" [^>]*value="..."
        m = re.search(r'name="%s"[^>]*value="([^"]*)"' % re.escape(f), html)
        if m:
            print(f"{f}: value='{m.group(1)}' (input value)")
            continue
        # check select options selected
        m2 = re.search(r'<select[^>]*name="%s"[\s\S]*?<option[^>]*selected[^>]*>([^<]+)</option>' % re.escape(f), html)
        if m2:
            print(f"{f}: select selected='{m2.group(1).strip()}'")
            continue
        # check checkbox/radio checked
        m3 = re.search(r'name="%s"[^>]*checked' % re.escape(f), html)
        if m3:
            print(f"{f}: checked=True")
            continue
        # not found
        print(f"{f}: NOT FOUND or no value in HTML")

print('\nCheck complete.')
