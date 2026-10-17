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
    "projects": ["What was his exact contribution?", "Show the architecture decisions", "Which technologies were used?"],
    "skills": ["Which skills are strongest?", "Show projects using these skills", "What is his AI stack?"],
    "experience": ["What does he work on now?", "Show his career timeline", "What production systems has he built?"],
    "research": ["Explain the GlycanBench validation", "Show his publications", "What are the model limitations?"],
    "education": ["What did he study?", "Show certifications", "How does biology shape his engineering?"],
    "contact": ["Is he available for roles?", "Show his résumé", "How can I contact him?"],
    "profile": ["Show his strongest projects", "What is his current role?", "What makes his background different?"],
    "general": ["Show his strongest projects", "What are his main skills?", "What is his current role?"],
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
        "followups": FOLLOWUPS.get(prepared.decision.topic, FOLLOWUPS["general"]),
        "project": project,
    }
