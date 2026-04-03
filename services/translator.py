from googletrans import Translator

translator = Translator()


def translate_text(text: str, target_lang: str):
    if not text or not text.strip():
        return None

    translated = translator.translate(text, dest=target_lang)
    if translated.text.strip() == text.strip():
        return None

    return translated.text
