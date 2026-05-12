# Эксперимент: <experiment_name>

## 1. Кратко

Дата:

```text
2026-05-12
```

Git-ветка:

```text
geometry-v3
```

Базовый эксперимент:

```text
geometry_v2
```

Файл конфига:

```text
configs/geometry_v3.yaml
```

Файл сабмита:

```text
data/submissions/submission_geometry_v3.csv
```

Public Recall@160:

```text
0.0151567706
```

Статус:

```text
[ ] черновик
[x] сабмит валиден
[x] отправлен на платформу
[ ] лучше baseline
[ ] хуже baseline
[x] принят как новый baseline
[ ] отклонён
```

---

## 2. Что проверяем

Цель эксперимента:

```text
Проверить, улучшает ли качество рекомендаций явный kernel-based reranking кандидатов относительно пользовательской меры интереса.
```

Гипотеза:

```text
Если кандидат близок не только к агрегированной геометрической области пользователя,
но и к конкретным тяжёлым атомам его истории, то такой кандидат должен быть более
релевантен для будущего контакта. Поэтому добавление kernel score по top history atoms
должно повысить Recall@160 относительно geometry_v2.
```

Короткое описание изменения относительно baseline:

```text
geometry_v3 наследует candidate generation из geometry_v2, но добавляет явный
kernel-based reranking.

Сначала строится набор кандидатов как в geometry_v2:
- vertical_category_region
- vertical_category
- vertical_sid01
- region_sid01

Затем для каждого пользователя берутся top-N кандидатов по base_score и top-N
наиболее тяжёлых атомов его истории. Для пары candidate item — history item
считается дискретное ядро близости по совпадениям vertical/category/region/loc/sid.
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
[x] изменена формула score
[ ] изменён fallback
[x] изменена постобработка
[ ] добавлены train-данные
[ ] добавлен ALS/collaborative source
[x] добавлен reranker
```

Подробно:

```text
1. Candidate generation полностью унаследован из geometry_v2.
2. После построения кандидатов выполняется prefilter: top-500 кандидатов на пользователя по base_score.
3. Для каждого пользователя берутся top-30 наиболее тяжёлых атомов истории по event_weight.
4. Для каждой пары candidate item — history atom считается kernel similarity.
5. Kernel similarity учитывает совпадения vertical, category, region, loc и sid-prefix.
6. Финальный score стал суммой base_score, kernel_score и малого popularity prior.
7. Сабмит строится по final_score.
```

---

## 4. Основные параметры

Заполнить только те параметры, которые важны для эксперимента.

```yaml
experiment:
  name: geometry_v3
  base: geometry_v2

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

candidate_prefilter:
  top_candidates_per_user_before_kernel: 500

kernel_reranking:
  enabled: true
  top_history_atoms_per_user: 30
  base_score_weight: 1.00
  kernel_weight: 0.35

  weights:
    same_vertical: 0.50
    same_category: 1.00
    same_region: 0.80
    same_loc: 0.40
    same_sid0: 0.30
    same_sid01: 1.20
    same_sid012: 1.80
    same_sid0123: 2.40

  popularity:
    enabled: true
    weight: 0.03
    formula: log1p(item_popularity)

submission:
  top_final: 160
  global_fallback_top_k: 160
```

Формула score, если менялась:

```text
Да, изменилась.

geometry_v2:
score = base_score

geometry_v3:
final_score =
    1.00 * base_score
  + 0.35 * kernel_score
  + 0.03 * log1p(item_popularity)

kernel_score =
    sum over top history atoms j:
        atom_weight_j * K(candidate_item, history_item_j)

K(i,j) =
    0.50 * 1[same vertical]
  + 1.00 * 1[same category]
  + 0.80 * 1[same region]
  + 0.40 * 1[same loc]
  + 0.30 * 1[same sid0]
  + 1.20 * 1[same sid01]
  + 1.80 * 1[same sid012]
  + 2.40 * 1[same sid0123]
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
data/interim/item_popularity_eval_events.parquet
```

Пересчитанные intermediate-файлы:

```text
data/interim/geometry_candidates_v3_base.parquet
data/interim/geometry_candidates_v3_prefiltered.parquet
data/interim/geometry_candidates_v3_kernel_scores.parquet
```

Новые файлы эксперимента:

```text
configs/geometry_v3.yaml
src/build_geometry_submission_v3.py
data/submissions/submission_geometry_v3.csv
experiments/geometry_v3.md
```

---

## 6. Команды запуска

```bash
python src/build_geometry_submission_v3.py
python src/validate_submission.py --submission data/submissions/submission_geometry_v3.csv
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
geometry_v2
```

Baseline Recall@160:

```text
0.0110544427894445
```

Current Recall@160:

```text
0.0151567706
```

Разница:

```text
0.0151567706 - 0.0110544427894445 = 0.0041023278105555
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
Сработал явный kernel-based reranking. кандидат стал оцениваться не только по
агрегированной области интереса пользователя, но и по близости к конкретным
тяжёлым атомам его истории. Это усилило персонализацию и позволило лучше
различать кандидатов внутри одного и того же geometry-key.
```

Что, вероятно, не сработало:

```text
Явного ухудшения не наблюдается. Однако kernel reranking существенно увеличил
разброс финальных item-ов: в финальном сабмите 1,458,339 уникальных item_id.
Это оказалось полезным на public leaderboard, но требует дальнейшей проверки
на local validation.
```

Почему мог получиться такой результат:

```text
В geometry_v2 кандидат получал score в основном от массы агрегированной области,
например (region_id_y, sid_0_y, sid_1_y). В geometry_v3 кандидат дополнительно
сравнивается с конкретными объявлениями из истории пользователя.

пользователь это атомарная мера на пространстве объявлений, а релевантность
кандидата — ядровой потенциал этой точки относительно пользовательской меры.
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
geometry_v3 повысил Public Recall@160 с 0.0110544427894445 до 0.0151567706
относительно geometry_v2. Это прирост примерно на 37.11% относительно v2.
Также geometry_v3 существенно лучше geometry_v1.
```

Следующий шаг:

```text

```
