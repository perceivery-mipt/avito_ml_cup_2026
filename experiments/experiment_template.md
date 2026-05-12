# Эксперимент: <название_эксперимента>

## 1. Метаданные

Дата:

```text
YYYY-MM-DD
```

Автор:

```text
<имя>
```

Git-ветка:

```text
<branch_name>
```

Базовый эксперимент:

```text
geometry_v1
```

Файл конфигурации:

```text
configs/<config_name>.yaml
```

Файл сабмита:

```text
data/submissions/<submission_name>.csv
```

Public score:

```text
Recall@160 =
```

Статус эксперимента:

```text
[ ] черновик
[ ] отправлен на платформу
[ ] принят как новый baseline
[ ] отклонён
[ ] требует повторного запуска
```

---

## 2. Краткое описание эксперимента

В 2–5 предложениях описать, что именно проверяется.

Пример:

```text
В этом эксперименте проверяется, улучшает ли качество рекомендаций добавление
источника кандидатов region_sid01, то есть поиска объявлений в той же географии
и с тем же семантическим sid-префиксом. Базой сравнения является geometry_v1.
Ожидается, что региональная семантическая близость особенно полезна для локальных
категорий объявлений.
```

---

## 3. Цель

Что хотим проверить?

```text

```

Пример:

```text
Проверить, даёт ли добавление геометрического ключа
(region_id_y, sid_0_y, sid_1_y) прирост Recall@160 относительно geometry_v1.
```

---

## 4. Гипотеза

Сформулировать проверяемую гипотезу строго и конкретно.

```text

```

Пример:

```text
Если будущие контакты пользователя чаще происходят с объявлениями, которые
одновременно близки по смыслу текста и находятся в том же регионе, что и его
прошлые взаимодействия, то добавление источника region_sid01 должно повысить
Recall@160.
```

---

## 5. Математическая постановка

### 5.1. Пространство объявлений

Каждое объявление рассматривается как точка дискретного стратифицированного пространства:

```text
x_i = (
    vertical_id,
    category_ext_y,
    region_id_y,
    loc_id_y,
    sid_0_y,
    sid_1_y,
    sid_2_y,
    sid_3_y
)
```

Описание координат:

```text
vertical_id      — крупная вертикаль каталога;
category_ext_y   — категория внутри вертикали;
region_id_y      — регион;
loc_id_y         — более детальная локация;
sid_0_y..sid_3_y — иерархический semantic id объявления.
```

Используемые вертикали:

```text
{0, 2, 3, 4, 5, 7}
```

Исключённые вертикали:

```text
{1, 6}
```

Причина исключения:

```text
Вертикали 1 и 6 не входят в официальный eval и имеют очень малый объём
по сравнению с остальными вертикалями.
```

### 5.2. Пользователь как мера интереса

Пользователь не представляется одной фиксированной точкой. Его история задаёт атомарную меру на пространстве объявлений:

```text
mu_u = sum_{(u,i,e,t)} w(e,t) * delta_{x_i}
```

Где:

```text
u             — пользователь;
i             — объявление;
e             — тип события;
t             — время события;
x_i           — точка объявления в item-пространстве;
delta_{x_i}   — атомарная мера в точке x_i;
w(e,t)        — масса атома, зависящая от типа события и давности.
```

Интерпретация:

```text
Каждое действие пользователя кладёт массу интереса в точку соответствующего
объявления. Чем действие сильнее и свежее, тем больше масса.
```

### 5.3. Веса событий

Формула веса события:

```text
w(e,t) = alpha_e * exp(-lambda * age_days)
```

Где:

```text
alpha_e  — базовая важность типа события;
age_days — возраст события в днях относительно cutoff/max_timestamp;
lambda   — параметр временного затухания.
```

Связь lambda с half-life:

```text
lambda = log(2) / half_life_days
```

Интерпретация half-life:

```text
half_life_days — число дней, за которое вклад события уменьшается в 2 раза.
```

### 5.4. Геометрические проекции меры

Полную атомарную меру хранить и использовать напрямую дорого, поэтому строятся её проекции на геометрические области:

```text
(user_id, vertical_id, category_ext_y, region_id_y)
(user_id, vertical_id, category_ext_y)
(user_id, vertical_id, sid_0_y, sid_1_y)
(user_id, vertical_id, sid_0_y, sid_1_y, sid_2_y)
(user_id, region_id_y, sid_0_y, sid_1_y)
```

Смысл:

```text
Каждая такая строка показывает, сколько массы интереса пользователя находится
в соответствующей области item-пространства.
```

### 5.5. Кандидатная генерация

Для каждой геометрической области заранее строится индекс популярных item-ов:

```text
geometry_key -> top item_id внутри этой области
```

Примеры ключей:

```text
(vertical_id, category_ext_y, region_id_y)
(vertical_id, category_ext_y)
(vertical_id, sid_0_y, sid_1_y)
(region_id_y, sid_0_y, sid_1_y)
(vertical_id, sid_0_y, sid_1_y, sid_2_y)
```

### 5.6. Scoring

Практическая формула score:

```text
score = mass * source_weight * (1 + log1p(item_popularity)) / sqrt(rank_in_key)
```

Где:

```text
mass              — масса пользовательского интереса в данной области;
source_weight     — вес источника кандидатов;
item_popularity   — популярность item-а в истории eval-пользователей;
rank_in_key       — место item-а внутри геометрического индекса.
```

### 5.7. Постобработка

```text
1. Склеить кандидатов из разных источников.
2. Агрегировать дубли user_id-item_id.
3. Удалить уже виденные пользователем item_id.
4. Добавить global popular fallback.
5. Отсортировать кандидатов по score.
6. Взять top-160 item_id на каждого user_id.
```

---

## 6. Что меняется относительно базового эксперимента

Базовый эксперимент:

```text
geometry_v1
```

Изменения:

```text
[ ] изменены веса событий
[ ] изменён half-life
[ ] добавлен новый источник кандидатов
[ ] удалён источник кандидатов
[ ] изменён source_weight
[ ] изменён top_profile_keys
[ ] изменён top_items_per_key
[ ] изменён fallback
[ ] изменена формула score
[ ] изменена постобработка
[ ] добавлены train-данные
[ ] добавлен ALS/collaborative source
[ ] добавлен LightGBM/CatBoost reranker
```

Подробное описание изменений:

```text
1.
2.
3.
```

Что НЕ менялось:

```text
1.
2.
3.
```

---

## 7. Используемые данные

### 7.1. Raw files

```text
data/raw/item_features.parquet
data/raw/eval_user_events.pq
data/raw/eval_users.csv
data/raw/contact_eids.csv
```

Дополнительные файлы:

```text
data/raw/prepare_local_eval.py
data/raw/popular.py
data/raw/submission_popular.csv
```

Train-файлы использовались?

```text
[ ] нет
[ ] да
```

Если да, перечислить:

```text
data/raw/train_000-019.zip
data/raw/train_020-039.zip
...
```

### 7.2. Intermediate files

```text
data/interim/item_geometry_eval_verticals.parquet
data/interim/eval_events_geometry.parquet
data/interim/user_interest_measure.parquet
data/interim/user_profile_vertical_category_region.parquet
data/interim/user_profile_vertical_category.parquet
data/interim/user_profile_vertical_sid01.parquet
data/interim/user_profile_vertical_sid012.parquet
data/interim/user_profile_region_sid01.parquet
data/interim/item_popularity_eval_events.parquet
data/interim/candidate_index_vertical_category_region.parquet
data/interim/candidate_index_vertical_category.parquet
data/interim/candidate_index_vertical_sid01.parquet
data/interim/candidate_index_region_sid01.parquet
data/interim/candidate_index_global_popular.parquet
```

Какие intermediate-файлы были пересчитаны:

```text

```

Какие intermediate-файлы были переиспользованы:

```text

```

---

## 8. Конфигурация эксперимента

```yaml
experiment:
  name:
  base:
  description:

item_space:
  eval_verticals:
    - 0
    - 2
    - 3
    - 4
    - 5
    - 7

user_measure:
  half_life_days:

event_weights:
  contact_eids:
  eid_7:
  eid_10:
  other:

user_profiles:
  vertical_category_region:
    top_k_per_user:

  vertical_category:
    top_k_per_user:

  vertical_sid01:
    top_k_per_user:

  vertical_sid012:
    top_k_per_user:

  region_sid01:
    top_k_per_user:

candidate_indices:
  top_k_per_key:
  global_top_k:

submission:
  top_final:
  global_fallback_top_k:

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

scoring:
  formula:

postprocessing:
  aggregate_duplicate_user_item_scores:
  remove_seen_items:
  fallback:
  sort_by:
```

---

## 9. Источники кандидатов

Заполнить только источники, реально использованные в эксперименте.

### 9.1. Source: vertical_category_region

```text
enabled =
profile file =
index file =
key = (vertical_id, category_ext_y, region_id_y)
source_weight =
top_profile_keys =
top_items_per_key =
роль источника =
```

Ожидаемый эффект:

```text

```

### 9.2. Source: vertical_category

```text
enabled =
profile file =
index file =
key = (vertical_id, category_ext_y)
source_weight =
top_profile_keys =
top_items_per_key =
роль источника =
```

Ожидаемый эффект:

```text

```

### 9.3. Source: vertical_sid01

```text
enabled =
profile file =
index file =
key = (vertical_id, sid_0_y, sid_1_y)
source_weight =
top_profile_keys =
top_items_per_key =
роль источника =
```

Ожидаемый эффект:

```text

```

### 9.4. Source: region_sid01

```text
enabled =
profile file =
index file =
key = (region_id_y, sid_0_y, sid_1_y)
source_weight =
top_profile_keys =
top_items_per_key =
роль источника =
```

Ожидаемый эффект:

```text

```

### 9.5. Source: vertical_sid012

```text
enabled =
profile file =
index file =
key = (vertical_id, sid_0_y, sid_1_y, sid_2_y)
source_weight =
top_profile_keys =
top_items_per_key =
роль источника =
```

Ожидаемый эффект:

```text

```

### 9.6. Source: global popular fallback

```text
enabled =
global_top_k =
fallback_top_k =
роль источника =
```

Ожидаемый эффект:

```text

```

---

## 10. Команды запуска

Команды, которые были выполнены для получения результата.

```bash
python src/build_item_geometry.py
python src/build_eval_events_geometry.py
python src/build_user_interest_measure.py
python src/build_user_interest_profiles.py
python src/build_candidate_indices.py
python src/build_geometry_submission_<version>.py
python src/validate_submission.py
```

Если запуск был частичным:

```text
Пересчитано:
-

Переиспользовано:
-
```

Время выполнения:

```text
build_item_geometry:
build_eval_events_geometry:
build_user_interest_measure:
build_user_interest_profiles:
build_candidate_indices:
build_submission:
validate_submission:
```

Проблемы при запуске:

```text

```

---

## 11. Валидация сабмита

Вставить вывод команды:

```bash
python src/validate_submission.py
```

Результаты:

```text
n_rows =
n_users =
n_unique_items =

min_recs_per_user =
mean_recs_per_user =
max_recs_per_user =

missing_users =
unknown_users =
duplicate_user_item_pairs =
users_with_more_than_160_recs =
unknown_items =
```

Ожидаемое валидное состояние:

```text
missing_users = 0
unknown_users = 0
duplicate_user_item_pairs = 0
users_with_more_than_160_recs = 0
unknown_items = 0
max_recs_per_user <= 160
```

Сабмит валиден?

```text
[ ] да
[ ] нет
```

Если нет, почему:

```text

```

---

## 12. Local validation

Использовалась локальная валидация?

```text
[ ] нет
[ ] да
```

Если да:

```text
Recall@160 local =
```

Описание локального split:

```text
train period:
gap:
target period:
users:
items:
anti-join rule:
```

Файл локальных таргетов:

```text

```

Файл локального сабмита:

```text

```

Комментарий:

```text

```

Если локальная валидация не использовалась:

```text
Причина:
```

---

## 13. Public leaderboard

Файл сабмита:

```text
data/submissions/<submission_name>.csv
```

Дата и время отправки:

```text
YYYY-MM-DD HH:MM
```

Public Recall@160:

```text

```

Место на leaderboard, если известно:

```text

```

Комментарий платформы / ошибки загрузки:

```text

```

---

## 14. Сравнение с baseline

Baseline:

```text
geometry_v1
```

Baseline Recall@160:

```text
0.0090026262
```

Текущий Recall@160:

```text

```

Абсолютное изменение:

```text
current_score - baseline_score =
```

Относительное изменение:

```text
(current_score - baseline_score) / baseline_score =
```

Итог:

```text
[ ] лучше baseline
[ ] хуже baseline
[ ] примерно без изменений
```

---

## 15. Диагностика кандидатов

Заполнить, если посчитано.

Общее число кандидатов до агрегации:

```text

```

Число кандидатов после агрегации:

```text

```

Среднее число кандидатов на пользователя до fallback:

```text

```

Доля fallback-кандидатов в финальном top-160:

```text

```

Распределение источников в финальном top-160:

```text
vertical_category_region:
vertical_category:
vertical_sid01:
region_sid01:
vertical_sid012:
global_popular:
```

Overlap источников:

```text

```

Популярность финальных item-ов:

```text
min:
mean:
median:
max:
```

---

## 16. Диагностика геометрии

Распределение финальных рекомендаций по vertical_id:

```text
vertical_id = 0:
vertical_id = 2:
vertical_id = 3:
vertical_id = 4:
vertical_id = 5:
vertical_id = 7:
```

Распределение по категориям:

```text

```

Распределение по регионам:

```text

```

SID-diversity:

```text
n_unique_sid0:
n_unique_sid01:
n_unique_sid012:
```

Среднее число уникальных sid01 на пользователя в top-160:

```text

```

Среднее число уникальных категорий на пользователя в top-160:

```text

```

Среднее число уникальных регионов на пользователя в top-160:

```text

```

---

## 17. Интерпретация результата

Что сработало:

```text

```

Что не сработало:

```text

```

Возможное объяснение результата:

```text

```

Был ли источник слишком широким?

```text

```

Был ли источник слишком узким?

```text

```

Не стал ли результат слишком похожим на global popular?

```text

```

Не ухудшилась ли персонализация?

```text

```

Не потеряли ли мы diversity?

```text

```

---

## 18. Анализ по сегментам пользователей

Заполнить, если есть сегментный анализ.

Пользователи с короткой историей:

```text
score / observation:
```

Пользователи с длинной историей:

```text
score / observation:
```

Пользователи с доминирующей vertical_id = 0:

```text
score / observation:
```

Пользователи с доминирующей vertical_id = 2:

```text
score / observation:
```

Пользователи с доминирующей vertical_id = 3:

```text
score / observation:
```

Пользователи с доминирующей vertical_id = 4:

```text
score / observation:
```

Пользователи с доминирующей vertical_id = 5:

```text
score / observation:
```

Пользователи с доминирующей vertical_id = 7:

```text
score / observation:
```

Пользователи с большим числом contact-событий:

```text
score / observation:
```

Пользователи почти только с eid=7:

```text
score / observation:
```

---

## 19. Возможные причины роста или падения

Отметить релевантное.

```text
[ ] новый источник добавил полезные персонализированные кандидаты
[ ] новый источник добавил слишком много шумных кандидатов
[ ] выросла доля популярных, но неперсонализированных item-ов
[ ] слишком сильное влияние eid=7
[ ] слишком слабое влияние contact_eids
[ ] sid01 оказался полезнее category
[ ] category оказался полезнее sid01
[ ] региональная привязка помогла
[ ] региональная привязка ухудшила recall из-за слишком узкой фильтрации
[ ] source_weight слишком большой
[ ] source_weight слишком маленький
[ ] top_items_per_key слишком большой
[ ] top_items_per_key слишком маленький
[ ] fallback занимает слишком много мест
[ ] недостаточно diversity в top-160
```

Комментарий:

```text

```

---

## 20. Решение по эксперименту

Выбрать одно:

```text
[ ] принять как новый baseline
[ ] оставить как дополнительный источник идей
[ ] отклонить
[ ] повторить с другими параметрами
[ ] объединить частично с другим экспериментом
```

Причина решения:

```text

```

---

## 21. Следующие шаги

Конкретные следующие действия:

```text
1.
2.
3.
```

Следующая гипотеза:

```text

```

Следующий файл конфигурации:

```text
configs/<next_config>.yaml
```

Следующий сабмит:

```text
data/submissions/<next_submission>.csv
```

---

## 22. Заметки

Любые дополнительные наблюдения:

```text

```

Идеи, которые стоит проверить позже:

```text
- добавить ALS/collaborative candidates;
- построить local validation на train-файлах;
- подобрать event weights;
- подобрать half-life;
- добавить source vertical_sid012;
- добавить source region_sid01;
- попробовать source category_region_sid01;
- проверить более сильный popularity prior;
- проверить diversity-aware top-160;
- обучить LightGBM reranker на локальном split.
```
