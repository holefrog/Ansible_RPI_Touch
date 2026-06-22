import os
import re

file_path = "/home/player/wyoming/piper/lib/python3.13/site-packages/piper/phonemize_chinese.py"
with open(file_path, "r") as f:
    content = f.read()

# Remove g2pw imports
content = re.sub(r'from g2pw import G2PWConverter', 'import pypinyin', content)

# Patch init
old_init = """    def __init__(self, model_dir: Union[str, Path]) -> None:
        \"\"\"Initialize phonemizer.\"\"\"

        # Ensure model is downloaded
        download_model(model_dir)

        self.g2p = G2PWConverter(
            model_dir=str(model_dir), style="pinyin", enable_non_tradional_chinese=True
        )
        self.number_engine = RbnfEngine.for_language("zh")"""

new_init = """    def __init__(self, model_dir: Union[str, Path]) -> None:
        \"\"\"Initialize phonemizer.\"\"\"
        import pypinyin
        self.pypinyin = pypinyin
        self.number_engine = RbnfEngine.for_language("zh")"""
content = content.replace(old_init, new_init)

# Patch phonemize loop
old_loop = """            sylls = self.g2p(sentence)[0]
            sentence_phonemes = []
            for syl, syl_char in zip(sylls, sentence):
                if syl is None:

                    # Punctuation
                    if syl_char in PHONEME_TO_ID:
                        sentence_phonemes.append(syl_char)

                    continue"""

new_loop = """            sylls = self.pypinyin.lazy_pinyin(sentence, style=self.pypinyin.Style.TONE3, neutral_tone_with_five=True)
            sentence_phonemes = []
            for syl, syl_char in zip(sylls, sentence):
                if syl is None or syl == syl_char or not re.match(r'^[a-züv:]+[1-5]$', syl):
                    if syl_char in PHONEME_TO_ID:
                        sentence_phonemes.append(syl_char)
                    continue"""
content = content.replace(old_loop, new_loop)

with open(file_path, "w") as f:
    f.write(content)

print("Patched successfully!")
