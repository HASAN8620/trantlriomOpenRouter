import os
import re
import json
import time
import requests
import sys

# ==========================================
# 1. API KEYS SETUP & ROTATION ENGINE
# ==========================================
KEYS_ENV = os.environ.get("OPENROUTER_API_KEYS", "")
API_KEYS = [k.strip() for k in KEYS_ENV.split(",") if k.strip()]

if not API_KEYS:
    print("❌ ERROR: OPENROUTER_API_KEYS secret nahi mila. GitHub Settings check karein.")
    sys.exit(1)

print(f"✅ SYSTEM: Total {len(API_KEYS)} OpenRouter Keys Loaded! 🚀")

INPUT_FILE = "american.oxt"
OUTPUT_FILE = "american_roman.oxt"
CHECKPOINT_FILE = "translation_checkpoint.json"
BATCH_SIZE = 15  # Optimal for 31B models to prevent context cutoff
MODEL_NAME = "google/gemma-2-9b-it:free"
curr_key_idx = 0

# ==========================================
# 2. HIGH-LEVEL PROMPT (MAX PAYNE PAKISTANI TONE)
# ==========================================
SYSTEM_PROMPT = """You are an elite video game localization expert from Pakistan.
Your task is to translate Max Payne 3 English dialogues into NATURAL, DRAMATIC, and GRITTY Pakistani Roman Urdu (WhatsApp style).

STRICT OUTPUT RULES:
1. You MUST respond with ONLY a valid JSON object matching the exact input keys. NO markdown, NO explanations, NO intro/outro text.
2. The tone must be mature, cynical, and native to a Pakistani speaker (e.g., using words like 'khauf', 'tabahi', 'azab', 'sakoon').
3. NEVER do literal word-for-word translation. Capture the true feeling and emotion of the scene.

STRICTLY FORBIDDEN HINDI WORDS (MUST USE URDU EQUIVALENTS):
- NEVER use 'shareer' -> use 'jism' or 'body'
- NEVER use 'samay' -> use 'waqt' or 'time'
- NEVER use 'dard nivaarak' -> use 'painkillers'
- NEVER use 'swasthya' -> use 'sehat'
- NEVER use 'karya' -> use 'kaam'
- NEVER use 'bhavnaon' -> use 'ehsaas' or 'jazbaat'
- NEVER use 'khojne' -> use 'dhoondne'
- NEVER use 'vishesh' -> use 'khaas'
- NEVER use 'vah' -> use 'woh'
- NEVER use 'ladaai' -> use 'larai'
- NEVER use 'badi' / 'bada' -> use 'bari' / 'bara'
- NEVER use 'prayas' -> use 'koshish'

GAMING TERMS TO KEEP IN ENGLISH:
'painkillers', 'ammo', 'guns', 'checkpoint', 'comfort zone', 'health', 'plan B', 'cops', 'cover'.

FORMATTING:
Keep ALL formatting tags (~z~, ~w~, ~n~, ~a~, ~g~, ~b~) EXACTLY in their original positions."""

# ==========================================
# 3. PYTHON AUTO-CORRECTOR (LAST LINE OF DEFENSE)
# ==========================================
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
    r'\bprayas\b': 'koshish'
}

def clean_hindi_words(text):
    if not isinstance(text, str):
        return text
    for pattern, replacement in HINDI_TO_URDU.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

# ==========================================
# 4. TRANSLATION BATCH FUNCTION (WITH RETRIES)
# ==========================================
def translate_batch(batch_dict):
    global curr_key_idx
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    prompt = f"Translate to Roman Urdu. Return ONLY JSON:\n{json.dumps(batch_dict, ensure_ascii=False)}"
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    max_attempts = len(API_KEYS) * 2
    
    for attempt in range(max_attempts):
        headers = {
            "Authorization": f"Bearer {API_KEYS[curr_key_idx]}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",
            "X-Title": "Max Payne Pakistani Localizer"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=50)
            
            if response.status_code == 200:
                res_data = response.json()
                content = res_data['choices'][0]['message']['content']
                
                # Cleanup potential Markdown
                clean_content = content.strip()
                if clean_content.startswith("```json"): clean_content = clean_content[7:]
                if clean_content.startswith("```"): clean_content = clean_content[3:]
                if clean_content.endswith("```"): clean_content = clean_content[:-3]
                
                try:
                    parsed = json.loads(clean_content.strip())
                    if isinstance(parsed, dict) and parsed:
                        return {k: clean_hindi_words(v) for k, v in parsed.items()}
                except json.JSONDecodeError:
                    print(f"\n⚠️ JSON Decode Error. Retrying API...", end="", flush=True)
                    
            elif response.status_code in [429, 402]:
                print(f"\n⚠️ Key #{curr_key_idx + 1} Limit Hit. Switching Key...", end="", flush=True)
                curr_key_idx = (curr_key_idx + 1) % len(API_KEYS)
                time.sleep(2)
                continue
            else:
                print(f"\n⚠️ API ERROR {response.status_code}: {response.text[:100]}", flush=True)
                
        except Exception as e:
            print(f"\n⚠️ Connection Error. Checking next key...", end="", flush=True)
            
        curr_key_idx = (curr_key_idx + 1) % len(API_KEYS)
        time.sleep(2)
        
    print("\n❌ CRITICAL: Saari API Keys thak chuki hain. Safe Exit kar rahe hain taake GitHub auto-save kar le.")
    sys.exit(1) # Exits cleanly to trigger the GitHub Actions auto-save

# ==========================================
# 5. CORE LOGIC & RESUME SYSTEM
# ==========================================
if not os.path.exists(INPUT_FILE):
    print(f"❌ ERROR: '{INPUT_FILE}' file nahi mili.")
    sys.exit(1)

print(f"📁 Reading source file: {INPUT_FILE}", flush=True)

saved_data = {}
# 🔄 RESUME CHECK
if os.path.exists(CHECKPOINT_FILE):
    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f: 
        try:
            saved_data = json.load(f)
            saved_data = {k: clean_hindi_words(v) for k, v in saved_data.items()}
            print(f"🔄 RESUME ACTIVE: {len(saved_data)} lines ka backup mil gaya. Yahan se aage shuru kar rahe hain!", flush=True)
        except Exception:
            saved_data = {}

with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f: 
    all_lines = f.readlines()

pending_batch = {}
total_dialogues = 0

# Count total valid dialogues first
for line in all_lines:
    if re.search(r'=\s*~(z|w)~', line):
        total_dialogues += 1

print(f"🎯 Total Dialogues to Translate: {total_dialogues}")

for line in all_lines:
    if re.search(r'=\s*~(z|w)~', line):
        k = line.split('=', 1)[0].strip()
        
        # SKIP IF ALREADY TRANSLATED (RESUME LOGIC)
        if k not in saved_data:
            pending_batch[k] = line.split('=', 1)[1].strip()
            
        if len(pending_batch) >= BATCH_SIZE:
            current_progress = len(saved_data) + len(pending_batch)
            print(f"\n🚀 Translating Batch... ({current_progress}/{total_dialogues})", flush=True)
            
            res = translate_batch(pending_batch)
            if res:
                saved_data.update(res)
                # 💾 INSTANT CHECKPOINT SAVE
                with open(CHECKPOINT_FILE, "w", encoding="utf-8") as cf: 
                    json.dump(saved_data, cf, ensure_ascii=False, indent=2)
                print("✅ [Saved to Checkpoint]", flush=True)
            
            pending_batch = {}
            time.sleep(1.5)

# Process any remaining lines
if pending_batch:
    res = translate_batch(pending_batch)
    if res:
        saved_data.update(res)
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as cf: 
            json.dump(saved_data, cf, ensure_ascii=False, indent=2)

print("\n🔨 Rebuilding final american_roman.oxt file...", flush=True)
converted_count = 0

with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    for line in all_lines:
        if re.search(r'=\s*~(z|w)~', line):
            k = line.split('=', 1)[0].strip()
            if k in saved_data:
                clean_text = clean_hindi_words(saved_data[k])
                out.write(f"{k} = {clean_text}\n")
                converted_count += 1
            else: 
                out.write(line)
        else: 
            out.write(line)
        
print(f"\n🎉 BOOM! {converted_count}/{total_dialogues} lines Successfully Converted to Max Payne Roman Urdu!", flush=True)
