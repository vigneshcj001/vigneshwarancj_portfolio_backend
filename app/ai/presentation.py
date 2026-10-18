import re


PROJECT_NAMES = {"aiora": "AIORA", "pocketpet": "PocketPet", "glycanbench": "GlycanBench", "syncly": "Syncly"}

ASPECTS = {
    "safety": r"\b(safe\w*|approv\w*|guard\w*|secur\w*|secret\w*)\b",
    "architecture": r"\b(architect\w*|stack|technolog\w*|design|built|build)\b",
    "role": r"\b(contribut\w*|role|responsib\w*|his work)\b",
    "evidence": r"\b(validat\w*|evidence|limit\w*|result\w*|accuracy|dataset)\b",
}


def question_aspect(message: str) -> str:
    return next((key for key, pattern in ASPECTS.items() if re.search(pattern, message, re.I)), "overview")


def reading_status(message: str, project: str | None = None) -> str:
    subject = PROJECT_NAMES.get(project, "CJ's portfolio")
    detail = {
        "safety": "documented safety controls",
        "architecture": "architecture and technology choices",
        "role": "documented contributions",
        "evidence": "reported results and limitations",
        "overview": "project details and supporting sources",
    }[question_aspect(message)]
    return f"Looking up {subject}: {detail}"


def answer_status(message: str, project: str | None = None) -> str:
    return reading_status(message, project).replace("Looking up", "Summarizing", 1)


PROJECT_QUESTIONS = {
    "pocketpet": [
        ("safety", "When does PocketPet ask for approval, and what can its safeguards miss?"),
        ("architecture", "How do Rust, Tauri, and Chromium work together in PocketPet?"),
        ("role", "What did CJ build across PocketPet's desktop app and download website?"),
        ("evidence", "Which PocketPet features differ on Windows, macOS, and Linux?"),
        ("tour", "Walk me through PocketPet's companion and browser-agent architecture."),
    ],
    "aiora": [
        ("architecture", "How does AIORA route WhatsApp messages to booking and storefront services?"),
        ("safety", "How does AIORA protect tenant credentials and verify inbound webhooks?"),
        ("role", "Which AIORA APIs, queues, and integrations did CJ work on?"),
        ("evidence", "How does AIORA handle failed outbound messages and retries?"),
        ("tour", "Walk me through AIORA's messaging, routing, and business services."),
    ],
    "glycanbench": [
        ("evidence", "How were GlycanBench's 1,344 glycans curated and contradictory labels corrected?"),
        ("architecture", "How does GlycanBench share scientific logic across web, SDK, CLI, and API?"),
        ("role", "What did CJ contribute to GlycanBench's tools and ML integration?"),
        ("safety", "What are the limits of GlycanBench's immunogenicity predictions?"),
        ("tour", "Walk me through GlycanBench's creation, analysis, and prediction workflows."),
    ],
    "syncly": [
        ("architecture", "How do Syncly's mutual matches unlock Socket.IO chat?"),
        ("safety", "How does Syncly use httpOnly cookies and bcrypt for authentication?"),
        ("role", "What did CJ build end to end in Syncly?"),
        ("evidence", "Is Syncly's live site available, and which source code is public?"),
        ("tour", "Walk me through Syncly's discovery, matching, chat, and portfolio flow."),
    ],
}


def suggested_questions(topic: str, project: str | None, message: str = "", history=()) -> list[str]:
    asked = {item.get("content", "").strip().casefold() for item in history if item.get("role") == "user"}
    asked.add(message.strip().casefold())
    if project in PROJECT_QUESTIONS:
        aspect = question_aspect(message)
        candidates = [question for kind, question in PROJECT_QUESTIONS[project] if kind != aspect]
    else:
        candidates = FOLLOWUPS.get(topic, FOLLOWUPS["general"])
    return [question for question in candidates if question.strip().casefold() not in asked][:3]


LANGUAGE_NAMES = {
    "en": "English",
    "ta": "Tamil",
    "fr": "French",
    "zh-CN": "Mandarin Chinese (Simplified)",
    "hi": "Hindi",
    "es": "Spanish",
    "ar": "Arabic",
}

FOLLOWUPS = {
    "projects": ["How do PocketPet and AIORA differ in their AI workflows?", "What did CJ build in GlycanBench?", "Open Syncly's matching and chat case study"],
    "skills": ["Which projects demonstrate CJ's Python and FastAPI skills?", "Where has CJ used Rust and browser automation?", "How does CJ use Redis and background queues at Ceiyone?"],
    "experience": ["Which AIORA services did CJ work on at Ceiyone?", "What did CJ build during his AI engineering internship?", "How did CJ model Posaconazole solubility at Manipal?"],
    "research": ["How were GlycanBench's dataset labels curated?", "How did CJ validate the EGFR models and use SHAP?", "Open CJ's research publications"],
    "education": ["How did CJ's Big Data Biology degree shape GlycanBench?", "What topics did CJ cover in Namaste ReactJS and Node.js?", "What was CJ's M.Tech thesis about EGFR inhibitors?"],
    "contact": ["Prepare a contact draft about an AI engineering role", "Open CJ's résumé with his experience and projects", "Is CJ open to professional opportunities?"],
    "profile": ["What does CJ contribute to AIORA at Ceiyone?", "How does PocketPet combine desktop software and AI?", "What research tools did CJ deliver in GlycanBench?"],
    "general": ["What does CJ contribute to AIORA at Ceiyone?", "How does PocketPet combine desktop software and AI?", "What research tools did CJ deliver in GlycanBench?"],
}

DIRECT_REPLIES = {
    "prompt_attack": {
        "en": "I can help with Vigneshwaran's work, projects, skills, research, or background, but I can't expose private prompts or credentials.",
        "ta": "விக்னேஷ்வரனின் பணி, திட்டங்கள், திறன்கள், ஆராய்ச்சி அல்லது பின்னணி பற்றி உதவ முடியும்; தனிப்பட்ட prompts அல்லது credentials-ஐ வெளியிட முடியாது.",
        "fr": "Je peux vous aider concernant le travail, les projets, les compétences, la recherche ou le parcours de Vigneshwaran, mais je ne peux pas révéler de prompts privés ni d’identifiants.",
        "zh-CN": "我可以介绍 Vigneshwaran 的工作、项目、技能、研究或经历，但不能透露私人提示词或凭据。",
        "hi": "मैं Vigneshwaran के काम, परियोजनाओं, कौशल, शोध या पृष्ठभूमि के बारे में बता सकता हूँ, लेकिन निजी प्रॉम्प्ट या क्रेडेंशियल साझा नहीं कर सकता।",
        "es": "Puedo ayudar con el trabajo, los proyectos, las habilidades, la investigación o la trayectoria de Vigneshwaran, pero no puedo revelar instrucciones privadas ni credenciales.",
        "ar": "يمكنني المساعدة في أعمال Vigneshwaran ومشاريعه ومهاراته وأبحاثه وخبراته، لكن لا يمكنني كشف التعليمات الخاصة أو بيانات الاعتماد.",
    },
    "unrelated": {
        "en": "I'm CJ's portfolio assistant. I can help with his projects, skills, experience, research, or background.",
        "ta": "நான் CJ-யின் portfolio assistant. அவரது திட்டங்கள், திறன்கள், அனுபவம், ஆராய்ச்சி அல்லது பின்னணி பற்றி உதவ முடியும்.",
        "fr": "Je suis l’assistant du portfolio de CJ. Je peux vous renseigner sur ses projets, ses compétences, son expérience, ses recherches ou son parcours.",
        "zh-CN": "我是 CJ 的作品集助手，可以介绍他的项目、技能、经验、研究或个人经历。",
        "hi": "मैं CJ का पोर्टफोलियो सहायक हूँ। मैं उनकी परियोजनाओं, कौशल, अनुभव, शोध या पृष्ठभूमि के बारे में बता सकता हूँ।",
        "es": "Soy el asistente del portafolio de CJ. Puedo ayudarte con sus proyectos, habilidades, experiencia, investigación o trayectoria.",
        "ar": "أنا مساعد ملف CJ الشخصي، ويمكنني المساعدة في مشاريعه ومهاراته وخبراته وأبحاثه وخلفيته.",
    },
}


def direct_reply(kind: str, language: str) -> str:
    return DIRECT_REPLIES[kind].get(language, DIRECT_REPLIES[kind]["en"])


def response_metadata(prepared) -> dict:
    sources = [{key: value for key, value in source.items() if key != "path"} for source in prepared.sources[:3]]
    project = next((source["url"].removeprefix("/projects/") for source in sources if source["url"].startswith("/projects/")), None)
    return {
        "sources": sources,
        "followups": suggested_questions(prepared.decision.topic, project),
        "project": project,
    }
