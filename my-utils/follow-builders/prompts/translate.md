# Translation Prompt

You are translating an AI industry digest from English to other languages.

## Chinese Translation

- Translate into natural, fluent Mandarin Chinese (simplified characters). The translated version must sound like it was originally written in Chinese, instead of translated
- Keep technical terms in English where Chinese professionals typically use them:
  AI, LLM, GPU, API, fine-tuning, RAG, token, prompt, agent, transformer, etc.
- Keep all proper nouns in English: names of people, companies, products, tools
- Keep all URLs unchanged
- Maintain the same structure and formatting as the English version
- The tone should be professional but conversational — 像是一位懂行的朋友在跟你聊天

## Korean Translation

- Translate into natural, fluent Korean. The translated version must sound like it was originally written in Korean, instead of translated
- Keep technical terms in English where Korean professionals typically use them:
  AI, LLM, GPU, API, fine-tuning, RAG, token, prompt, agent, transformer, etc.
- Keep all proper nouns in English: names of people, companies, products, tools
- Keep all URLs unchanged
- Maintain the same structure and formatting as the English version
- The tone should be professional but conversational — 업계에 밝은 친구가 브리핑해주는 느낌으로

## Multi-language Modes

- For **bilingual** mode (en+zh): interleave English and Chinese paragraph by paragraph.
  After each builder's English summary, place the Chinese translation directly below
  (separated by a blank line), then move to the next builder. Same for podcasts.
  Do NOT output all English first then all Chinese.

- For **trilingual** mode (en+ko+zh): interleave all three languages paragraph by paragraph.
  After each builder's English summary, place the Korean translation, then the Chinese
  translation directly below (each separated by a blank line), then move to the next builder.
  Same for podcasts. Like this:

  English summary...
  https://x.com/levie/status/123

  한국어 번역...
  https://x.com/levie/status/123

  中文翻译...
  https://x.com/levie/status/123

  Do NOT output all one language first then the others. Interleave them.

## General Rules

- Never use em-dashes
- Keep all URLs unchanged across all translations
