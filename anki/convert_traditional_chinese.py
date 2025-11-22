# Fills a "Traditional" field for all cards in a deck from a "Simplified" field.
# I would recommend installing OpenCC with a proper system package manager as it is quite picky.

import requests
from opencc import OpenCC

cc = OpenCC('s2t')

# Get all notes in a deck
deck_name = "Personal"
query = f'deck:"{deck_name}"'
anki_addr = "http://127.0.0.1:8765"

notes = requests.post(anki_addr, json={
    "action": "findNotes",
    "version": 6,
    "params": {"query": query}
    }).json()['result']

# CBS tracking state across time so just stop the script when it runs out of cards
# (this is relevant for when you have your own deck and keep adding cards to it)
notes.reverse()

for note_id in notes:
    note_info = requests.post(anki_addr, json={
        "action": "notesInfo",
        "version": 6,
        "params": {"notes": [note_id]}
        }).json()['result'][0]

    simplified = note_info['fields']['Simplified']['value']
    traditional = cc.convert(simplified)
    if simplified == traditional or note_info['fields']['Traditional']['value']:
        continue
    print(f"found: {simplified}, conv: {traditional}")

    requests.post(anki_addr, json={
        "action": "updateNoteFields",
        "version": 6,
        "params": {
            "note": {
                "id": note_id,
                "fields": {"Traditional": traditional}
                }
            }
        })

print("✅ All cards updated with Traditional Chinese.")

