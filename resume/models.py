from django.db import models


class Visitor(models.Model):
    """
    用來記錄「唯一訪客」的模型。

    - visitor_id：從前端送來，儲存在使用者瀏覽器（localStorage / cookie）中的隨機 ID
    - ip_address：使用者 IP（可能因為 Proxy/CDN 而不完全準確）
    - country / country_code：透過 IP 反查的國家名稱與國碼（例如 Taiwan / TW）
    - user_agent：瀏覽器 User-Agent 字串（可用來做粗略裝置統計）
    - visit_count：此訪客累計造訪次數（頁面載入次數）
    - first_seen / last_seen：第一次與最後一次造訪時間
    """

    visitor_id = models.CharField(max_length=64, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    country_code = models.CharField(max_length=10, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    visit_count = models.PositiveIntegerField(default=0)

    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Visitor"
        verbose_name_plural = "Visitors"

    def __str__(self) -> str:  # pragma: no cover - admin / debug 用
        return f"{self.visitor_id} ({self.country_code or 'Unknown'})"

