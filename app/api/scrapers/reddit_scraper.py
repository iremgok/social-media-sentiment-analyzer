from typing import Dict, List, Optional
import praw
from app.api.scrapers.base import BaseScraper


class RedditScraper(BaseScraper):
    """
    Reddit üzerinden belirli bir anahtar kelimeye veya
    subreddit'e ait gönderi ve yorumları toplayan sınıf.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: str = "SentimentAnalyzerApp/1.0",
    ):
        self.is_configured = bool(client_id and client_secret)

        if self.is_configured:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
            )
            print("Reddit API bağlantısı başarıyla kuruldu.")
        else:
            self.reddit = None
            print("Uyarı: Reddit API anahtarları girilmedi. Mock (demo) modunda çalışılıyor.")

    def fetch_comments(self, query: str, limit: int = 50) -> List[Dict[str, str]]:
        """
        Belirtilen anahtar kelimeye göre Reddit araması yapar ve yorumları toplar.
        API anahtarı yoksa test amaçlı sentetik yorumlar üretir.
        """
        if not self.is_configured:
            return self._generate_mock_comments(query, limit)

        comments_data = []
        try:
            # Genel arama yap
            search_results = self.reddit.subreddit("all").search(query, sort="relevance", limit=10)

            for submission in search_results:
                submission.comments.replace_more(limit=0)  # Derin yorum ağacını atla
                for comment in submission.comments.list():
                    if len(comments_data) >= limit:
                        break

                    # Çok kısa veya silinmiş yorumları filtrele
                    if comment.body and comment.body != "[deleted]" and len(comment.body.split()) >= 3:
                        comments_data.append({
                            "id": comment.id,
                            "text": comment.body,
                            "platform": "reddit",
                            "created_utc": str(comment.created_utc),
                        })

                if len(comments_data) >= limit:
                    break

            return comments_data

        except Exception as e:
            print(f"Reddit veri çekme hatası: {str(e)}")
            return self._generate_mock_comments(query, limit)

    def _generate_mock_comments(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        API anahtarı tanımlanmadığında geliştirme ve test için sentetik veri sağlar.
        """
        mock_templates = [
            f"I have been using {query} for a week now and the battery performance is phenomenal! Highly recommended.",
            f"Totally disappointed with {query}. The latest update made it lag constantly and crash.",
            f"Got my {query} delivered today. The design is sleek, but the customer service was quite slow.",
            f"Honestly, {query} is way overpriced for what it offers. You can find better alternatives.",
            f"The display quality on {query} is unmatched. Loving the 120Hz smooth scrolling!",
            f"Just an average experience with {query}. It does the job, nothing extraordinary.",
            f"Overheating issues on {query} are terrible. Can barely hold it while gaming.",
            f"Best purchase I made this year. {query} exceeded all my expectations!",
        ]

        results = []
        for i in range(min(limit, len(mock_templates))):
            results.append({
                "id": f"mock_{i+1}",
                "text": mock_templates[i],
                "platform": "reddit_mock",
                "created_utc": "1700000000",
            })
        return results


# --- TEST BLOĞU (Girintisiz, en solda) ---
if __name__ == "__main__":
    # API key olmadan mock modda test ediyoruz:
    scraper = RedditScraper()
    data = scraper.fetch_comments(query="iPhone 15", limit=5)

    print(f"\n--- Çekilen Yorumlar (Toplam: {len(data)}) ---")
    for item in data:
        print(f"[{item['id']}] {item['text']}")