import uuid

from django.db import models
from documents.models import DocRLK


class ClientJourneyLink(models.Model):
    """Персональная ссылка клиента на статус покупки по рабочему листу."""
    rlk = models.ForeignKey(
        DocRLK,
        on_delete=models.CASCADE,
        related_name='journey_links',
        verbose_name='Рабочий лист',
    )
    token = models.UUIDField('Токен доступа', default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField('Активна', default=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    last_opened_at = models.DateTimeField('Последний вход', null=True, blank=True)
    opens_count = models.PositiveIntegerField('Открытий', default=0)

    class Meta:
        db_table = 'clientJourneyLink'
        verbose_name = 'Ссылка клиента'
        verbose_name_plural = 'Ссылки клиентов'
        ordering = ['-created_at']

    def __str__(self):
        return f'RLK {self.rlk_id} — {self.token}'
