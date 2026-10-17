def simulate_project(slug: str, text: str) -> dict:
    normalized = text.strip()
    if slug == "aiora":
        lowered = normalized.lower()
        intent = "booking" if "book" in lowered else "storefront" if any(word in lowered for word in ("buy", "order", "product")) else "agent-menu"
        return {"simulation": True, "route": intent, "pipeline": ["gateway", "tenant-router", intent, "queued-reply"], "security": ["rate-limit", "HMAC webhook verification"]}
    if slug == "pocketpet":
        sensitive = any(word in normalized.lower() for word in ("pay", "password", "submit", "purchase"))
        return {"simulation": True, "task": normalized, "action": "approval_required" if sensitive else "preview_ready", "controls": ["pause", "cancel", "spend-limit", "secret-field-refusal"]}
    if slug == "glycanbench":
        return {"simulation": True, "input": normalized, "available_tools": ["format conversion", "descriptors", "fingerprints", "GLYSUM alignment", "MPNN prediction"], "notice": "Use live GlycanBench for scientific output."}
    raise KeyError(slug)
