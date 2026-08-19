import re
import emoji

class TextPreprocessor:
    """
    Gelen yorumları temizler. Linkleri, boşlukları ve etiketleri kaldırır.
    Duygu farklılığı olmaması için emojileri metne çevirir.
    """

    def __init__(self, convert_emojis_to_text: bool = True):
        self.convert_emojis_to_text = convert_emojis_to_text

    def clean(self, text:str) -> str:

        if not text or not isinstance(text, str):
            return ""

        # 1. URL'leri kaldır (http, https, www)
        text = re.sub(r"https?://\S+|www\.\S+", "", text)

        # 2. Kullanıcı etiketlerini kaldır
        text = re.sub(r"@\w+", "", text)

        # 3. Hashtag işaretini kaldır ama kelimeyi koru (#iPhone -> iPhone)
        text = re.sub(r"#(\w+)", r"\1", text)

        # 4. Emojileri metne çevir (Örn: 😊 -> :smiling_face_with_smiling_eyes:)
        if self.convert_emojis_to_text:
            text = emoji.demojize(text, language="en")
            # :smiling_face: formatındaki iki noktaları ve alt çizgileri temizle
            text = text.replace(":", " ").replace("_", " ")

        # 5. Özel karakterleri temizle (Harfler, rakamlar ve temel noktalama kalsın)
        text = re.sub(r"[^\w\s.,!?'-]", "", text)

        # 6. Çoklu boşlukları ve satır sonlarını tek boşluğa indir
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def clean_batch(self, texts: list[str]) -> list[str]:
        """Birden fazla metni liste halinde temizler (boyut hizalamasını korur)."""
        return [self.clean(t) for t in texts]




