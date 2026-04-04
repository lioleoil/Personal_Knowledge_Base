import json, glob, csv, math, os

files = sorted(glob.glob('d:/DQA/SH/logs_split/*.json'))

events = []
changes = []
undo_links = []

for f in files:
    with open(f) as fp:
        d = json.load(fp)
    r = d['_raw']
    t = r.get('type', '')
    data = r.get('data', {})

    if t == 'annotation.object.select':      cat = 'select'
    elif t == 'annotation.bbox3d.transform': cat = 'transform'
    elif t == 'history.undo':                cat = 'undo'
    elif t == 'history.redo':                cat = 'redo'
    else:                                    cat = 'other'

    events.append({
        'event_id':       d['_id'],
        'event_type':     t,
        'event_time':     r.get('time','').replace('T',' ').replace('Z',''),
        'session_id':     r.get('sessionid',''),
        'user_id':        data.get('user',{}).get('id',''),
        'task_id':        data.get('project',{}).get('task_id',''),
        'event_category': cat
    })

    for i, ch in enumerate(data.get('changes', [])):
        old = ch.get('old', {})
        new = ch.get('new', {})
        old_pos = old.get('position')
        new_pos = new.get('position')
        dist = ''
        if old_pos and new_pos:
            dist = round(math.sqrt(
                (new_pos['x']-old_pos['x'])**2 +
                (new_pos['y']-old_pos['y'])**2 +
                (new_pos['z']-old_pos['z'])**2
            ), 4)
        changes.append({
            'event_id':      d['_id'],
            'event_time':    r.get('time','').replace('T',' ').replace('Z',''),
            'session_id':    r.get('sessionid',''),
            'event_type':    t,
            'change_idx':    i,
            'object_id':     ch.get('object_id',''),
            'object_type':   ch.get('object_type',''),
            'change_action': ch.get('action',''),
            'old_val':       json.dumps(old, ensure_ascii=False),
            'new_val':       json.dumps(new, ensure_ascii=False),
            'move_distance': dist
        })

    if t in ('history.undo', 'history.redo'):
        undo_links.append({
            'undo_event_id':         d['_id'],
            'undo_type':             t,
            'undo_time':             r.get('time','').replace('T',' ').replace('Z',''),
            'session_id':            r.get('sessionid',''),
            'reverted_event_id':     data.get('reverted_command_id',''),
            'reverted_command_type': data.get('reverted_command_type',''),
            'reverted_count':        data.get('count','')
        })


def print_table(title, rows, cols):
    widths = {c: len(c) for c in cols}
    for r in rows:
        for c in cols:
            widths[c] = max(widths[c], len(str(r.get(c,''))))
    sep = '+' + '+'.join('-'*(widths[c]+2) for c in cols) + '+'
    hdr = '|' + '|'.join((' '+c+' ').ljust(widths[c]+2) for c in cols) + '|'
    print()
    print(title)
    print(sep); print(hdr); print(sep)
    for r in rows:
        print('|' + '|'.join((' '+str(r.get(c,''))+' ').ljust(widths[c]+2) for c in cols) + '|')
    print(sep)
    print('  %d rows' % len(rows))


# ── int_labelit__undo_links ───────────────────────────────────
event_map = {e['event_id']: e for e in events}
undo_link_rows = []

for u in undo_links:
    rev = event_map.get(u['reverted_event_id'], {})
    undo_link_rows.append({
        'undo_event_id':         u['undo_event_id'][:8],
        'undo_type':             u['undo_type'],
        'undo_time':             u['undo_time'][11:23],
        'session_id':            u['session_id'][:8],
        'reverted_event_id':     u['reverted_event_id'][:8],
        'reverted_command_type': u['reverted_command_type'],
        'reverted_count':        u['reverted_count'],
        'rev_event_type':        rev.get('event_type','NOT FOUND').replace('annotation.',''),
        'rev_event_time':        rev.get('event_time','')[11:23],
        'rev_event_category':    rev.get('event_category','NOT FOUND')
    })

print_table(
    '[1] int_labelit__undo_links\n'
    '    stg_labelit__undo_history JOIN stg_labelit__events\n'
    '    ON reverted_event_id = event_id',
    undo_link_rows,
    ['undo_event_id','undo_type','undo_time','session_id',
     'reverted_event_id','reverted_command_type','reverted_count',
     'rev_event_type','rev_event_time','rev_event_category']
)


# ── int_labelit__effective_changes ───────────────────────────
reverted_ids = set()
restored_ids = set()
for u in undo_links:
    if u['undo_type'] == 'history.undo':
        reverted_ids.add(u['reverted_event_id'])
    elif u['undo_type'] == 'history.redo':
        restored_ids.add(u['reverted_event_id'])
final_reverted = reverted_ids - restored_ids

eff_display = []
eff_full = []

for ch in sorted(changes, key=lambda x: x['event_time']):
    is_rev = ch['event_id'] in final_reverted

    eff_display.append({
        'event_id':      ch['event_id'][:8],
        'event_time':    ch['event_time'][11:23],
        'session_id':    ch['session_id'][:8],
        'event_type':    ch['event_type'].replace('annotation.',''),
        'object_id':     ch['object_id'],
        'object_type':   ch['object_type'],
        'move_distance': ch['move_distance'],
        'is_reverted':   'TRUE' if is_rev else 'FALSE',
        'effective':     'N (취소됨)' if is_rev else 'Y (유효)'
    })

    row = dict(ch)
    row['is_reverted'] = 'TRUE' if is_rev else 'FALSE'
    eff_full.append(row)

print_table(
    '[2] int_labelit__effective_changes\n'
    '    stg_labelit__event_changes LEFT JOIN stg_labelit__undo_history\n'
    '    ON event_id = reverted_event_id  →  is_reverted 플래그 추가',
    eff_display,
    ['event_id','event_time','session_id','event_type',
     'object_id','object_type','move_distance','is_reverted','effective']
)


# ── CSV 저장 ──────────────────────────────────────────────────
out_dir = 'd:/DQA/SH/logs_split'

p1 = os.path.join(out_dir, 'int_labelit__undo_links.csv')
with open(p1, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=undo_link_rows[0].keys())
    w.writeheader()
    w.writerows(undo_link_rows)

p2 = os.path.join(out_dir, 'int_labelit__effective_changes.csv')
with open(p2, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=eff_full[0].keys())
    w.writeheader()
    w.writerows(eff_full)

print()
print('saved:', p1)
print('saved:', p2)
