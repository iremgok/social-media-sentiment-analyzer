"""
Sözlük tabanlı analiz için kelime listeleri (Türkçe + İngilizce).

Bu liste kapsamlı olmak için değil; model indirmeden çalışan hafif bir
`lexicon` modu ve ağır modeller yüklenemediğinde güvenli bir yedek sağlamak
için tasarlanmıştır.
"""

POSITIVE_WORDS = frozenset({
    # English
    "amazing", "awesome", "best", "brilliant", "excellent", "exceeded", "fantastic", "fast",
    "glad", "good", "gorgeous", "great", "happy", "impressed", "impressive", "incredible",
    "love", "loved", "loving", "nice", "perfect", "phenomenal", "recommend", "recommended",
    "reliable", "smooth", "solid", "stunning", "superb", "unmatched", "useful", "wonderful",
    "worth", "satisfied", "beautiful", "enjoy", "enjoying",
    # Türkçe
    "harika", "mükemmel", "süper", "güzel", "iyi", "memnun", "memnunum", "tavsiye", "başarılı",
    "kaliteli", "hızlı", "sevdim", "bayıldım", "muhteşem", "efsane", "beğendim", "teşekkürler",
    "kusursuz", "şahane",
    # Emoji
    "😍", "🔥", "👍", "😊", "😀", "❤️", "❤", "🥰", "👏", "💯",
})

NEGATIVE_WORDS = frozenset({
    # English
    "awful", "bad", "broke", "broken", "buggy", "crash", "crashes", "disappointed",
    "disappointing", "expensive", "fail", "failed", "hate", "horrible", "lag", "laggy",
    "overheating", "overpriced", "poor", "refund", "ruined", "slow", "terrible", "useless",
    "worst", "annoying", "waste", "junk", "scam", "damaged",
    # Türkçe
    "berbat", "kötü", "rezalet", "kırıklığı", "donuyor", "çöküyor", "yavaş", "pahalı",
    "bozuk", "bozuldu", "hasarlı", "sorun", "sorunlu", "şikayet", "iade", "yazık", "beğenmedim",
    "nefret", "vasat", "çöp", "maalesef",
    # Emoji
    "😡", "👎", "🤦", "😠", "😞", "😢", "💩",
})

# İngilizcede olumsuzlayıcı kelimeden önce, Türkçede sonra gelir.
NEGATORS_BEFORE = frozenset({
    "not", "no", "never", "hardly", "dont", "don", "isn", "wasn", "doesn", "didn", "won", "hiç",
})
NEGATORS_AFTER = frozenset({"değil", "değilim", "değildi", "değiliz", "yok"})

STOPWORDS = frozenset({
    # English
    "the", "and", "for", "with", "this", "that", "have", "has", "had", "was", "were", "are",
    "but", "you", "your", "its", "it's", "they", "them", "from", "just", "been", "about",
    "what", "when", "will", "would", "could", "after", "into", "than", "then", "there",
    "very", "really", "honestly", "totally", "made", "make", "all", "any", "one", "can",
    "anyone", "yet", "got", "get", "today", "week", "days", "ever", "way", "still", "also",
    "https", "http", "www", "com",
    # Türkçe
    "bir", "bu", "şu", "ve", "ile", "için", "ama", "çok", "daha", "gibi", "kadar", "olarak",
    "ben", "sen", "biz", "siz", "onu", "bunu", "diye", "mi", "mı", "mu", "mü", "de", "da",
    "ki", "ne", "hem", "her", "tam", "sürekli", "hiç", "olan", "oldu", "gerçekten", "kesinlikle", "bugün", "aldım", "verdiğim",
})
