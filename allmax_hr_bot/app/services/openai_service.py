from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import anthropic
from app.config import settings

logger = logging.getLogger(__name__)


def _safe_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


class OpenAIService:
    def __init__(self) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    async def json_chat(self, system: str, user: str, fallback: dict, temperature: float = 0.2) -> dict:
        if not self.client:
            return fallback

        for attempt in range(3):
            try:
                res = await self.client.messages.create(
                    model=settings.anthropic_model,
                    max_tokens=4096,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                content = res.content[0].text or "{}"
                return _safe_json(content)
            except Exception as exc:
                logger.warning("Anthropic JSON attempt %s failed: %s", attempt + 1, exc)
                await asyncio.sleep(0.8 * (attempt + 1))
        return fallback

    async def generate_interview_questions(self, position: str, regulation_text: str, candidate: dict, count: int = 10) -> list[dict]:
        count = max(1, min(30, int(count or 10)))
        fallback = {"questions": _fallback_interview_questions(position, count)}
        system = (
            "Siz ALLMAX HR intervyu assistentisiz. Siz faqat tanlangan lavozim reglamenti va nomzod anketasi asosida savollar tuzasiz. "
            "Savollar ishga mos, adolatli, aniq va lavozimga tegishli bo'lishi kerak. Diskriminatsion yoki shaxsiy hayotga noo'rin aralashuvchi savollar bermang. "
            "Faqat JSON qaytaring."
        )
        distribution = "Kamida vaziyatli, reglament/bilim, intizom/mas'uliyat va motivatsion savollar bo'lsin; 10 savol bo'lsa 4/3/2/1 ta taqsimotdan foydalaning."
        user = f"Lavozim: {position}\nNomzod: {json.dumps(candidate, ensure_ascii=False)}\nReglament:\n{regulation_text[:25000]}\n\n{count} savol tuzing. {distribution} JSON schema: {{\"questions\":[{{\"number\":1,\"type\":\"situation|knowledge|discipline|motivation\",\"question\":\"...\",\"what_it_checks\":\"...\"}}]}}"
        data = await self.json_chat(system, user, fallback)
        qs = data.get("questions") or fallback["questions"]
        if len(qs) < count:
            qs = fallback["questions"]
        return qs[:count]

    async def evaluate_interview(self, candidate: dict, answers: list[dict], regulation_text: str) -> dict:
        fallback_score = _heuristic_score(answers)
        fallback = _fallback_evaluation(fallback_score)
        system = (
            "Siz ALLMAX HR baholash assistentisiz. Faqat ishga mos mezonlar bo'yicha baholang: tajriba, reglamentni tushunish, mas'uliyat, intizom, mijoz bilan muloqot, halollik, jamoada ishlash, stressga chidamlilik, o'rganishga tayyorlik va javoblar sifati. "
            "Jins, millat, din, tashqi ko'rinish, siyosiy qarash yoki boshqa shaxsiy belgilar asosida xulosa qilmang. AI bahosi final qaror emas, admin uchun tavsiya. Faqat JSON qaytaring."
        )
        user = f"Nomzod: {json.dumps(candidate, ensure_ascii=False)}\nReglament: {regulation_text[:15000]}\nSavol-javoblar: {json.dumps(answers, ensure_ascii=False)}\nJSON schema: {{\"score\":0,\"grade\":\"low|medium|excellent\",\"summary\":\"...\",\"strengths\":[\"...\"],\"risks\":[\"...\"],\"admin_recommendation\":\"reject|review|invite_interview\",\"polite_candidate_message\":\"...\",\"reasoning_for_admin\":\"...\"}}"
        data = await self.json_chat(system, user, fallback)
        score = int(data.get("score") or fallback_score)
        data["score"] = max(0, min(100, score))
        data["grade"] = data.get("grade") or ("low" if score < 60 else "medium" if score < 80 else "excellent")
        return data

    async def classify_followup(self, text: str) -> str:
        fallback = {"class": "unclear"}
        system = "Intervyu natijasi haqidagi qisqa matnni accepted, rejected, waiting yoki unclear klasslaridan biriga ajrating. Faqat JSON."
        data = await self.json_chat(system, text, fallback)
        value = str(data.get("class") or data.get("status") or "unclear").lower()
        return value if value in {"accepted", "rejected", "waiting", "unclear"} else "unclear"

    async def generate_lesson_test(self, lesson: dict, regulation_text: str, count: int = 10) -> list[dict]:
        fallback = _fallback_test(count, lesson.get("title") or "Dars")
        system = "Siz ALLMAX stajirovka test tuzuvchi assistantsiz. Faqat o'tilgan dars va reglament asosida test tuzing. Faqat JSON qaytaring."
        user = f"Dars: {json.dumps(lesson, ensure_ascii=False)}\nReglament: {regulation_text[:15000]}\n{count} ta savol tuzing. Har bir savolda A,B,C,D variant va bitta correct_answer. JSON: {{\"questions\":[{{\"question\":\"...\",\"options\":{{\"A\":\"...\",\"B\":\"...\",\"C\":\"...\",\"D\":\"...\"}},\"correct_answer\":\"A\",\"explanation\":\"...\"}}]}}"
        data = await self.json_chat(system, user, {"questions": fallback})
        qs = data.get("questions") or fallback
        return _normalize_questions(qs, count)

    async def generate_final_test(self, department: str, lessons: list[dict], regulation_text: str, count: int = 30) -> list[dict]:
        count = max(1, min(100, int(count or 30)))
        fallback = _fallback_test(count, department)
        system = "Siz ALLMAX yakuniy stajirovka testi tuzuvchi assistantsiz. Savollar reglament va o'tilgan darslar asosida bo'lsin. Faqat JSON."
        user = f"Bo'lim: {department}\nDarslar: {json.dumps(lessons, ensure_ascii=False)[:20000]}\nReglament: {regulation_text[:25000]}\n{count} ta test savol tuzing. JSON: {{\"questions\":[{{\"question\":\"...\",\"options\":{{\"A\":\"...\",\"B\":\"...\",\"C\":\"...\",\"D\":\"...\"}},\"correct_answer\":\"A\",\"explanation\":\"...\"}}]}}"
        data = await self.json_chat(system, user, {"questions": fallback})
        return _normalize_questions(data.get("questions") or fallback, count)

    async def evaluate_final(self, employee: dict, lesson_stats: list[dict], final_test: dict) -> dict:
        percent = float(final_test.get("percentage") or 0)
        level = "low" if percent < 60 else "medium" if percent < 80 else "excellent"
        fallback = {
            "final_score_percent": percent,
            "level": level,
            "strong_topics": [],
            "weak_topics": [],
            "responsibility_comment": "Natijalar testlar asosida baholandi.",
            "admin_recommendation": "ready_for_work" if percent >= 80 else "supervise_more" if percent >= 60 else "continue_training",
            "message_to_admin": _final_admin_message(percent),
        }
        system = "Siz ALLMAX stajirovka yakuniy baholash assistentisiz. Test natijalari asosida admin uchun adolatli xulosa bering. Faqat JSON."
        user = f"Xodim: {json.dumps(employee, ensure_ascii=False)}\nDars testlari: {json.dumps(lesson_stats, ensure_ascii=False)}\nYakuniy test: {json.dumps(final_test, ensure_ascii=False)}\nJSON schema: {{\"final_score_percent\":0,\"level\":\"low|medium|excellent\",\"strong_topics\":[\"...\"],\"weak_topics\":[\"...\"],\"responsibility_comment\":\"...\",\"admin_recommendation\":\"continue_training|supervise_more|ready_for_work\",\"message_to_admin\":\"...\"}}"
        data = await self.json_chat(system, user, fallback)
        data.setdefault("message_to_admin", fallback["message_to_admin"])
        return data


def _normalize_questions(qs: list[dict], count: int) -> list[dict]:
    out: list[dict] = []
    for i, q in enumerate(qs[:count], 1):
        opts = q.get("options") or {}
        norm_opts = {k: str(opts.get(k) or opts.get(k.lower()) or f"Variant {k}") for k in ["A", "B", "C", "D"]}
        correct = str(q.get("correct_answer") or "A").upper()
        if correct not in norm_opts:
            correct = "A"
        out.append({"question": str(q.get("question") or f"Savol {i}"), "options": norm_opts, "correct_answer": correct, "explanation": str(q.get("explanation") or "Reglament asosida.")})
    while len(out) < count:
        out.extend(_fallback_test(count - len(out), "Mavzu"))
    return out[:count]


def _fallback_interview_questions(position: str, count: int = 10) -> list[dict]:
    templates = [
        ("situation", f"{position} lavozimida mijoz norozilik bildirsa, vaziyatni qanday hal qilasiz?", "mijoz bilan muloqot"),
        ("situation", "Ish jarayonida xato aniqlasangiz, kimga va qanday xabar berasiz?", "halollik va mas'uliyat"),
        ("situation", "Bir vaqtning o'zida bir nechta vazifa berilsa, ustuvorlikni qanday belgilaysiz?", "tartib va stressga chidamlilik"),
        ("situation", "Jamoada kelishmovchilik chiqsa, qanday yo'l tutasiz?", "jamoada ishlash"),
        ("knowledge", f"{position} bo'yicha asosiy vazifalarni qanday tushunasiz?", "lavozimni tushunish"),
        ("knowledge", "Reglamentga rioya qilish nega muhim?", "intizom"),
        ("knowledge", "Kunlik hisobot yoki nazorat ishlarida nimalarga e'tibor berasiz?", "hisobot madaniyati"),
        ("discipline", "Ishga kech qolish ehtimoli tug'ilsa, oldindan qanday harakat qilasiz?", "intizom"),
        ("discipline", "Sizga berilgan vazifa tugallanmasa, qanday javobgarlik olasiz?", "mas'uliyat"),
        ("motivation", "Nega aynan ALLMAX jamoasida ishlamoqchisiz?", "motivatsiya"),
    ]
    out = [{"number": i, "type": t, "question": q, "what_it_checks": w} for i, (t, q, w) in enumerate(templates, 1)]
    while len(out) < count:
        i = len(out) + 1
        out.append({"number": i, "type": "knowledge", "question": f"{position} lavozimida reglamentga rioya qilishga oid {i}-amaliy misolni tushuntiring.", "what_it_checks": "reglamentni tushunish"})
    return out[:count]


def _heuristic_score(answers: list[dict]) -> int:
    text = " ".join(str(a.get("answer") or "") for a in answers).lower()
    score = 55
    positives = ["mijoz", "mas'ul", "mas'ul", "hisobot", "reglament", "jamoa", "halol", "o'rgan", "organ", "intizom", "vaqt"]
    score += min(35, sum(4 for p in positives if p in text))
    if len(text) > 900:
        score += 10
    elif len(text) < 250:
        score -= 10
    return max(0, min(100, score))


def _fallback_evaluation(score: int) -> dict:
    grade = "low" if score < 60 else "medium" if score < 80 else "excellent"
    return {
        "score": score,
        "grade": grade,
        "summary": "Nomzod javoblari avtomatik fallback algoritm asosida baholandi.",
        "strengths": ["Javob berishga tayyorlik"],
        "risks": [] if score >= 60 else ["Reglament va vazifalarni chuqurroq tushuntirish kerak"],
        "admin_recommendation": "reject" if score < 60 else "review" if score < 80 else "invite_interview",
        "polite_candidate_message": "Arizangiz uchun rahmat.",
        "reasoning_for_admin": "Fallback baholash ishladi.",
    }


def _fallback_test(count: int, title: str) -> list[dict]:
    qs = []
    base = [
        ("Reglamentga rioya qilishning asosiy maqsadi nima?", "Ish sifatini va tartibni ta'minlash"),
        ("Mijoz bilan muloqotda eng muhim jihat qaysi?", "Hurmat va aniq javob"),
        ("Xato aniqlansa nima qilish kerak?", "Mas'ul shaxsga xabar berish"),
        ("Kunlik vazifa tugagach nima qilinadi?", "Hisobot topshiriladi"),
    ]
    for i in range(count):
        q, correct_text = base[i % len(base)]
        qs.append({
            "question": f"{title}: {q}",
            "options": {"A": correct_text, "B": "E'tibor bermaslik", "C": "Keyinga qoldirish", "D": "Faqat og'zaki aytish"},
            "correct_answer": "A",
            "explanation": "To'g'ri javob reglament va mas'uliyat talablariga mos.",
        })
    return qs


def _final_admin_message(percent: float) -> str:
    if percent >= 80:
        return "✅ Tavsiya: xodim reglamentlarni yaxshi o'zlashtirgan. Ish jarayonida mustaqil ishlashga tayyorligi yuqori ko'rinmoqda."
    if percent >= 60:
        return "⚠️ Tavsiya: xodim asosiy mavzularni o'zlashtirgan, lekin ayrim joylarda qo'shimcha nazorat va qayta o'rgatish kerak."
    return "❌ Ogohlantirish: xodim materiallarni yetarli o'zlashtirmagan. Mas'uliyat va e'tibor darajasini qayta tekshirish, qo'shimcha o'qitish va nazorat zarur."


openai_service = OpenAIService()
