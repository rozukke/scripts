# Get example sentences for Anki cards from Tatoeba. The best dictionary I have doesn't have examples,
# and most of my sources aren't super valid for sentence mining, so we make do. This rewrites
# ALL sentences, so could be a decent refresh for a deck once in a while. Also includes the
# sentence in traditional Chinese.

import requests
import random
import sys
from opencc import OpenCC
from pypinyin import lazy_pinyin, Style

from tatoeba_ingest import query

cc = OpenCC('s2t')
cc_t2s = OpenCC('t2s')

ANKI_ADDR = "http://127.0.0.1:8765"
DECK_NAME = "Personal"

def get_example_sentence(word):
    results = query(word)
    if results:
        return results[0]
    else:
        print(f"Could not find example sentence for {word}")

def progress_bar(curr, total, end=""):
    progress = (curr + 1) / total
    bar = int(progress * 30)  # bar width = 30 chars
    print(f"\rProgress: [{'#' * bar}{'.' * (30 - bar)}] {progress*100:6.0f}%", end=end)
    sys.stdout.flush()

def to_pinyin(sentence):
    py = lazy_pinyin(sentence, style=Style.TONE, v_to_u=True)
    return " ".join(py)

# -----------------------
# 1. Get all notes
# -----------------------
print("Getting all notes for deck...\n")
anki_query = f'deck:"{DECK_NAME}"'
notes = requests.post(ANKI_ADDR, json={
    "action": "findNotes",
    "version": 6,
    "params": {"query": anki_query}
}).json()['result']

# -----------------------
# 2. Collect all Simplified words
# -----------------------
all_words = []
note_data = {}  # store details to avoid calling notesInfo twice


print(f"Getting all cards from deck {DECK_NAME}")
for i, nid in enumerate(notes):
    progress_bar(i, len(notes))
    info = requests.post(ANKI_ADDR, json={
        "action": "notesInfo",
        "version": 6,
        "params": {"notes": [nid]}
    }).json()['result'][0]


    note_data[nid] = info
    simp = info['fields']['Simplified']['value'].strip()
    if simp:
        all_words.append(simp)

print(f"\n\n📘 Found {len(all_words)} words.")


# -----------------------
# 3. Process each note: update Traditional + generate Example
# -----------------------
for i, note_id in enumerate(notes):
    info = note_data[note_id]

    simplified = info['fields']['Simplified']['value']

    # --- Generate example sentence ---
    print(f"→ Getting example sentence for: {simplified}")
    example_query = get_example_sentence(simplified)
    if not example_query:
        print("SENTENCE NOT FOUND")
        continue


    example = example_query["cmn"]
    example_trans = example_query["eng"]
    pinyin_str = to_pinyin(example)
    print(f"   Example: {example} / {pinyin_str} / {example_trans}")

    # Tatoeba examples can be traditional
    trad = cc.convert(example)
    if trad == example:
        example = cc_t2s.convert(example)

    requests.post(ANKI_ADDR, json={
        "action": "updateNoteFields",
        "version": 6,
        "params": {
            "note": {
                "id": note_id,
                "fields": {
                    "Sentence": example,
                    "Sentence Traditional": trad,
                    "Sentence Pinyin": pinyin_str,
                    "Sentence Translation": example_trans,
                }
            }
        }
    })
    print()
    progress_bar(i, len(notes), end="\n")

print("✅ All cards updated with Traditional + generated example sentences.")
