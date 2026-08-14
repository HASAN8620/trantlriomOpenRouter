import os
import re
import json
import time
import requests

# 1. Load OpenRouter API Keys
KEYS_ENV = os.environ.get("OPENROUTER_API_KEYS", "")
API_KEYS = [k.strip() for k in KEYS_ENV.split(",") if k.strip()]

if not API_KEYS:
    print("❌ Error: OPENROUTER_API_KEYS Secret nahi mila. GitHub Settings check karein.")
    exit(1)

print(f"✅ Total {len(API_KEYS)} OpenRouter API Keys loaded successfully! 🚀")

input_file = "american.oxt"
output_file = "american_roman.oxt"
checkpoint_file = "translation_checkpoint.json"
batch_size = 20

# 🌟 Best Free Model for Natural Pakistani Roman Urdu
MODEL_NAME = "google/gemma-4-31b:free"

curr_key_idx = 0

# 2. Natural Pakistani Roman Urdu Prompt
SYSTEM_PROMPT = """You are a native Pakistani video game localization expert for Max Payne 3.
Translate English game dialogues into NATURAL, EASY, FLUENT, and DRAMATIC Pakistani Roman Urdu (WhatsApp style).

STRICT OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching the exact input keys. Do NOT add markdown wrappers or extra text.

TRANSLATION RULES:
1. Translate into natural spoken Pakistani dialogue tone (NO LITERAL WORD-FOR-WORD TRANSLATION).
2. STRICTLY FORBIDDEN HINDI WORDS:
   - NEVER use 'shareer' -> use 'jism' or 'body'
   - NEVER use 'samay' -> use 'waqt' or 'time'
   - NEVER use 'dard nivaarak' -> use 'painkillers'
   - NEVER use 'swasthya' -> use 'sehat'
   - NEVER use 'karya' -> use 'kaam'
   - NEVER use 'bhavnaon' -> use 'ehsaas'
   - NEVER use 'khojne' -> use 'dhoondne'
   - NEVER use 'vishesh' -> use 'khaas'
   - NEVER use 'vah' -> use 'woh'
   - NEVER use 'ladaai' -> use 'larai'
   - NEVER use 'badi' / 'bada' -> use 'bari' / 'bara'
3. KEEP GAMING TERMS: Keep 'painkillers', 'ammo', 'guns', 'checkpoint', 'comfort zone', 'health', 'plan B' in English.
4. FORMATTING TAGS: Keep all formatting tags (~z~, ~w~, ~n~, ~a~, ~g~, ~b~) EXACTLY as they appear."""

# 3. Python Auto-Corrector Engine
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

# 4. Translation Function with Key Rotation
def translate_batch(batch_dict):
    global curr_key_idx
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
    
    max_attempts = len(API_KEYS) * 3
    
    for attempt in range(max_attempts):
        headers = {
            "Authorization": f"Bearer {API_KEYS[curr_key_idx]}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
            "X-Title": "Max Payne Translator"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            
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
                    print(f"\n⚠️ JSON Decode Error. Retrying...", end="", flush=True)
                    
            elif response.status_code in [429, 402]:
                print(f"\n⚠️ Key #{curr_key_idx + 1} Limit Hit/Paused. Switching to next key...", end="", flush=True)
                curr_key_idx = (curr_key_idx + 1) % len(API_KEYS)
                time.sleep(1)
                continue
            else:
                print(f"\n⚠️ ERROR {response.status_code}: {response.text[:100]}", flush=True)
                
        except Exception as e:
            print(f"\n⚠️ Connection Error: {str(e)[:50]}...", end="", flush=True)
            
        curr_key_idx = (curr_key_idx + 1) % len(API_KEYS)
        time.sleep(1)
        
    print("\n❌ Saari OpenRouter keys paused ho gayin.")
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
                print(f"\n🚀 Translating via OpenRouter Gemma... ({len(saved_data)}/{total})", flush=True)
                res = translate_batch(pending_batch)
                if res:
                    saved_data.update(res)
                    with open(checkpoint_file, "w", encoding="utf-8") as cf: 
                        json.dump(saved_data, cf, ensure_ascii=False, indent=2)
                    print("✅ [Batch Saved Successfully]", flush=True)
                pending_batch = {}
                time.sleep(1.0)

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
            
    print(f"\n🎉 BOOM! SUCCESS! {count} lines Perfect Roman Urdu mein convert ho gayin!", flush=True)
else:
    print(f"❌ Error: '{input_file}' file nahi mili.", flush=True)
