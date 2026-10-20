#!/usr/bin/env python3
"""Convert the two existing menu macros into direct, app-scoped broadcasts."""
import json
from pathlib import Path
import uuid
import zipfile

root = Path(__file__).resolve().parent
source = json.loads((root / 'keymaps-original.json').read_text())
package = 'io.github.mzbali.tizentube'
for mapping, action in zip(source['keymap_list'], ['SLOWER', 'FASTER']):
    for constraint in mapping['constraintList']:
        for extra in constraint['extras']:
            if extra['id'] == 'extra_package_name':
                extra['data'] = package
    mapping['actionList'] = [{
        'type': 'INTENT', 'flags': 0, 'uid': str(uuid.uuid4()),
        'data': f'intent:#Intent;action={package}.{action};component={package}/.SpeedReceiver;end',
        'extras': [
            {'id': 'extra_intent_target', 'data': 'BROADCAST_RECEIVER'},
            {'id': 'extra_intent_description', 'data': f'YouTube speed: {action.lower()}'},
            {'id': 'extra_intent_extras', 'data': '[]'}
        ]
    }]
out = root / 'out'
out.mkdir(exist_ok=True)
with zipfile.ZipFile(out / 'speed-keymaps.zip', 'w') as archive:
    archive.writestr('data.json', json.dumps(source, indent=2))
