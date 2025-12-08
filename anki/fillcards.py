import ankiutils
import requests

# Get example sentences for Anki cards from Tatoeba. The best dictionary I have doesn't have examples,
# and most of my sources aren't super valid for sentence mining, so we make do. This rewrites
# ALL sentences, so could be a decent refresh for a deck once in a while. Also includes the
# sentence in traditional Chinese.

ANKI_ADDR = "http://127.0.0.1:8765"
DECK_NAME = "Personal"

# -----------------------
# 1. Get all notes
# -----------------------
print(f"Getting all cards from deck {DECK_NAME}")
anki_query = f'deck:"{DECK_NAME}"'
notes = requests.post(ANKI_ADDR, json={
    "action": "findNotes",
    "version": 6,
    "params": {"query": anki_query}
}).json()['result']

# -----------------------
# 2. Collect all Simplified words
# -----------------------
note_data = {}  # store details to avoid calling notesInfo twice
translated_sentences = {}

for i, nid in enumerate(notes):
    ankiutils.show_progress_bar(i, len(notes))

    info = requests.post(ANKI_ADDR, json={
        "action": "notesInfo",
        "version": 6,
        "params": {"notes": [nid]}
    }).json()['result'][0]
    note_data[nid] = info

print(f"\n\n📘 Found {len(note_data.keys())} words.")

# -----------------------
# 3. Process each note: update Traditional + generate Example
# -----------------------
for i, note_id in enumerate(notes):
    print()
    ankiutils.show_progress_bar(i, len(notes), end="\n")

    info = note_data[note_id]
    simplified_word = info['fields']['Simplified']['value']
    trad_word = ankiutils.convert_to_traditional(simplified_word)

    # Update Traditional Chinese word value
    if info['fields']['Traditional']['value'] == "" and trad_word != simplified_word:
        requests.post(ANKI_ADDR, json={
            "action": "updateNoteFields",
            "version": 6,
            "params": {
                "note": {
                    "id": note_id,
                    "fields": {
                        "Traditional": trad_word,
                    }
                }
            }
        })

    # Check if already processed
    if info['fields']['Sentence Translation']['value'] != "":
        continue

    if len(info['fields']['Sentence']['value']) > len(simplified_word):
        # Quality sentence exists, get translation and pinyin
        existing_example = info['fields']['Sentence']['value']
        print(f"→ Getting translation for: {existing_example}")

        # Check for existing translation or translate via LLM
        if existing_example in translated_sentences.keys():
            sentence_eng = translated_sentences[existing_example]
        else:
            example_query = None
            while not example_query:
                example_query = ankiutils.generate_example_trans(existing_example)
            sentence_eng = example_query["eng"]

        translated_sentences[existing_example] = sentence_eng
        sentence_pyn = ankiutils.get_word_aware_pinyin(existing_example)
        print(f"   Example: {existing_example} / {sentence_pyn} / {sentence_eng}")

        sentence_trad = ankiutils.convert_to_traditional(existing_example)

    else:
        # --- Get example sentence ---
        print(f"→ Getting example sentence for: {simplified_word}")
        example_query = None
        while True:
            last_query = example_query
            example_query = ankiutils.get_example_sentence_from_db(simplified_word)
            if not example_query:
                # Does not exist in db
                break
            elif last_query and last_query["cmn"] == example_query["cmn"]:
                # There's only one bad sentence that we got in last query
                example_query = None
                break
            elif not ankiutils.word_aware_in_sentence(simplified_word, example_query["cmn"]):
                # Word is not correctly used in sentence
                continue

            # Sentence OK
            break

        # AI generate if does not exist
        if not example_query:
            example_query = ankiutils.generate_example_sentence(simplified_word)

        sentence_cmn = example_query["cmn"]
        sentence_eng = example_query["eng"]
        sentence_pyn = ankiutils.get_word_aware_pinyin(sentence_cmn)
        print(f"   Example: {sentence_cmn} / {sentence_pyn} / {sentence_eng}")

        # Tatoeba examples can be traditional, check if this is the case
        sentence_try_simp = ankiutils.convert_to_simplified(sentence_cmn)
        if sentence_try_simp != sentence_cmn:
            # Switch sentences over
            sentence_trad = sentence_cmn
            sentence_cmn = sentence_try_simp
        else:
            sentence_trad = ankiutils.convert_to_traditional(sentence_cmn)

    # Add color to highlight current word
    sentence_cmn = sentence_cmn.replace(simplified_word, f"<span style='color: chartreuse'>{simplified_word}</span>")
    sentence_trad = sentence_trad.replace(trad_word, f"<span style='color: chartreuse'>{trad_word}</span>")

    requests.post(ANKI_ADDR, json={
        "action": "updateNoteFields",
        "version": 6,
        "params": {
            "note": {
                "id": note_id,
                "fields": {
                    "Sentence": sentence_cmn,
                    "Sentence Traditional": sentence_trad,
                    "Sentence Pinyin": sentence_pyn,
                    "Sentence Translation": sentence_eng,
                }
            }
        }
    })

print("✅ All cards updated with Traditional + generated example sentences.")
