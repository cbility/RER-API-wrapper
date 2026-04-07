from selectolax.parser import HTMLParser

for fname in ['certificates_rego_breakdown', 'certificates_roc_breakdown', 'certificates_rego_history', 'certificates_roc_history']:
    with open(f'test/rer-html/{fname}.html', encoding='utf-8') as f:
        html = f.read()
    tree = HTMLParser(html)
    table = tree.css_first('table')
    print(f'=== {fname} ===')
    if table:
        headers = [th.text(strip=True) for th in table.css('th')]
        print('Headers:', headers)
        for row in table.css('tr')[1:3]:
            cells = row.css('td')
            row_data = []
            for td in cells:
                link = td.css_first('a')
                href = link.attrs.get('href', '') if link else None
                row_data.append({'text': td.text(strip=True)[:40], 'href': href})
            print('  Row:', row_data)
    print()
