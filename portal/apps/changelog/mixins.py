from django.db import models


class ChangeloggableMixin(models.Model):
  """Значения полей сразу после инициализации объекта"""
  _original_values = None

  class Meta:
    abstract = True

  def __init__(self, *args, **kwargs):
    super(ChangeloggableMixin, self).__init__(*args, **kwargs)

    # Нельзя getattr/hasattr по deferred-полям (.only/.defer) —
    # это вызывает refresh_from_db → снова __init__ → RecursionError.
    try:
      deferred = set(self.get_deferred_fields())
    except Exception:
      deferred = set()

    original = {}
    for field in self._meta.fields:
      if field.name in ('added', 'changed'):
        continue
      # Для FK сравниваем/храним id (attname), не связанный объект
      attr = field.attname
      if field.name in deferred or attr in deferred:
        continue
      original[field.name] = getattr(self, attr)
    self._original_values = original

  def get_changed_fields(self):
    """Получаем измененные данные."""
    result = {}
    if not self._original_values:
      return result
    try:
      deferred = set(self.get_deferred_fields())
    except Exception:
      deferred = set()
    for name, value in self._original_values.items():
      field = self._meta.get_field(name)
      attr = field.attname
      if name in deferred or attr in deferred:
        continue
      current = getattr(self, attr)
      if value != current:
        result[name] = current
    return result
