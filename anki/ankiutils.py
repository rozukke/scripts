import requests
import random
import sys
import json
import re

import jieba
import generate_examples_llm
from pypinyin import pinyin, Style
from tatoeba_ingest import query
from opencc import OpenCC

cc_s2t = OpenCC('s2t')
cc_t2s = OpenCC('t2s')

def show_progress_bar(curr, total, end=""):
    progress = (curr + 1) / total
    bar = int(progress * 30)  # bar width = 30 chars
    print(f"\rProgress: [{'#' * bar}{'.' * (30 - bar)}] {progress*100:6.0f}%", end=end)
    sys.stdout.flush()

def get_example_sentence_from_db(word):
    results = query(word)
    if results:
        return results[0]
    else:
        print(f"Could not find example sentence for {word}")
        return None

def word_aware_in_sentence(word, sentence) -> bool:
    return word in jieba.cut(sentence)

def convert_to_traditional(text):
    return cc_s2t.convert(text)

def convert_to_simplified(text):
    return cc_s2t.convert(text)

def is_simplified(text) -> bool:
    return cc_t2s.convert(text) != text

def get_word_aware_pinyin(text):
    # 1. Use jieba to cut the sentence into semantic words
    # e.g., "我喜欢吃饺子" -> ["我", "喜欢", "吃", "饺子"]
    words = jieba.cut(text)

    agglutinated_chunks = []

    for word in words:
        # 2. Convert each semantic word to pinyin
        # pinyin() returns a list of lists, e.g., [['xǐ'], ['huan']]
        py_list = pinyin(word, style=Style.TONE)

        # 3. Join the syllables within that word together
        # [['xǐ'], ['huan']] -> "xǐhuan"
        flat_word = "".join([item[0] for item in py_list])
        agglutinated_chunks.append(flat_word)

    # 4. Join the words with a space
    return " ".join(agglutinated_chunks)

# Use whatever service you like. I'm using Yi 1.5 6B with Kobold because I cbs getting a proper
# API set up. Gippity is definitely better at this so I may have to swtich one day.
KOBOLDCPP_URL = "http://127.0.0.1:5001/api/v1/generate"

def generate_example_trans(sentence):
    # ChatML format
    prompt = f"""
<|im_start|>system
您是一个中文辅助助手。
任务：接收一个中文句子，并以 JSON 格式输出以下字段：
1. "eng": 自然准确的英文翻译。

<|im_start|> user
今天天气真好。
<|im_end|>
<|im_start|> assistant
{{
  "eng": "The weather is really good today."
}}
<|im_end|>

<|im_start|> user
我想买一杯咖啡，带走。
<|im_end|>
<|im_start|> assistant
{{
  "eng": "I would like to buy a cup of coffee, take away."
}}
<|im_end|>

<|im_start|> user
这家店的衣服太贵了。
<|im_end|>
<|im_start|> assistant
{{
  "eng": "The clothes in this shop are too expensive."
}}
<|im_end|>

<|im_start|> user
{sentence}
<|im_end|>
<|im_start|> assistant
"""

    data = {
        "prompt": prompt,
        "max_length": 150,
        "temperature": 0.4,
        "min_p": 0.05,
        "stop_sequence": ["<|im_end|>"]
    }

    try:
        response = requests.post(KOBOLDCPP_URL, json=data).json()
        raw_text = response["results"][0]["text"].strip()

        match = re.search(r"\{.*\}", raw_text, re.DOTALL)

        if match:
            json_str = match.group(0)
            parsed_data = json.loads(json_str)

            # Validation: Ensure all three keys exist
            if "eng" in parsed_data.keys():
                return parsed_data
            else:
                print(f"⚠️ Missing field 'eng' in: {raw_text}")
                return None

    except json.JSONDecodeError:
        print(f"⚠️ JSON Decode Error. Raw text: {raw_text}")
        return None
    except Exception as e:
        print(f"⚠️ KoboldCPP API error: {e}")
        return None


def generate_example_sentence(word):
    """
    Use KoboldCPP to generate an example sentence with translation. Tries repeatedly until a well-formed response is returned.
    """
    example = {
        "cmn": "",
        "eng": "",
    }
    while len(example["cmn"]) < 5 or word not in example["cmn"] or example["cmn"][-1] not in ['。', '！', '？']:
        example = _generate_example_sentence(word)
    return example

def _generate_example_sentence(word):
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
        "rep_pen": 1.05,
        "rep_pen_range": 10,
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
