# Generate example sentences for Anki cards. The best dictionary I have doesn't have examples,
# and most of my sources aren't super valid for sentence mining, so we make do. This rewrites
# ALL sentences, so could be a decent refresh for a deck once in a while. Also includes the
# sentence in traditional Chinese.


import json
import re
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

def generate_example_sentence(word):
    # ChatML format, using Yi 1.5 6B
    prompt = f"""
<|im_start|>system
您正在为中文学习者生成自然的例句。

要求：
1. 句子需自然、口语化、真实，句式稍微丰富一些（不仅仅是简单句）。
2. 不超过 35 个字。
3. 请以 JSON 格式输出，包含中文句子 (cmn) 和英文翻译 (eng)。

<|im_start|> user
晴天
<|im_end|>
<|im_start|> assistant
{{
  "cmn": "既然今天是个难得的晴天，我们可以去公园野餐。",
  "eng": "Since it is a rare sunny day today, we can go to the park for a picnic."
}}
<|im_end|>

<|im_start|> user
便宜
<|im_end|>
<|im_start|> assistant
{{
  "cmn": "这家店的午餐不仅味道很好，而且价格非常便宜。",
  "eng": "The lunch at this shop is not only delicious but also very cheap."
}}
<|im_end|>

<|im_start|> user
食物
<|im_end|>
<|im_start|> assistant
{{
  "cmn": "如果你喜欢辣的食物，那你一定要尝尝这道菜。",
  "eng": "If you like spicy food, you must try this dish."
}}
<|im_end|>

<|im_start|> user
旅行
<|im_end|>
<|im_start|> assistant
{{
  "cmn": "为了放松心情，我计划下个月去海边旅行几天。",
  "eng": "In order to relax, I plan to travel to the seaside for a few days next month."
}}
<|im_end|>

<|im_start|> user
游客
<|im_end|>
<|im_start|> assistant
{{
  "cmn": "因为现在是假期，所以在这个景点看到了很多游客。",
  "eng": "Because it is the holidays, I saw many tourists at this attraction."
}}
<|im_end|>

<|im_start|> user
方便
<|im_end|>
<|im_start|> assistant
{{
  "cmn": "住在这个小区很方便，楼下就有24小时便利店和地铁站。",
  "eng": "Living in this neighborhood is convenient; there is a 24-hour convenience store and subway station downstairs."
}}
<|im_end|>

<|im_start|> user
颜色
<|im_end|>
<|im_start|> assistant
{{
  "cmn": "这件外套的颜色很特别，穿在身上显得很有精神。",
  "eng": "The color of this coat is unique; it makes you look energetic when wearing it."
}}
<|im_end|>

<|im_start|> user
四川
<|im_end|>
<|im_start|> assistant
{{
  "cmn": "虽然四川菜有点辣，但是我的外国朋友们都非常喜欢吃。",
  "eng": "Although Sichuan food is a bit spicy, my foreign friends all really like eating it."
}}
<|im_end|>

<|im_start|> user
照片
<|im_end|>
<|im_start|> assistant
{{
  "cmn": "我们可以拍一张照片，留作这次聚会的纪念吗？",
  "eng": "Can we take a photo as a souvenir of this gathering?"
}}
<|im_end|>

<|im_start|> user
健康
<|im_end|>
<|im_start|> assistant
{{
  "cmn": "为了保持身体健康，他坚持每天早上跑五公里。",
  "eng": "To stay healthy, he insists on running 5km every morning."
}}
<|im_end|>

<|im_start|> user
{word}
<|im_end|>
<|im_start|> assistant
"""

    data = {
        "prompt": prompt,
        "max_length": 100,
        "temperature": 0.8, # Slightly lowered to ensure valid JSON syntax
        "min_p": 0.05,
        "stop_sequence": ["<|im_end|>"]
    }

    try:
        response = requests.post(KOBOLDCPP_URL, json=data).json()
        raw_text = response["results"][0]["text"].strip()
        print(f"Gen attempt: {raw_text}")

        match = re.search(r"\{.*\}", raw_text, re.DOTALL)

        if match:
            json_str = match.group(0)
            parsed_data = json.loads(json_str)

            # Validation: Ensure specific keys exist
            if "cmn" in parsed_data and "eng" in parsed_data:
                return parsed_data

        print(f"⚠️ Invalid JSON structure received: {raw_text}")
        return None

    except json.JSONDecodeError:
        print(f"⚠️ JSON Decode Error. Raw text: {raw_text}")
        return None
    except Exception as e:
        print(f"⚠️ KoboldCPP API error: {e}")
        return None

def progress_bar(curr, total, end=""):
    progress = (curr + 1) / total
    bar = int(progress * 30)  # bar width = 30 chars
    print(f"\rProgress: [{'#' * bar}{'.' * (30 - bar)}] {progress*100:6.0f}%", end=end)
    sys.stdout.flush()

def to_pinyin(sentence):
    py = lazy_pinyin(sentence, style=Style.TONE, v_to_u=True)
    return " ".join(py)

def get_example_wrapper(simplified_word):
    example = {
        "cmn": "",
        "eng": "",
    }
    while len(example["cmn"]) < 5 or simplified_word not in example["cmn"] or example["cmn"][-1] not in ['。', '！', '？']:
        example = generate_example_sentence(simplified_word)

    return example

if __name__ == "__main__":
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

    print(f"\n\n📘 Found {len(note_data.keys())} words.")


    # -----------------------
    # 3. Process each note: update Traditional + generate Example
    # -----------------------
    for i, note_id in enumerate(notes):
        info = note_data[note_id]

        simplified = info['fields']['Simplified']['value']

        # --- Generate example sentence ---
        print(f"→ Generating example sentence for: {simplified}")
        example = get_example_wrapper(simplified)

        pinyin_str = to_pinyin(example["cmn"])
        print(f"   Example: {example["cmn"]} / {pinyin_str} / {example["eng"]}")
        # requests.post(ANKI_ADDR, json={
        #     "action": "updateNoteFields",
        #     "version": 6,
        #     "params": {
        #         "note": {
        #             "id": note_id,
        #             "fields": {
        #                 "Sentence": example,
        #                 "Sentence Traditional": cc.convert(example),
        #                 "Sentence Pinyin": pinyin_str,
        #             }
        #         }
        #     }
        # })
        print()
        progress_bar(i, len(notes), end="\n")

    print("✅ All cards updated with Traditional + generated example sentences.")
