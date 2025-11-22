# Generate example sentences for Anki cards. The best dictionary I have doesn't have examples,
# and most of my sources aren't super valid for sentence mining, so we make do. This rewrites
# ALL sentences, so could be a decent refresh for a deck once in a while. Also includes the
# sentence in traditional Chinese.

import requests
import random
import sys
from opencc import OpenCC
from pypinyin import lazy_pinyin, Style
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions

cc = OpenCC('s2t')
client = genai.Client()

ANKI_ADDR = "http://127.0.0.1:8765"
DECK_NAME = "Personal"

def progress_bar(curr, total, end=""):
    progress = (curr + 1) / total
    bar = int(progress * 30)  # bar width = 30 chars
    print(f"\rProgress: [{'#' * bar}{'.' * (30 - bar)}] {progress*100:6.0f}%", end=end)
    sys.stdout.flush()

def to_pinyin(sentence):
    py = lazy_pinyin(sentence, style=Style.TONE, v_to_u=True)
    return "".join(py)

def generate_example_sentence(word, all_words):
    # ChatML format, using Yi 1.5 6B
    # Get ChatGPT to replace this with a different format or longer sentences if you want.
    prompt = f"""
您正在为中文学习者生成自然的例句。

要求：
1. 可以使用列表中的词，但不必须全部来自列表。
2. 句子应自然流畅，正式程度不一。您可以同时使用俚语和正式用语。
3. 不超过 35 个字。
4. 只输出句子，不要解释。

已学词汇（可选用）：{" ".join(all_words)}
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        config=GenerateContentConfig(
            system_instruction=[prompt]
        ),
        contents=word
    )
    return response.text.strip()

# -----------------------
# 1. Get all notes
# -----------------------
print("Getting all notes for deck...\n")
query = f'deck:"{DECK_NAME}"'
notes = requests.post(ANKI_ADDR, json={
    "action": "findNotes",
    "version": 6,
    "params": {"query": query}
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
    print(f"→ Generating example sentence for: {simplified}")
    example = ""
    while len(example) < 5 or simplified not in example or example[-1] not in ['。', '！', '？']:
        # Helps the variety of words used in the example
        # By default, close by words from the list will be used in the example sentence
        random.shuffle(all_words)
        example = generate_example_sentence(simplified, all_words)

    pinyin_str = to_pinyin(example)
    print(f"   Example: {example} / {pinyin_str}")
    requests.post(ANKI_ADDR, json={
        "action": "updateNoteFields",
        "version": 6,
        "params": {
            "note": {
                "id": note_id,
                "fields": {
                    "Sentence": example,
                    "Sentence Traditional": cc.convert(example),
                    "Sentence Pinyin": pinyin_str,
                }
            }
        }
    })
    print()
    progress_bar(i, len(notes), end="\n")
print("✅ All cards updated with Traditional + generated example sentences.")

