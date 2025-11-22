# Generate example sentences for Anki cards. The best dictionary I have doesn't have examples,
# and most of my sources aren't super valid for sentence mining, so we make do. This rewrites
# ALL sentences, so could be a decent refresh for a deck once in a while. Also includes the
# sentence in traditional Chinese.

import requests
import random
import sys
from opencc import OpenCC
from pypinyin import lazy_pinyin, Style

cc = OpenCC('s2t')

ANKI_ADDR = "http://127.0.0.1:8765"
DECK_NAME = "Personal"

# Use whatever service you like. I'm using Yi 1.5 6B with Kobold because I cbs getting a proper
# API set up. Gippity is definitely better at this so I may have to swtich one day.
KOBOLDCPP_URL = "http://127.0.0.1:5001/api/v1/generate"

def generate_example_sentence(word, all_words):
    # ChatML format, using Yi 1.5 6B
    # Get ChatGPT to replace this with a different format or longer sentences if you want.
    prompt = f"""
<|im_start|>system
您正在为中文学习者生成自然的例句。

要求：
1. 必须使用词汇：{word}
2. 可以使用列表中的词，但不必须全部来自列表。
3. 句子需自然、口语化、真实，不要生硬拼凑。
4. 不超过 35 个字。
5. 只输出句子，不要解释。

已学词汇（可选用）：{', '.join(all_words)}

<|im_start|> user
晴天
<|im_end|>
<|im_start|> assistant
今天是个难得的晴天。
<|im_end|>

<|im_start|> user
便宜
<|im_end|>
<|im_start|> assistant
这家店的午餐很便宜。
<|im_end|>

<|im_start|> user
食物
<|im_end|>
<|im_start|> assistant
这里的食物味道不错。
<|im_end|>

<|im_start|> user
旅行
<|im_end|>
<|im_start|> assistant
我想去海边旅行几天。
<|im_end|>

<|im_start|> user
游客
<|im_end|>
<|im_start|> assistant
周末这里总是很多游客。
<|im_end|>

<|im_start|> user
方便
<|im_end|>
<|im_start|> assistant
住在地铁旁边真的很方便。
<|im_end|>

<|im_start|> user
颜色
<|im_end|>
<|im_start|> assistant
我喜欢这件外套的颜色。
<|im_end|>

<|im_start|> user
四川
<|im_end|>
<|im_start|> assistant
四川的汤很香，也很辣。
<|im_end|>

<|im_start|> user
照片
<|im_end|>
<|im_start|> assistant
这张照片拍得特别清楚。
<|im_end|>

<|im_start|> user
健康
<|im_end|>
<|im_start|> assistant
每天散步对健康很好。
<|im_end|>

<|im_start|> user
{word}
<|im_end|>
<|im_start|> assistant\n"""

    data = {
        "prompt": prompt,
        "max_length": 35,
        "temperature": 1.0,
        # "top_p": 0.95,
        "min_p": 0.05,
        "stop_sequence": ["<|im_end|>", "\n"]
    }

    try:
        response = requests.post(KOBOLDCPP_URL, json=data).json()
        text = response["results"][0]["text"].strip()
        return text
    except Exception as e:
        print("⚠️ KoboldCPP error:", e)
        return ""

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
