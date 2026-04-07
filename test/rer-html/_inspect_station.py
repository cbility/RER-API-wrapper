from selectolax.parser import HTMLParser

with open('test/rer-html/station.html', encoding='utf-8') as f:
    html = f.read()

tree = HTMLParser(html)

# H1 spans
h1 = tree.css_first('h1')
print('=== H1 spans ===')
for span in h1.css('span'):
    print(f'  span class={span.attrs.get("class","")} text={repr(span.text(strip=True))}')
print('  h1 full text:', repr(h1.text(strip=True)))

# Map h3 headings to their following DL keys
print()
print('=== h3 -> DL keys ===')
for h3 in tree.css('h3'):
    label = h3.text(strip=True)
    sib = h3.next
    while sib and sib.tag not in ('dl', 'table', 'h2', 'h3'):
        sib = sib.next
    if sib and sib.tag == 'dl':
        keys = [dt.text(strip=True) for dt in sib.css('dt')]
        print(f'  [{label}] -> {keys}')
    else:
        tag = sib.tag if sib else 'none'
        print(f'  [{label}] -> (no dl, next={tag})')

# All tables (full)
print()
print('=== TABLES ===')
for i, tbl in enumerate(tree.css('table')):
    print(f'--- TABLE {i} ---')
    for row in tbl.css('tr'):
        cells = row.css('th,td')
        print(' | '.join(c.text(strip=True) for c in cells))
