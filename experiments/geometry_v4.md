# Эксперимент: <experiment_name>

## 1. Кратко

Дата:

```text
2026-05-12
```

Git-ветка:

```text
geometry-v4
```

Базовый эксперимент:

```text
geometry_v3
```

Файл конфига:

```text
configs/geometry_v4.yaml
```

Файл сабмита:

```text
data/submissions/submission_geometry_v4.csv
```

Public Recall@160:

```text
```

Статус:

```text
[ ] черновик
[] сабмит валиден
[] отправлен на платформу
[ ] лучше baseline
[ ] хуже baseline
[] принят как новый baseline
[ ] отклонён
```

---

## 2. Что проверяем

Цель эксперимента:

```text
Проверить, улучшает ли качество рекомендаций расширенный kernel-reranking, который отдельно учитывает:
1. суммарную близость кандидата ко всей важной истории пользователя;
2. максимальную близость кандидата к одному важному item из истории;
3. суммарную близость кандидата к contact-истории;
4. максимальную близость кандидата к одному contact-item.
```

Гипотеза:

```text
geometry_v3 уже показал, что явная kernel-близость кандидата к истории пользователя сильно улучшает Recall@160.

В geometry_v4 проверяется более сильная гипотеза: будущий contact-item должен быть особенно похож не просто на общую историю пользователя, а на его наиболее важные и contact-события.

Если это верно, то contact-aware kernel terms должны повысить Recall@160 относительно geometry_v3.
```

Короткое описание изменения относительно baseline:

```text
geometry_v4 наследует candidate generation из geometry_v3, но расширяет kernel-reranking.

В geometry_v3 использовался один kernel_score по общей истории пользователя.

В geometry_v4 используются четыре kernel-компоненты:
- kernel_sum;
- kernel_max;
- contact_kernel_sum;
- contact_kernel_max.

Финальный score становится более таргетированным на будущие contact-события.
```

---

## 3. Что изменилось относительно baseline

Отметить только реальные изменения:

```text
[ ] добавлен новый источник кандидатов
[ ] выключен источник кандидатов
[ ] изменены веса источников
[x] изменены top_k параметры
[ ] изменены веса событий
[ ] изменён half_life_days
[x] изменена формула score
[ ] изменён fallback
[x] изменена постобработка/reranking
[ ] добавлены train-данные
[ ] добавлен ALS/collaborative source
[x] добавлен расширенный reranker
```

Подробно:

```text
1. Candidate generation наследуется из geometry_v3.
2. top_candidates_per_user_before_kernel увеличен с 500 до 1000.
3. top_history_atoms_per_user увеличен с 30 до 50.
4. Добавлен top_contact_atoms_per_user = 20.
5. Вместо одного kernel_weight используется несколько компонент:
   - kernel_sum_weight;
   - kernel_max_weight;
   - contact_kernel_sum_weight;
   - contact_kernel_max_weight.
6. Добавляется отдельная contact-only мера пользователя.
7. Финальное ранжирование использует extended final_score.
```

---

## 4. Основные параметры

Заполнить только те параметры, которые важны для эксперимента.

```yaml
experiment:
  name: geometry_v4
  base: geometry_v3

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
  top_candidates_per_user_before_kernel: 1000

kernel_reranking:
  enabled: true

  top_history_atoms_per_user: 50
  top_contact_atoms_per_user: 20

  base_score_weight: 1.00
  kernel_sum_weight: 0.20
  kernel_max_weight: 0.50
  contact_kernel_sum_weight: 0.30
  contact_kernel_max_weight: 0.80

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

geometry_v3:

final_score =
    1.00 * base_score
  + 0.35 * kernel_score
  + 0.03 * log1p(item_popularity)

geometry_v4:

final_score =
    1.00 * base_score
  + 0.20 * kernel_sum
  + 0.50 * kernel_max
  + 0.30 * contact_kernel_sum
  + 0.80 * contact_kernel_max
  + 0.03 * log1p(item_popularity)

где:

kernel_sum =
    суммарный kernel-потенциал кандидата относительно общей истории пользователя;

kernel_max =
    максимальная близость кандидата к одному важному item из общей истории;

contact_kernel_sum =
    суммарный kernel-потенциал кандидата относительно contact-истории;

contact_kernel_max =
    максимальная близость кандидата к одному contact-item.
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
data/interim/geometry_candidates_v4_base.parquet
data/interim/geometry_candidates_v4_prefiltered.parquet
data/interim/geometry_candidates_v4_kernel_scores.parquet
```

Новые файлы эксперимента:

```text
configs/geometry_v4.yaml
src/build_geometry_submission_v4.py
data/submissions/submission_geometry_v4.csv
experiments/geometry_v4.md
```

---

## 6. Команды запуска

```bash
POLARS_MAX_THREADS=<N> RAYON_NUM_THREADS=<N> python -u src/build_geometry_submission_v4.py
python src/validate_submission.py --submission data/submissions/submission_geometry_v4.csv

POLARS_MAX_THREADS=16 RAYON_NUM_THREADS=16 python -u src/build_geometry_submission_v4.py

geometry_v4 существенно тяжелее geometry_v3, потому что считает две kernel-компоненты:
1. по общей истории;
2. по contact-only истории.

Также увеличено число кандидатов перед kernel-reranking и число атомов истории.
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
geometry_v3
```

Baseline Recall@160:

```text
0.0151567706
```

Current Recall@160:

```text
0.0139647074
```

Разница:

```text
0.0139647074 - 0.0151567706 = -0.0011920632
```

Вывод:

```text
[] улучшение
[ ] ухудшение
[ ] примерно без изменений
```

---

## 9. Интерпретация

Что, вероятно, сработало:

```text
Скрипт успешно построил валидный contact-aware kernel submission на VM. Идея технически реализуема: были рассчитаны kernel_sum, kernel_max, contact_kernel_sum и contact_kernel_max.
```

Что, вероятно, не сработало:

```text
Текущая contact-aware формула ухудшила Public Recall@160 относительно geometry_v3. Вероятно, contact_kernel_max_weight = 0.80 слишком агрессивно усилил узкий сигнал contact-истории, а уменьшенный budget top_candidates=300, top_history_atoms=20, top_contact_atoms=10 ограничил качество reranking.
```

Почему мог получиться такой результат:

```text
geometry_v3 использует более сбалансированный kernel по общей истории пользователя. geometry_v4 дополнительно усиливает contact-only историю, но при текущих параметрах это могло сузить рекомендации и вытеснить полезных кандидатов из top-160.
```

---

## 10. Решение

```text
[ ] принять как новый baseline
[x] оставить как идею, но не baseline
[ ] отклонить
[ ] повторить с другими параметрами
```

Причина:

```text
geometry_v4 получил Public Recall@160 = 0.0139647074, что ниже geometry_v3 = 0.0151567706. Текущий лучший baseline остаётся geometry_v3.
```

Следующий шаг:

```text

```
