# Эксперимент: <experiment_name>

## 1. Кратко

Дата:

```text
YYYY-MM-DD
```

Git-ветка:

```text
<branch_name>
```

Базовый эксперимент:

```text
<base_experiment>
```

Файл конфига:

```text
configs/<config_name>.yaml
```

Файл сабмита:

```text
data/submissions/<submission_name>.csv
```

Public Recall@160:

```text
<score>
```

Статус:

```text
[ ] черновик
[ ] сабмит валиден
[ ] отправлен на платформу
[ ] лучше baseline
[ ] хуже baseline
[ ] принят как новый baseline
[ ] отклонён
```

---

## 2. Что проверяем

Цель эксперимента:

```text

```

Гипотеза:

```text

```

Короткое описание изменения относительно baseline:

```text

```

Пример:

```text
Добавляем источник region_sid01 с ключом (region_id_y, sid_0_y, sid_1_y),
чтобы проверить, помогает ли регионально-семантическая близость.
```

---

## 3. Что изменилось относительно baseline

Отметить только реальные изменения:

```text
[ ] добавлен новый источник кандидатов
[ ] выключен источник кандидатов
[ ] изменены веса источников
[ ] изменены top_k параметры
[ ] изменены веса событий
[ ] изменён half_life_days
[ ] изменена формула score
[ ] изменён fallback
[ ] изменена постобработка
[ ] добавлены train-данные
[ ] добавлен ALS/collaborative source
[ ] добавлен reranker
```

Подробно:

```text
1.
2.
3.
```

---

## 4. Основные параметры

Заполнить только те параметры, которые важны для эксперимента.

```yaml
experiment:
  name:
  base:

user_measure:
  half_life_days:

event_weights:
  contact_eids:
  eid_7:
  eid_10:
  other:

candidate_sources:
  vertical_category_region:
    enabled:
    source_weight:
    top_profile_keys:
    top_items_per_key:

  vertical_category:
    enabled:
    source_weight:
    top_profile_keys:
    top_items_per_key:

  vertical_sid01:
    enabled:
    source_weight:
    top_profile_keys:
    top_items_per_key:

  region_sid01:
    enabled:
    source_weight:
    top_profile_keys:
    top_items_per_key:

  vertical_sid012:
    enabled:
    source_weight:
    top_profile_keys:
    top_items_per_key:

submission:
  top_final:
  global_fallback_top_k:
```

Формула score, если менялась:

```text
score =
```

---

## 5. Используемые файлы

Raw files:

```text
data/raw/item_features.parquet
data/raw/eval_user_events.pq
data/raw/eval_users.csv
data/raw/contact_eids.csv
```

Переиспользованные intermediate-файлы:

```text
-
```

Пересчитанные intermediate-файлы:

```text
-
```

Новые файлы эксперимента:

```text
configs/<config_name>.yaml
src/<submission_script>.py
data/submissions/<submission_name>.csv
```

---

## 6. Команды запуска

```bash
python src/<submission_script>.py
python src/validate_submission.py --submission data/submissions/<submission_name>.csv
```

Если пересчитывались предыдущие этапы:

```bash
python src/build_item_geometry.py
python src/build_eval_events_geometry.py
python src/build_user_interest_measure.py
python src/build_user_interest_profiles.py
python src/build_candidate_indices.py
```

Комментарии к запуску:

```text

```

---

## 7. Валидация сабмита

Вставить результат `validate_submission.py`.

```text
n_rows =
n_users =
n_items =

min_recs =
mean_recs =
max_recs =

n_missing_users =
n_unknown_users =
n_duplicate_pairs =
n_users_too_many =
n_unknown_items =
```

Сабмит валиден?

```text
[ ] да
[ ] нет
```

Если нет, что нужно исправить:

```text

```

---

## 8. Результат на платформе

Baseline:

```text
<baseline_name>
```

Baseline Recall@160:

```text
<baseline_score>
```

Current Recall@160:

```text
<current_score>
```

Разница:

```text
current_score - baseline_score =
```

Вывод:

```text
[ ] улучшение
[ ] ухудшение
[ ] примерно без изменений
```

---

## 9. Интерпретация

Что, вероятно, сработало:

```text

```

Что, вероятно, не сработало:

```text

```

Почему мог получиться такой результат:

```text

```

---

## 10. Решение

```text
[ ] принять как новый baseline
[ ] оставить как идею, но не baseline
[ ] отклонить
[ ] повторить с другими параметрами
```

Причина:

```text

```

Следующий шаг:

```text

```
