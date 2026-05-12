# Эксперимент: <experiment_name>

## 1. Кратко

Дата:

```text
2026-05-12
```

Git-ветка:

```text
geometry-v2
```

Базовый эксперимент:

```text
geometry_v1
```

Файл конфига:

```text
configs/geometry_v2.yaml
```

Файл сабмита:

```text
data/submissions/submission_geometry_v2.csv
```

Public Recall@160:

```text
<score>
```

Статус:

```text
[ ] черновик
[x] сабмит валиден
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
Проверить, улучшает ли качество рекомендаций добавление регионально-семантического источника кандидатов region_sid01.
```

Гипотеза:

```text
Если будущие контактные объявления пользователя часто находятся в том же регионе и имеют похожий semantic id prefix, что и его прошлые взаимодействия, то источник region_sid01 должен повысить Recall@160 относительно geometry_v1.
```

Короткое описание изменения относительно baseline:

```text
В geometry_v2 к трём источникам geometry_v1 добавлен четвёртый источник кандидатов:

region_sid01:
  key = (region_id_y, sid_0_y, sid_1_y)

Этот источник достаёт популярные объявления из тех же регионально-семантических областей, где у пользователя накоплена масса интереса.
```

---

## 3. Что изменилось относительно baseline

Отметить только реальные изменения:

```text
[x] добавлен новый источник кандидатов
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
1. Добавлен источник region_sid01.
2. Используется user profile: data/interim/user_profile_region_sid01.parquet.
3. Используется candidate index: data/interim/candidate_index_region_sid01.parquet.
4. Ключ источника: (region_id_y, sid_0_y, sid_1_y).
5. source_weight = 0.70.
6. top_profile_keys = 5.
7. top_items_per_key = 25.
8. Остальные параметры geometry_v1 не менялись.
```

---

## 4. Основные параметры

Заполнить только те параметры, которые важны для эксперимента.

```yaml
experiment:
  name: geometry_v2
  base: geometry_v1

user_measure:
  half_life_days: 7.0

event_weights:
  contact_eids: 8.0
  eid_7: 1.0
  eid_10: 2.0
  other: 3.0

candidate_sources:
  vertical_category_region:
    enabled: true
    source_weight: 1.00
    top_profile_keys: 5
    top_items_per_key: 50

  vertical_category:
    enabled: true
    source_weight: 0.60
    top_profile_keys: 5
    top_items_per_key: 60

  vertical_sid01:
    enabled: true
    source_weight: 0.80
    top_profile_keys: 5
    top_items_per_key: 30

  region_sid01:
    enabled: true
    source_weight: 0.70
    top_profile_keys: 5
    top_items_per_key: 25

  vertical_sid012:
    enabled: false
    source_weight: 0.50
    top_profile_keys: 5
    top_items_per_key: 20

submission:
  top_final: 160
  global_fallback_top_k: 160
```

Формула score, если менялась:

```text
Не менялась относительно geometry_v1.

score = mass * source_weight * (1 + log1p(item_popularity)) / sqrt(rank_in_key)
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
data/interim/item_geometry_eval_verticals.parquet
data/interim/eval_events_geometry.parquet
data/interim/user_interest_measure.parquet
data/interim/user_profile_vertical_category_region.parquet
data/interim/user_profile_vertical_category.parquet
data/interim/user_profile_vertical_sid01.parquet
data/interim/user_profile_region_sid01.parquet
data/interim/candidate_index_vertical_category_region.parquet
data/interim/candidate_index_vertical_category.parquet
data/interim/candidate_index_vertical_sid01.parquet
data/interim/candidate_index_region_sid01.parquet
data/interim/candidate_index_global_popular.parquet
```

Пересчитанные intermediate-файлы:

```text
data/interim/geometry_candidates_v2.parquet
```

Новые файлы эксперимента:

```text
configs/geometry_v2.yaml
src/build_geometry_submission_v2.py
data/submissions/submission_geometry_v2.csv
experiments/geometry_v2.md
```

---

## 6. Команды запуска

```bash
python src/build_geometry_submission_v2.py
python src/validate_submission.py --submission data/submissions/submission_geometry_v2.csv
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
geometry_v2 использует уже построенные user profiles и candidate indices.
Новые raw/interim базовые таблицы не пересчитывались.
```

---

## 7. Валидация сабмита

Вставить результат `validate_submission.py`.

```text
n_rows = 15105280
n_users = 94408
n_items = 776334

min_recs = 160  
mean_recs = 160  
max_recs = 160  

n_missing_users = 0
n_unknown_users = 0
n_duplicate_pairs = 0
n_users_too_many = 0
n_unknown_items = 0
```

Сабмит валиден?

```text
[x] да
[ ] нет
```

Если нет, что нужно исправить:

```text

```

---

## 8. Результат на платформе

Baseline:

```text
geometry_v1
```

Baseline Recall@160:

```text
0.0090026262
```

Current Recall@160:

```text
0.0110544427894445
```

Разница:

```text
0.0110544427894445 - 0.0090026262 = 0.0020518165894445
```

Вывод:

```text
[x] улучшение
[ ] ухудшение
[ ] примерно без изменений
```

---

## 9. Интерпретация

Что, вероятно, сработало:

```text
Добавление region_sid01 улучшило Recall@160. Это означает, что для части пользователей важна не только категориальная или semantic-близость внутри vertical, но и совместная регионально-семантическая близость: тот же region_id_y + тот же sid_0_y/sid_1_y.
```

Что, вероятно, не сработало:

```text
Явного ухудшения не наблюдается. Источник region_sid01 не вытеснил полезные кандидаты из v1, а добавил дополнительные релевантные item-ы.
```

Почему мог получиться такой результат:

```text
Для Avito география является сильным фактором релевантности. При этом sid_0_y/sid_1_y задаёт семантическую близость текста объявления. Комбинация region_id_y и sid-prefix лучше локализует область интереса пользователя, чем один только vertical_sid01.
```

---

## 10. Решение

```text
[x] принять как новый baseline
[ ] оставить как идею, но не baseline
[ ] отклонить
[ ] повторить с другими параметрами
```

Причина:

```text
geometry_v2 дал прирост Recall@160 с 0.0090026262 до 0.0110544427894445, то есть примерно на 22.79% относительно geometry_v1.
```

Следующий шаг:

```text

```
