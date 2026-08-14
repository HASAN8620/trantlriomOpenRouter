import os
import re
import json
import time
import requests

# 1. Load OpenRouter API Key
API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()

if not API_KEY:
    print("❌ Error: OPENROUTER_API_KEY Secret nahi mila. GitHub Settings check karein.")
    exit(1)

print("✅ OpenRouter API Key loaded successfully!")

input_file = "american.oxt"
output_file = "american_roman.oxt"
checkpoint_file = "translation_checkpoint.json"
batch_size = 15

# 🚀 Top Free Model on OpenRouter for Urdu Translation
MODEL_NAME = "google/gemma-2-9b-it:free"  # Ya "meta-llama/llama-3.3-70b-instruct:free"

# 2. Natural Urdu Prompt
SYSTEM_PROMPT = """You are a native Pakistani video game localization expert for Max Payne 3.
Translate English game dialogues into NATURAL, FLUENT, and DRAMATIC Pakistani Roman Urdu (WhatsApp style).

STRICT OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching the exact input keys. No explanation, no markdown tags.

RULES:
1. Use easy, natural Pakistani spoken Urdu (WhatsApp style).
2. STRICTLY FORBIDDEN HINDI WORDS:
   - NEVER 'shareer' -> use 'jism' or 'body'
   - NEVER 'samay' -> use 'waqt' or 'time'
   - NEVER 'dard nivaarak' -> use 'painkillers'
   - NEVER 'swasthya' -> use 'sehat'
   - NEVER 'karya' -> use 'kaam'
   - NEVER 'bhavnaon' -> use 'ehsaas'
   - NEVER 'khojne' -> use 'dhoondne'
   - NEVER 'vishesh' -> use 'khaas'
   - NEVER 'vah' -> use 'woh'
   - NEVER 'ladaai' -> use 'larai'
   - NEVER 'badi' / 'bada' -> use 'bari' / 'bara'
3. Keep gaming words in English: 'painkillers', 'ammo', 'guns', 'checkpoint', 'comfort zone', 'health', 'plan B'.
4. Keep all formatting tags (~z~, ~w~, ~n~, ~a~, ~g~, ~b~) EXACTLY as they appear."""

# 3. Fail-Safe Python Auto-Corrector
HINDI_TO_URDU = {
    r'\bsamay\b': 'waqt',
    r'\bshareer\b': 'jism',
    r'\bdard nivaarak\b': 'painkillers',
    r'\bswasthya\b': 'sehat',
    r'\bkarya\b': 'kaam',
    r'\bbhavnaon\b': 'ehsaas',
    r'\bkhojne\b': 'dhoondne',
    r'\bvishesh\b': 'khaas',
    r'\bvah\b': 'woh',
    r'\bladaai li\b': 'larai hui',
    r'\bladaai\b': 'larai',
    r'\bbadi\b': 'bari',
    r'\bbada\b': 'bara',
}

def clean_hindi_words(text):
    if not isinstance(text, str):
        return text
    for pattern, replacement in HINDI_TO_URDU.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

# 4. OpenRouter API Request
def translate_batch(batch_dict):
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    prompt = f"Translate the following JSON values to natural Pakistani Roman Urdu. Return a JSON object with the same keys:\n{json.dumps(batch_dict, ensure_ascii=False)}"
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com", # Required by OpenRouter
        "X-Title": "Max Payne Translator"
    }
    
    for attempt in range(5):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                res_data = response.json()
                content = res_data['choices'][0]['message']['content']
                
                try:
                    clean_content = content.strip()
                    if clean_content.startswith("```json"): clean_content = clean_content[7:]
                    if clean_content.startswith("```"): clean_content = clean_content[3:]
                    if clean_content.endswith("```"): clean_content = clean_content[:-3]
                    
                    parsed = json.loads(clean_content.strip())
                    if isinstance(parsed, dict) and parsed:
                        cleaned_parsed = {k: clean_hindi_words(v) for k, v in parsed.items()}
                        return cleaned_parsed
                except json.JSONDecodeError:
                    print(f"\n⚠️ JSON Parse Error. Retrying...", end="", flush=True)
                    
            elif response.status_code == 429:
                print(f"\n⚠️ Rate Limit! 10 seconds wait...", end="", flush=True)
                time.sleep(10)
                continue
            else:
                print(f"\n⚠️ ERROR {response.status_code}: {response.text[:100]}", flush=True)
                
        except Exception as e:
            print(f"\n⚠️ Connection Error: {str(e)[:50]}...", end="", flush=True)
            
        time.sleep(3)
        
    print("\n❌ OpenRouter Error.")
    exit(1)

# 5. Main Processing Logic
if os.path.exists(input_file):
    print(f"📁 Reading file: {input_file}", flush=True)
    
    saved_data = {}
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r", encoding="utf-8") as f: 
            try:
                saved_data = json.load(f)
                saved_data = {k: clean_hindi_words(v) for k, v in saved_data.items()}
                print(f"🔄 Checkpoint Loaded: {len(saved_data)} lines pehle se completed hain.", flush=True)
            except Exception:
                saved_data = {}

    with open(input_file, "r", encoding="utf-8", errors="ignore") as f: all_lines = f.readlines()
    pending_batch = {}
    total = 0

    for line in all_lines:
        if re.search(r'=\s*~(z|w)~', line):
            total += 1
            k = line.split('=', 1)[0].strip()
            if k not in saved_data:
                pending_batch[k] = line.split('=', 1)[1].strip()
                
            if len(pending_batch) >= batch_size:
                print(f"\n🚀 Translating via OpenRouter... ({len(saved_data)}/{total})", flush=True)
                res = translate_batch(pending_batch)
                if res:
                    saved_data.update(res)
                    with open(checkpoint_file, "w", encoding="utf-8") as cf: 
                        json.dump(saved_data, cf, ensure_ascii=False, indent=2)
                    print("✅ [Batch Saved Successfully]", flush=True)
                pending_batch = {}
                time.sleep(2.5)

    if pending_batch:
        res = translate_batch(pending_batch)
        if res:
            saved_data.update(res)
            with open(checkpoint_file, "w", encoding="utf-8") as cf: 
                json.dump(saved_data, cf, ensure_ascii=False, indent=2)

    print("\n🔨 Rebuilding american_roman.oxt file...", flush=True)
    count = 0
    with open(output_file, "w", encoding="utf-8") as out:
        for line in all_lines:
            if re.search(r'=\s*~(z|w)~', line):
                k = line.split('=', 1)[0].strip()
                if k in saved_data:
                    clean_text = clean_hindi_words(saved_data[k])
                    out.write(f"{k} = {clean_text}\n")
                    count += 1
                else: out.write(line)
            else: out.write(line)
            
    print(f"\n🎉 BOOM! SUCCESS! {count} lines OpenRouter Free Model se convert ho gayin!", flush=True)
else:
    print(f"❌ Error: '{input_file}' file nahi mili.", flush=True)
