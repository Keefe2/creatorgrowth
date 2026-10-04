"""Built-in content generation engine.

Produces platform-shaped copy from topic + tone without any external API,
so the app works offline. Swap `generate()` with an LLM call later —
the interface stays the same.
"""
import random

from .schemas import AIGenerateIn, AIGenerateOut

_HOOKS_UR = [
    "سنو، ایک بات بتاؤں؟ 👀",
    "یہ پڑھ کر تمہارا دماغ گھوم جائے گا 🤯",
    "سچ بتاؤں؟ تم تیار نہیں ہو اس کے لیے 🔥",
    "رکو رکو… یہ ضرور پڑھو ⚡",
]

_HOOKS_EN = [
    "Stop scrolling. Read this. 👀",
    "This will rewire how you think 🤯",
    "Nobody talks about this 🔥",
    "Wait… you need to see this ⚡",
]

_CTAS_UR = [
    "کمنٹ میں بتاؤ تمہارا کیا خیال ہے؟ 💬",
    "شیئر کرو اسے جسے یہ جاننا چاہیے 📤",
    "فالو کرو، روز ایسا کانٹینٹ ملے گا ✨",
]

_CTAS_EN = [
    "Drop your take in the comments 💬",
    "Share this with someone who needs it 📤",
    "Follow for daily drops like this ✨",
]

_HASHTAGS = {
    "facebook": ["#viral", "#trending", "#foryou"],
    "x": ["#viral", "#trending"],
    "youtube": ["#shorts", "#viral"],
    "instagram": ["#reels", "#viral", "#explore"],
}


def _pick(rng: random.Random, seq: list[str]) -> str:
    return seq[rng.randint(0, len(seq) - 1)]


def generate(payload: AIGenerateIn, seed: int | None = None) -> AIGenerateOut:
    rng = random.Random(seed if seed is not None else payload.topic)
    ur = payload.language == "ur"

    if payload.tone == "bold":
        angle = "بے باک انداز میں" if ur else "told straight, no filter"
    elif payload.tone == "playful":
        angle = "مزاحیہ انداز میں" if ur else "with a playful twist"
    elif payload.tone == "professional":
        angle = "پروفیشنل انداز میں" if ur else "in a sharp professional tone"
    else:
        angle = "وائرل اسٹائل میں" if ur else "in full viral mode"

    hook = _pick(rng, _HOOKS_UR if ur else _HOOKS_EN)
    cta = _pick(rng, _CTAS_UR if ur else _CTAS_EN)

    if ur:
        title = f"{payload.topic} — {angle}"
        body = (
            f"{hook}\n\n"
            f"آج کی بات: {payload.topic}\n"
            f"اسے {angle} سمجھو، کیونکہ یہ وہ سچ ہے جو اکثر لوگ نظر انداز کر دیتے ہیں۔\n\n"
            f"سوچو… اگر تم نے آج ہی اس پر عمل شروع کر دیا تو ایک مہینے بعد تم کہاں ہو گے؟\n\n"
            f"{cta}"
        )
    else:
        title = f"{payload.topic} — {angle}"
        body = (
            f"{hook}\n\n"
            f"Today's truth: {payload.topic}\n"
            f"Here it is {angle}, because this is the part most people skip.\n\n"
            f"Think… if you started acting on this today, where would you be in a month?\n\n"
            f"{cta}"
        )

    hashtags = list(_HASHTAGS.get(payload.platform, ["#viral"]))
    return AIGenerateOut(title=title, body=body, hashtags=hashtags)
