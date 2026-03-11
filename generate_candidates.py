#!/usr/bin/env python3
"""
Piyo 繪本審校候選生成器

用途：針對審校發現的問題，批量生成 TTS 音檔與場景圖的候選版本，
     供人工挑選後一鍵替換。

每次審校只需修改頂部 REVIEW CONFIG 區塊。

Usage:
  python3 generate_candidates.py tts                     # 生成 TTS 候選
  python3 generate_candidates.py images                  # 生成場景圖候選
  python3 generate_candidates.py images --priority P0    # 只跑指定優先級
  python3 generate_candidates.py apply --audio P03=c2 P07=c4 --images P01=c1
"""

import os
import sys
import json
import time
import base64
import shutil
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CANDIDATES_DIR = os.path.join(SCRIPT_DIR, "candidates")

# ══════════════════════════════════════════════════════════════
# REVIEW CONFIG — 每次審校修改此區塊
# ══════════════════════════════════════════════════════════════

TTS_CONFIG = {
    "story": "金髮女孩與三隻熊",
    "lang": "TC",
    "num_candidates": 5,
    "seeds": [42, 1337, 8888, 2024, 7777],
    "stability": 1.0,           # 高穩定度改善發音準確性
    "similarity_boost": 0.75,
    "style": 0.0,
    "pages": {
        "standard": ["P03", "P07", "P08", "P14"],
        "toddler":  ["P05", "P06", "P07"],
    },
    # apply 時的目標路徑（相對於 4_previewGen/）
    "targets": {
        ("standard", "P03"): "final/goldilocks-and-the-three-bears/ZH-TW/standard/P03_v1.mp3",
        ("standard", "P07"): "final/goldilocks-and-the-three-bears/ZH-TW/standard/P07_v1.mp3",
        ("standard", "P08"): "final/goldilocks-and-the-three-bears/ZH-TW/standard/P08_v1.mp3",
        ("standard", "P14"): "final/goldilocks-and-the-three-bears/ZH-TW/standard/P14_v1.mp3",
        ("toddler", "P05"):  "final/goldilocks-and-the-three-bears/ZH-TW/toddler/P05.mp3",
        ("toddler", "P06"):  "final/goldilocks-and-the-three-bears/ZH-TW/toddler/P06_v2.mp3",
        ("toddler", "P07"):  "final/goldilocks-and-the-three-bears/ZH-TW/toddler/P07_v1.mp3",
    },
}

IMAGE_CONFIG = {
    "story_name": "三隻小豬",
    "num_candidates": 3,
    "pages": [
        # ── B-2：角色肢體修正（P0 優先）──
        {
            "page": "P09", "priority": "P0",
            "prompt_extra": (
                "CRITICAL ANATOMY CONSTRAINT: Every pig character must have EXACTLY 2 legs "
                "and EXACTLY 2 arms. NO extra limbs, NO third leg, NO additional appendages. "
                "When running, legs must be clearly separated with NO ambiguous overlap that "
                "could look like a third limb. Count: each pig = 2 arms + 2 legs = 4 limbs total.\n\n"
            ),
            "negative_extra": "extra legs, third leg, extra limbs, extra feet, merged limbs, ambiguous limb count, three legs",
        },
        {
            "page": "P10", "priority": "P0",
            "prompt_extra": (
                "CRITICAL ANATOMY CONSTRAINT: Every pig character must have EXACTLY 2 legs "
                "and EXACTLY 2 arms. NO extra limbs, NO third leg, NO additional appendages. "
                "Ensure running piglets have clearly correct limb count — 2 legs each.\n\n"
            ),
            "negative_extra": "extra legs, third leg, extra limbs, extra feet, merged limbs, ambiguous limb count, three legs",
        },
        # ── B-1：偏灰偏淡修正（P1 優先）──
        {
            "page": "P01", "priority": "P1",
            "prompt_extra": (
                "COLOR REQUIREMENT: This outdoor scene must be bright and vibrant with GOOD color "
                "saturation. Colors should be vivid enough for 2-3 year olds to easily distinguish "
                "characters on a small mobile screen. Use the visibility level of Goldilocks story P01 "
                "as the standard. Avoid pale, washed-out, or grey-tinted colors.\n\n"
            ),
            "style_override": True,
        },
        {
            "page": "P02", "priority": "P1",
            "prompt_extra": (
                "COLOR REQUIREMENT: Outdoor scene must be bright and vibrant with GOOD saturation. "
                "Vivid enough for toddlers on small screens. NOT washed-out or grey.\n\n"
            ),
            "style_override": True,
        },
        {
            "page": "P03", "priority": "P1",
            "prompt_extra": (
                "COLOR REQUIREMENT: Outdoor scene must be bright and vibrant with GOOD saturation. "
                "Vivid enough for toddlers on small screens. NOT washed-out or grey.\n\n"
            ),
            "style_override": True,
        },
        {
            "page": "P04", "priority": "P1",
            "prompt_extra": (
                "COLOR REQUIREMENT: Outdoor scene must be bright and vibrant with GOOD saturation. "
                "Background must NOT be pale or washed-out. Vivid enough for toddlers on small screens.\n\n"
            ),
            "style_override": True,
        },
    ],
    # apply 時的目標路徑（使用者會另行指定，此處僅記錄候選圖放置位置）
    "targets": {},
}

# ══════════════════════════════════════════════════════════════
# TTS GENERATION
# ══════════════════════════════════════════════════════════════

def generate_tts_candidates():
    """生成 TTS 候選音檔"""
    from elevenlabs.client import ElevenLabs
    from elevenlabs import PronunciationDictionaryVersionLocator

    cfg = TTS_CONFIG

    # Load parsed scripts
    parsed_path = os.path.join(PROJECT_ROOT, "3_ttsGen", "parsed_scripts.json")
    with open(parsed_path, "r", encoding="utf-8") as f:
        parsed = json.load(f)

    # Load pronunciation dictionary config
    dict_path = os.path.join(PROJECT_ROOT, "3_ttsGen", "tc_pronunciation_dict.json")
    with open(dict_path, "r", encoding="utf-8") as f:
        tc_dict = json.load(f)

    # ElevenLabs client
    api_key = _get_elevenlabs_api_key()
    client = ElevenLabs(api_key=api_key)

    pron_locators = [PronunciationDictionaryVersionLocator(
        pronunciation_dictionary_id=tc_dict["id"],
        version_id=tc_dict["version_id"],
    )]

    lang_code = {"TC": "zh", "EN": "en", "JP": "ja"}[cfg["lang"]]

    # Count total
    total = sum(len(pages) for pages in cfg["pages"].values()) * cfg["num_candidates"]
    done = 0
    errors = []

    print(f"\n{'=' * 60}")
    print(f"🎙️  TTS 候選生成: {cfg['story']} — {cfg['lang']}")
    print(f"   頁數: {sum(len(p) for p in cfg['pages'].values())} × {cfg['num_candidates']} = {total} 個音檔")
    print(f"   stability: {cfg['stability']}")
    print(f"{'=' * 60}\n")

    for version, page_list in cfg["pages"].items():
        out_dir = os.path.join(CANDIDATES_DIR, "audio", version)
        os.makedirs(out_dir, exist_ok=True)

        print(f"  📂 {version} ({len(page_list)} pages)")

        story_data = parsed[cfg["story"]][cfg["lang"]][version]

        for page_key in page_list:
            if page_key not in story_data:
                print(f"    ⚠️  {page_key} 不在 parsed_scripts.json 中，跳過")
                continue

            page = story_data[page_key]
            all_inputs = [inp for seg in page["segments"] for inp in seg]
            text = "\n".join(inp["text"] for inp in all_inputs)
            voice_id = all_inputs[0]["voice_id"]

            for ci in range(1, cfg["num_candidates"] + 1):
                seed = cfg["seeds"][ci - 1]
                out_mp3 = os.path.join(out_dir, f"{page_key}_c{ci}.mp3")
                out_json = os.path.join(out_dir, f"{page_key}_c{ci}.json")

                # Skip if already exists
                if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 0 and os.path.exists(out_json):
                    done += 1
                    print(f"    ⏭️  {page_key}_c{ci} (已存在)")
                    continue

                print(f"    🎙️  [{done+1}/{total}] {page_key}_c{ci} (seed={seed})", end="", flush=True)

                result = _tts_generate_with_retry(
                    client, text, voice_id, lang_code, seed,
                    cfg["stability"], cfg["similarity_boost"], cfg["style"],
                    pron_locators, out_mp3,
                )

                done += 1

                if isinstance(result, int):
                    print(f" ✅ {result} chars")
                else:
                    print(f" ❌ {result}")
                    errors.append(f"{version}/{page_key}_c{ci}: {result}")

                time.sleep(3)

    print(f"\n{'=' * 60}")
    print(f"📊 TTS 生成完成！成功: {done - len(errors)}, 失敗: {len(errors)}")
    if errors:
        for e in errors:
            print(f"   ❌ {e}")
    print(f"📁 輸出: {os.path.join(CANDIDATES_DIR, 'audio')}")
    print(f"{'=' * 60}")


def _tts_generate_with_retry(client, text, voice_id, lang_code, seed,
                              stability, similarity_boost, style,
                              pron_locators, output_path, max_retries=3):
    """呼叫 ElevenLabs API 生成音檔 + alignment，帶 retry"""
    for attempt in range(max_retries):
        try:
            response = client.text_to_speech.convert_with_timestamps(
                text=text,
                voice_id=voice_id,
                model_id="eleven_v3",
                language_code=lang_code,
                seed=seed,
                output_format="mp3_44100_128",
                voice_settings={
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style,
                },
                apply_text_normalization="auto",
                pronunciation_dictionary_locators=pron_locators,
            )

            # Save MP3
            audio_bytes = base64.b64decode(response.audio_base_64)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)

            # Save alignment JSON
            alignment_path = output_path.replace(".mp3", ".json")
            alignment_data = {}
            if response.alignment:
                alignment_data["alignment"] = {
                    "characters": list(response.alignment.characters),
                    "character_start_times_seconds": list(response.alignment.character_start_times_seconds),
                    "character_end_times_seconds": list(response.alignment.character_end_times_seconds),
                }
            if response.normalized_alignment:
                alignment_data["normalized_alignment"] = {
                    "characters": list(response.normalized_alignment.characters),
                    "character_start_times_seconds": list(response.normalized_alignment.character_start_times_seconds),
                    "character_end_times_seconds": list(response.normalized_alignment.character_end_times_seconds),
                }
            with open(alignment_path, "w", encoding="utf-8") as f:
                json.dump(alignment_data, f, ensure_ascii=False, indent=2)

            return len(text)

        except Exception as e:
            wait = 3 * (2 ** attempt)
            print(f"\n      ⚠️  Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"      ⏳ Retrying in {wait}s...")
                time.sleep(wait)
            else:
                return str(e)


def _get_elevenlabs_api_key():
    """從環境變數或 tts_generate_full.py 取得 API key"""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return key
    # Fallback: read from existing script
    script_path = os.path.join(PROJECT_ROOT, "3_ttsGen", "tts_generate_full.py")
    with open(script_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("API_KEY"):
                # Extract string value
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                return key
    raise RuntimeError("找不到 ElevenLabs API key")


# ══════════════════════════════════════════════════════════════
# IMAGE GENERATION
# ══════════════════════════════════════════════════════════════

# Scene gen 常數（從 2_sceneGen/scene_gen.py 複製，避免 import 副作用）
_CORE_STYLE = """
Style: Japanese children's picture book illustration,
iyashikei healing style, soft pastel low-saturation colors,
color palette of mint green and cream and soft peach and powder blue,
rounded kawaii character design with dot eyes and minimal features,
gentle hand-drawn texture with subtle paper grain,
soft diffused lighting with no hard shadows,
clean composition with generous breathing space,
warm quiet cozy atmosphere,
2-3 head-to-body ratio for characters,
very soft warm grey outlines instead of black"""

_CORE_STYLE_BRIGHT = """
Style: Japanese children's picture book illustration,
iyashikei healing style, soft pastel colors with GOOD saturation and brightness,
color palette of mint green and cream and soft peach and powder blue,
rounded kawaii character design with dot eyes and minimal features,
gentle hand-drawn texture with subtle paper grain,
soft diffused lighting with no hard shadows,
clean composition with generous breathing space,
warm quiet cozy atmosphere,
2-3 head-to-body ratio for characters,
very soft warm grey outlines instead of black"""

_QUALITY_TAGS = """
high quality, detailed illustration, professional children's book art,
consistent character design, soft digital watercolor texture,
high resolution, print-ready"""

_NEGATIVE_PROMPT = """
Avoid: realistic, photographic, 3D render, CGI,
sharp anime linework, Disney style, Pixar style,
dark shadows, horror, scary, gore,
high saturation, neon colors, vivid colors, pure black,
black outlines, sharp edges, angular shapes,
cluttered composition, busy background,
ABSOLUTELY NO text, NO words, NO letters, NO numbers, NO writing of any kind anywhere in the image,
no speech bubbles, no captions, no labels, no signs with text,
watermark, signature, logo, frame, border,
deformed hands, extra fingers, distorted faces, extra limbs"""

_CHARACTER_REGISTRY = {
    "大毛": {
        "en": "Biggie",
        "lock": "mochi-round pale pink piglet, biggest floppy ears, cream straw hat, pale blue overalls, dot eyes, pink cheek blush, 2-head proportion",
        "ref_file": "大毛.png",
    },
    "二毛": {
        "en": "Woody",
        "lock": "medium orange-pink piglet, backwards red cap, green apron, slightly cocky dot eyes, pink cheeks, 2-head proportion",
        "ref_file": "二毛.png",
    },
    "小毛": {
        "en": "Bricky",
        "lock": "smallest pale pink piglet, yellow round hard hat, orange vest, bright determined dot eyes, pink cheeks, neatest posture, 2-head proportion",
        "ref_file": "小毛.png",
    },
    "豬媽媽": {
        "en": "Mama Pig",
        "lock": "largest plump pink pig, floral apron, gentle ^_^ eyes, droopy ears",
        "ref_file": "豬媽媽.png",
    },
    "大野狼": {
        "en": "Big Bad Wolf",
        "lock": "round grey wolf, round dot shifty eyes, round snout NO fangs, faded purple vest, goofy not scary, slouchy posture",
        "ref_file": "大野狼.png",
    },
}

_HEIGHT_RULES = [
    ("大野狼", "豬媽媽", "Wolf is about 1.3x taller than Mama Pig"),
    ("豬媽媽", "大毛", "Mama Pig is about 1.4x taller than piglets"),
    ("大野狼", "大毛", "Wolf is about 1.8x taller than piglets"),
    ("大毛", "二毛", "Biggie and Woody are approximately the same height"),
    ("二毛", "小毛", "Bricky is slightly shorter than Woody"),
]


def generate_image_candidates(priority_filter=None):
    """生成場景圖候選"""
    from openai import OpenAI

    cfg = IMAGE_CONFIG
    client = OpenAI()

    # Load scene data from scene_gen.py
    scene_data = _load_scene_data(cfg["story_name"])

    # Filter by priority if specified
    pages = cfg["pages"]
    if priority_filter:
        pages = [p for p in pages if p["priority"] == priority_filter]

    total = len(pages) * cfg["num_candidates"]
    done = 0
    errors = []

    out_dir = os.path.join(CANDIDATES_DIR, "images")
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"🎨 場景圖候選生成: {cfg['story_name']}")
    if priority_filter:
        print(f"   篩選: priority={priority_filter}")
    print(f"   頁數: {len(pages)} × {cfg['num_candidates']} = {total} 張")
    print(f"{'=' * 60}\n")

    for page_cfg in pages:
        page_id = page_cfg["page"]
        scene = scene_data.get(page_id)
        if not scene:
            print(f"  ⚠️  {page_id} 不在場景資料中，跳過")
            continue

        # Build prompt
        base_prompt = scene["scene_prompt"]
        characters = scene["characters"]
        prompt_extra = page_cfg.get("prompt_extra", "")
        negative_extra = page_cfg.get("negative_extra", "")
        use_bright_style = page_cfg.get("style_override", False)

        full_prompt = _build_scene_prompt(
            base_prompt, characters, prompt_extra, negative_extra, use_bright_style
        )

        # Get reference images
        ref_images = _get_ref_images(characters, cfg["story_name"])

        print(f"  📍 {page_id} ({scene['title']}) — {page_cfg['priority']}")

        for ci in range(1, cfg["num_candidates"] + 1):
            out_path = os.path.join(out_dir, f"{page_id}_c{ci}.png")

            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                done += 1
                print(f"    ⏭️  {page_id}_c{ci} (已存在)")
                continue

            print(f"    🖌️  [{done+1}/{total}] {page_id}_c{ci}", end="", flush=True)

            try:
                _image_generate_with_retry(client, full_prompt, ref_images, out_path)
                print(" ✅")
                done += 1
            except Exception as e:
                print(f" ❌ {e}")
                errors.append(f"{page_id}_c{ci}: {e}")
                done += 1

            time.sleep(3)

    print(f"\n{'=' * 60}")
    print(f"📊 場景圖生成完成！成功: {done - len(errors)}, 失敗: {len(errors)}")
    if errors:
        for e in errors:
            print(f"   ❌ {e}")
    print(f"📁 輸出: {out_dir}")
    print(f"{'=' * 60}")


def _load_scene_data(story_name):
    """從 scene_gen.py 載入場景資料"""
    # Add scene_gen directory to path for import
    scene_gen_dir = os.path.join(PROJECT_ROOT, "2_sceneGen")
    sys.path.insert(0, scene_gen_dir)
    try:
        from scene_gen import STORIES
        pages = STORIES.get(story_name, [])
        return {p["page"]: p for p in pages}
    finally:
        sys.path.pop(0)


def _build_scene_prompt(base_prompt, characters, prompt_extra, negative_extra, use_bright_style):
    """組合完整 prompt"""
    parts = []

    # Extra prompt (fix-specific requirements)
    if prompt_extra:
        parts.append(prompt_extra)

    # Base scene description
    parts.append(base_prompt.strip())

    # Character lock features
    lock_section = "\n\nCHARACTER LOCK FEATURES (must match exactly):\n"
    for char_name in characters:
        if char_name in _CHARACTER_REGISTRY:
            char = _CHARACTER_REGISTRY[char_name]
            lock_section += f"- {char['en']}: {char['lock']}\n"
    parts.append(lock_section)

    # Height reminder
    if len(characters) >= 2:
        relevant = [r for r in _HEIGHT_RULES if r[0] in characters and r[1] in characters]
        if relevant:
            reminder = "\nHEIGHT RELATIONSHIPS:\n"
            for _, _, desc in relevant:
                reminder += f"- {desc}\n"
            parts.append(reminder)

    # Style
    parts.append(_CORE_STYLE_BRIGHT if use_bright_style else _CORE_STYLE)

    # Quality
    parts.append(_QUALITY_TAGS)

    # Negative prompt
    neg = _NEGATIVE_PROMPT
    if negative_extra:
        neg = neg.rstrip() + ", " + negative_extra
    parts.append(neg)

    return "\n".join(parts)


def _get_ref_images(characters, story_name):
    """取得角色參考圖路徑"""
    base_dir = os.path.join(PROJECT_ROOT, "2_sceneGen", "selected_characters", story_name)
    refs = []
    for char_name in characters:
        if char_name in _CHARACTER_REGISTRY:
            ref_path = os.path.join(base_dir, _CHARACTER_REGISTRY[char_name]["ref_file"])
            if os.path.exists(ref_path):
                refs.append(ref_path)

    # Height chart for multi-character scenes
    if len(characters) >= 2:
        height_chart = os.path.join(base_dir, "身高比例圖.png")
        if os.path.exists(height_chart):
            refs.append(height_chart)

    # API limit: max 5 reference images
    if len(refs) > 5:
        refs = refs[:4] + [refs[-1]]

    return refs


def _image_generate_with_retry(client, prompt, ref_images, output_path, max_retries=3):
    """OpenAI image generation with retry"""
    for attempt in range(max_retries):
        try:
            if ref_images:
                _generate_with_refs(client, prompt, ref_images, output_path)
            else:
                _generate_text_only(client, prompt, output_path)
            return
        except Exception as e:
            wait = 3 * (2 ** attempt)
            print(f"\n      ⚠️  Attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                print(f"      ⏳ Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def _generate_with_refs(client, prompt, ref_image_paths, output_path):
    """用 Responses API + 參考圖生成場景"""
    ref_instruction = (
        "IMPORTANT: Refer to the provided reference images for exact character appearances. "
        "Match the character designs, proportions, color palettes, and art style exactly as shown "
        "in the reference images. Pay special attention to the height comparison chart — "
        "maintain correct relative sizes between characters.\n\n"
        "CRITICAL: The image must contain ZERO text, ZERO letters, ZERO numbers, ZERO words anywhere. "
        "No signs, labels, speech bubbles, or writing of any kind.\n\n"
    )
    full_prompt = ref_instruction + prompt

    content = []
    for ref_path in ref_image_paths:
        with open(ref_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        content.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{b64}",
        })
    content.append({"type": "input_text", "text": full_prompt})

    response = client.responses.create(
        model="gpt-4o",
        input=[{"role": "user", "content": content}],
        tools=[{
            "type": "image_generation",
            "quality": "high",
            "size": "1536x1024",
            "output_format": "png",
            "background": "opaque",
        }],
    )

    for item in response.output:
        if item.type == "image_generation_call":
            image_data = base64.b64decode(item.result)
            with open(output_path, "wb") as f:
                f.write(image_data)
            return

    raise RuntimeError("No image generated in response")


def _generate_text_only(client, prompt, output_path):
    """Fallback: 純文字 prompt 生成"""
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        n=1,
        size="1536x1024",
        quality="high",
        output_format="b64_json",
    )
    image_data = base64.b64decode(response.data[0].b64_json)
    with open(output_path, "wb") as f:
        f.write(image_data)


# ══════════════════════════════════════════════════════════════
# APPLY SELECTIONS
# ══════════════════════════════════════════════════════════════

def apply_selections(audio_selections, image_selections):
    """將選定的候選版本複製到 final/ 目標路徑"""
    count = 0

    if audio_selections:
        print(f"\n🎙️  替換音檔:")
        for sel in audio_selections:
            # Parse "P03=c2" format
            page, candidate = sel.split("=")
            candidate_num = candidate.replace("c", "")

            # Find matching target
            matched = False
            for (version, p), target_rel in TTS_CONFIG["targets"].items():
                if p == page:
                    src_dir = os.path.join(CANDIDATES_DIR, "audio", version)
                    src_mp3 = os.path.join(src_dir, f"{page}_c{candidate_num}.mp3")
                    src_json = os.path.join(src_dir, f"{page}_c{candidate_num}.json")
                    dst_mp3 = os.path.join(SCRIPT_DIR, target_rel)
                    dst_json = dst_mp3.replace(".mp3", ".json")

                    if not os.path.exists(src_mp3):
                        print(f"   ❌ 找不到候選: {src_mp3}")
                        continue

                    # Backup
                    if os.path.exists(dst_mp3):
                        shutil.copy2(dst_mp3, dst_mp3 + ".bak")
                    if os.path.exists(dst_json):
                        shutil.copy2(dst_json, dst_json + ".bak")

                    # Copy
                    shutil.copy2(src_mp3, dst_mp3)
                    if os.path.exists(src_json):
                        shutil.copy2(src_json, dst_json)

                    print(f"   ✅ {version}/{page} ← {candidate} → {os.path.basename(dst_mp3)}")
                    count += 1
                    matched = True

            if not matched:
                print(f"   ⚠️  {page} 沒有對應的 target 設定")

    if image_selections:
        print(f"\n🎨  替換場景圖:")
        for sel in image_selections:
            page, candidate = sel.split("=")
            candidate_num = candidate.replace("c", "")
            src = os.path.join(CANDIDATES_DIR, "images", f"{page}_c{candidate_num}.png")

            if not os.path.exists(src):
                print(f"   ❌ 找不到候選: {src}")
                continue

            # Image targets need user to specify — just copy to a staging area
            staging = os.path.join(CANDIDATES_DIR, "selected_images")
            os.makedirs(staging, exist_ok=True)
            dst = os.path.join(staging, f"{page}.png")
            shutil.copy2(src, dst)
            print(f"   ✅ {page} ← {candidate} → selected_images/{page}.png")
            count += 1

        print(f"\n   📝 場景圖已複製到 candidates/selected_images/")
        print(f"      請自行製成 mp4 後放入 final/three-little-pigs/media/")

    print(f"\n📊 共替換 {count} 個檔案")
    if audio_selections:
        print(f"   💡 替換後請執行: python3 build.py")


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Piyo 繪本審校候選生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python3 generate_candidates.py tts
  python3 generate_candidates.py images --priority P0
  python3 generate_candidates.py apply --audio P03=c2 P07=c4 --images P01=c1
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # tts
    sub.add_parser("tts", help="生成 TTS 候選音檔")

    # images
    img_parser = sub.add_parser("images", help="生成場景圖候選")
    img_parser.add_argument("--priority", choices=["P0", "P1"], help="只跑指定優先級")

    # apply
    apply_parser = sub.add_parser("apply", help="替換選定的候選版本")
    apply_parser.add_argument("--audio", nargs="*", help="音檔選擇 (格式: P03=c2)")
    apply_parser.add_argument("--images", nargs="*", help="場景圖選擇 (格式: P01=c1)")

    args = parser.parse_args()

    if args.command == "tts":
        generate_tts_candidates()
    elif args.command == "images":
        generate_image_candidates(priority_filter=args.priority)
    elif args.command == "apply":
        if not args.audio and not args.images:
            print("請指定 --audio 或 --images 選擇")
            sys.exit(1)
        apply_selections(args.audio or [], args.images or [])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
