# Local vision route V0

Jarjar now distinguishes structured environment questions from true visual
semantics.

Routing examples:

- "Combien d'écrans j'ai ?" -> Qwen text + live metadata.
- "Quelle caméra est active ?" -> Qwen text + live metadata.
- "Qu'est-ce que tu vois sur la caméra ?" -> local vision provider.
- "Lis ce qu'il y a sur mon écran." -> local vision provider with a fresh
  virtual-desktop screenshot.
- vision provider unavailable -> Qwen text + live metadata fallback.

The default contract targets an OpenAI-compatible local endpoint:

- URL: `http://127.0.0.1:8081/v1/chat/completions`
- model label: `Qwen2.5-VL-3B-Instruct`

Both are configurable with `JARJAR_VISION_URL` and `JARJAR_VISION_MODEL`.

This commit defines the integration seam; it does not claim that a compatible
Qwen-VL model is already installed or running on the target machine.

Vision output is descriptive text only. It cannot execute actions.
