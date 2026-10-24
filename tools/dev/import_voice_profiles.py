# -*- coding: utf-8 -*-
"""把 4 条声线档案写进 Demon 的 config.json（dist 与 build/bin 各一份）。"""

import io, json, os

DIST = r"E:\dshwork\Demon\dist\Demon"
BUILD = r"E:\dshwork\Demon\build\bin"

# 参考音频复制到 dist\voices，用绝对路径（api_v2 的相对路径是按它自己的 cwd 解析）
refs = os.path.join(DIST, "voices")
xiaod = os.path.join(refs, "xiaod.wav")
demon = os.path.join(refs, "demon.wav")

profiles = [
    {
        "id": "小d-柔软", "name": "小d · 柔软",
        "gptWeights": "GPT_weights_v2Pro/nightmare-glly-JP-e15.ckpt",
        "sovitsWeights": "SoVITS_weights_v2Pro/nightmare-glly-JP_e8_s400.pth",
        "refAudio": xiaod,
        "promptText": "私を強くして……どうするつもりですか？",
        "promptLang": "ja",
    },
    {
        "id": "demon-小恶魔", "name": "demon · 小恶魔",
        "gptWeights": "GPT_weights_v2Pro/nightmare-JP-e15.ckpt",
        "sovitsWeights": "SoVITS_weights_v2Pro/nightmare-JP_e8_s368.pth",
        "refAudio": demon,
        "promptText": "この人たちが敵ね。へーえ、面白そうじゃない。",
        "promptLang": "ja",
    },
    {
        "id": "小d-柔软-泛化", "name": "小d · 柔软(泛化)",
        "gptWeights": "GPT_weights_v2Pro/nightmare-glly-JP-e10.ckpt",
        "sovitsWeights": "SoVITS_weights_v2Pro/nightmare-glly-JP_e8_s400.pth",
        "refAudio": xiaod,
        "promptText": "私を強くして……どうするつもりですか？",
        "promptLang": "ja",
    },
    {
        "id": "demon-小恶魔-2", "name": "demon · 小恶魔（泛化）",
        "gptWeights": "GPT_weights_v2Pro/nightmare-JP-e10.ckpt",
        "sovitsWeights": "SoVITS_weights_v2Pro/nightmare-JP_e8_s368.pth",
        "refAudio": demon,
        "promptText": "この人たちが敵ね。へーえ、面白そうじゃない。",
        "promptLang": "ja",
    },
]

for target in (DIST, BUILD):
    path = os.path.join(target, "config.json")
    cfg = {}
    if os.path.exists(path):
        cfg = json.load(io.open(path, encoding="utf-8"))
    cfg["voiceProfiles"] = profiles
    cfg.setdefault("voice", {})
    cfg["voice"]["profile"] = "小d-柔软"
    io.open(path, "w", encoding="utf-8", newline="").write(
        json.dumps(cfg, ensure_ascii=False, indent=2))
    print("[OK]", path)
