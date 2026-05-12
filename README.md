# AvitoTech ML Cup 2026 — Geometry-Aware Candidate Retrieval

Репозиторий содержит первый воспроизводимый baseline для AvitoTech ML Cup 2026 на основе геометрической кандидатной генерации.

Основная идея решения: рассматривать объявления как точки дискретного стратифицированного пространства, а историю пользователя — как атомарную меру интереса на этом пространстве. Кандидаты для рекомендации извлекаются из тех областей пространства, где у пользователя накоплена наибольшая масса интереса.

Текущий baseline:

```text

geometry_v1

```

Public leaderboard score:

```text

Recall@160 = 0.0090026262

```

---

## 1. Идея решения

Каждое объявление задаётся признаками:

```text

item_id

vertical_id

category_ext_y

region_id_y

loc_id_y

sid_0_y

sid_1_y

sid_2_y

sid_3_y

```

То есть объявление можно рассматривать как точку:

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

Пользователь не представляется одной фиксированной точкой. Вместо этого его история рассматривается как эмпирическая атомарная мера:

```text

mu_u = sum_{(u,i,e,t)} w(e,t) * delta_{x_i}

```

Где:

```text

u           — пользователь;

i           — объявление;

e           — тип события;

t           — время события;

x_i         — точка объявления в пространстве item-ов;

delta_{x_i} — атом в точке x_i;

w(e,t)      — вес события с учётом типа события и давности.

```

Вес события задаётся формулой:

```text

w(e,t) = alpha_e * exp(-lambda * age_days)

lambda = log(2) / half_life_days

```

Интерпретация: каждое действие пользователя кладёт массу интереса в точку соответствующего объявления. Чем действие сильнее и свежее, тем больше масса.

После этого строятся проекции пользовательской меры на геометрические ключи:

```text

(user_id, vertical_id, category_ext_y, region_id_y)

(user_id, vertical_id, category_ext_y)

(user_id, vertical_id, sid_0_y, sid_1_y)

(user_id, vertical_id, sid_0_y, sid_1_y, sid_2_y)

(user_id, region_id_y, sid_0_y, sid_1_y)

```

Для этих же ключей строятся индексы кандидатов:

```text

geometry_key -> top popular item_id inside this key

```

Финальная оценка кандидата:

```text

score = mass * source_weight * (1 + log1p(item_popularity)) / sqrt(rank_in_key)

```

Затем кандидаты агрегируются, уже виденные пользователем объявления удаляются, добавляется global popular fallback, и на каждого пользователя берётся top-160 item_id.

---

## 2. Структура проекта

```text

avito_ml_cup_2026/

├── configs/

│   ├── geometry_v1.yaml

│   └── paths.py

│

├── data/

│   ├── raw/

│   │   └── .gitkeep

│   ├── interim/

│   │   └── .gitkeep

│   ├── processed/

│   │   └── .gitkeep

│   └── submissions/

│       └── .gitkeep

│

├── experiments/

│   └── experiment_template.md

│

├── reports/

│   ├── item_space_minmax.csv

│   ├── item_space_sample_cardinalities.csv

│   ├── item_space_summary.csv

│   ├── top_categories.csv

│   └── vertical_counts.csv

│

├── src/

│   ├── analyze_item_space.py

│   ├── analyze_item_space_light.py

│   ├── build_candidate_indices.py

│   ├── build_eval_events_geometry.py

│   ├── build_geometry_submission_v1.py

│   ├── build_item_geometry.py

│   ├── build_user_interest_measure.py

│   ├── build_user_interest_profiles.py

│   ├── check_data.py

│   └── validate_submission.py

│

├── .gitignore

├── README.md

└── requirements.txt

```

---

## 3. Папка `configs/`

Папка содержит конфигурационные файлы проекта.

### `configs/paths.py`

Файл с централизованным описанием путей.

В нём задаются:

```text

PROJECT_ROOT

DATA_DIR

RAW_DIR

INTERIM_DIR

PROCESSED_DIR

SUBMISSIONS_DIR

REPORTS_DIR

ITEM_FEATURES_PATH

EVAL_USER_EVENTS_PATH

EVAL_USERS_PATH

CONTACT_EIDS_PATH

```

Назначение: все скрипты используют одни и те же пути, поэтому не нужно вручную прописывать абсолютные пути в каждом файле.

### `configs/geometry_v1.yaml`

Файл параметров первого baseline-эксперимента `geometry_v1`.

В нём фиксируются:

```text

название эксперимента;

описание идеи;

используемые raw/interim/submission директории;

eval-релевантные vertical_id;

признаки item-пространства;

half-life для временного затухания;

веса событий;

геометрические профили пользователя;

размеры candidate indices;

источники кандидатов;

формула scoring;

правила postprocessing;

итоговый public score.

```

Этот файл нужен для воспроизводимости эксперимента. Если меняется вес источника, half-life, top_k или набор candidate sources, нужно создавать новый конфиг, например:

```text

configs/geometry_v2.yaml

```

---

## 4. Папка `data/`

Папка `data/` разделена на четыре уровня.

### `data/raw/`

Сюда кладутся исходные файлы соревнования.

Ожидаемые файлы:

```text

item_features.parquet

eval_user_events.pq

eval_users.csv

contact_eids.csv

eval_user_events.zip

prepare_local_eval.py

popular.py

submission_popular.csv

```

Для полного локального обучения позже могут быть добавлены:

```text

train_000-019.zip

train_020-039.zip

train_040-059.zip

train_060-079.zip

train_080-099.zip

```

Эти файлы не хранятся в Git, потому что они большие. Папка сохраняется в репозитории только через `.gitkeep`.

### `data/interim/`

Сюда сохраняются промежуточные parquet-файлы, построенные скриптами из `src/`.

В текущем pipeline создаются:

```text

item_geometry_eval_verticals.parquet

eval_events_geometry.parquet

user_interest_measure.parquet

user_profile_vertical_category_region.parquet

user_profile_vertical_category.parquet

user_profile_vertical_sid01.parquet

user_profile_vertical_sid012.parquet

user_profile_region_sid01.parquet

item_popularity_eval_events.parquet

candidate_index_vertical_category_region.parquet

candidate_index_vertical_category.parquet

candidate_index_vertical_sid01.parquet

candidate_index_region_sid01.parquet

candidate_index_global_popular.parquet

geometry_candidates_v1.parquet

```

Эти файлы тоже не хранятся в Git, потому что они большие и воспроизводятся из raw-данных.

### `data/processed/`

Папка зарезервирована для будущих финальных обработанных датасетов.

Например, сюда можно будет положить:

```text

local_train.parquet

local_targets.parquet

reranker_train.parquet

als_user_item_matrix.npz

```

В текущей версии `geometry_v1` папка почти не используется.

### `data/submissions/`

Сюда сохраняются файлы сабмитов.

Текущий основной сабмит:

```text

submission_geometry_v1.csv

```

Формат файла:

```text

user_id,item_id

33,69678510

33,64225710

...

```

Сабмиты не хранятся в Git, потому что могут быть большими. Для `geometry_v1` файл содержит:

```text

15,105,280 строк

94,408 пользователей

160 рекомендаций на пользователя

```

---

## 5. Папка `experiments/`

Папка содержит описание экспериментов.

### `experiments/experiment_template.md`

Расширенный шаблон лабораторного журнала для новых экспериментов.

В шаблоне фиксируются:

```text

метаданные эксперимента;

цель;

гипотеза;

математическая постановка;

изменения относительно baseline;

используемые данные;

конфигурация;

источники кандидатов;

команды запуска;

валидация сабмита;

local validation;

public leaderboard result;

сравнение с baseline;

диагностика кандидатов;

диагностика геометрии;

интерпретация результата;

решение по эксперименту;

следующие шаги.

```

Для каждого нового эксперимента рекомендуется копировать шаблон:

```bash

cp experiments/experiment_template.md experiments/geometry_v2.md

```

И затем заполнять конкретные параметры и результат.

---

## 6. Папка `reports/`

Папка содержит небольшие диагностические отчёты, которые можно хранить в Git.

### `reports/item_space_minmax.csv`

Минимальные и максимальные значения основных признаков item-пространства.

Используется для проверки диапазонов:

```text

vertical_id

category_ext_y

region_id_y

loc_id_y

sid_0_y

sid_1_y

sid_2_y

sid_3_y

```

### `reports/item_space_sample_cardinalities.csv`

Оценка количества уникальных значений на sample из `item_features`.

Используется для первичной оценки мощности пространства:

```text

количество категорий;

количество регионов;

количество локаций;

количество sid_0;

количество sid01;

количество sid012.

```

### `reports/item_space_summary.csv`

Сводка по item-пространству.

Может содержать min/max/n_unique для признаков, если полный анализ был запущен.

### `reports/top_categories.csv`

Топ категорий по числу объявлений.

Используется для понимания распределения item-ов по категориям.

### `reports/vertical_counts.csv`

Количество item-ов по `vertical_id`.

Для `geometry_v1` было получено:

```text

vertical_id = 0: 153,162,868 item-ов

vertical_id = 1:       8,609 item-ов

vertical_id = 2:   4,947,048 item-ов

vertical_id = 3:   6,197,510 item-ов

vertical_id = 4:   7,540,650 item-ов

vertical_id = 5:   4,143,039 item-ов

vertical_id = 6:      14,042 item-ов

vertical_id = 7:   2,313,893 item-ов

```

Из-за малости и отсутствия в eval вертикали `1` и `6` исключаются из candidate generation.

---

## 7. Папка `src/`

Папка содержит исполняемые Python-скрипты pipeline.

### `src/check_data.py`

Проверяет наличие и читаемость raw-файлов:

```text

item_features.parquet

eval_user_events.pq

eval_users.csv

contact_eids.csv

```

Что делает:

```text

проверяет, существует ли файл;

печатает размер файла;

печатает схему;

печатает первые строки;

считает количество строк.

```

Запуск:

```bash

python src/check_data.py

```

Используется после скачивания данных, чтобы убедиться, что файлы лежат в правильных местах и читаются Polars.

---

### `src/analyze_item_space.py`

Полный анализ item-пространства.

Что делает:

```text

считает min/max/n_unique для основных признаков;

считает количество item-ов по vertical_id;

считает топ категорий;

считает количество уникальных sid-префиксов.

```

Для быстрого анализа лучше использовать `analyze_item_space_light.py`.

Запуск:

```bash

python src/analyze_item_space.py

```

---

### `src/analyze_item_space_light.py`

Лёгкая версия анализа item-пространства.

Что делает:

```text

считает min/max для признаков;

считает количество item-ов по vertical_id;

на sample 1,000,000 строк оценивает мощности категорий, регионов, loc и sid-префиксов.

```

Запуск:

```bash

python src/analyze_item_space_light.py

```

Результаты сохраняются в `reports/`.

---

### `src/build_item_geometry.py`

Строит компактную таблицу геометрии объявлений только для eval-релевантных вертикалей.

Вход:

```text

data/raw/item_features.parquet

```

Выход:

```text

data/interim/item_geometry_eval_verticals.parquet

```

Что делает:

```text

оставляет vertical_id из {0, 2, 3, 4, 5, 7};

выбирает признаки item-пространства;

приводит типы к более компактным UInt8/UInt16/UInt32;

сохраняет parquet.

```

Запуск:

```bash

python src/build_item_geometry.py

```

Для `geometry_v1` результат:

```text

178,305,008 item-ов

6 vertical_id

50 категорий

85 регионов

6665 локаций

1024 значения sid_0

```

---

### `src/build_eval_events_geometry.py`

Присоединяет геометрию объявлений к истории eval-пользователей.

Вход:

```text

data/raw/eval_user_events.pq

data/interim/item_geometry_eval_verticals.parquet

```

Выход:

```text

data/interim/eval_events_geometry.parquet

```

Что делает:

```text

читает события eval-пользователей;

читает item geometry;

делает inner join по item_id;

получает таблицу событий с признаками item-а.

```

После этого каждая строка события уже указывает не просто на `item_id`, а на точку `x_i` в геометрическом пространстве объявлений.

Запуск:

```bash

python src/build_eval_events_geometry.py

```

Для `geometry_v1` результат:

```text

96,773,143 события после join

94,405 пользователей

30,456,920 item-ов

17 типов eid

6 vertical_id

50 категорий

85 регионов

1024 sid_0

```

---

### `src/build_user_interest_measure.py`

Строит атомарную пользовательскую меру интереса.

Вход:

```text

data/interim/eval_events_geometry.parquet

data/raw/contact_eids.csv

```

Выход:

```text

data/interim/user_interest_measure.parquet

```

Что делает:

```text

читает события с геометрией;

читает contact_eids;

считает age_days;

задаёт event_alpha по типу события;

считает event_weight = event_alpha * exp(-lambda * age_days);

сохраняет weighted events.

```

Параметры `geometry_v1`:

```text

half_life_days = 7.0

contact_eids weight = 8.0

eid = 7 weight = 1.0

eid = 10 weight = 2.0

other eids weight = 3.0

```

Запуск:

```bash

python src/build_user_interest_measure.py

```

Результат интерпретируется так:

```text

каждая строка = атом пользовательской меры;

event_weight = масса атома.

```

---

### `src/build_user_interest_profiles.py`

Строит компактные проекции пользовательской меры на геометрические ключи.

Вход:

```text

data/interim/user_interest_measure.parquet

```

Выходы:

```text

data/interim/user_profile_vertical_category_region.parquet

data/interim/user_profile_vertical_category.parquet

data/interim/user_profile_vertical_sid01.parquet

data/interim/user_profile_vertical_sid012.parquet

data/interim/user_profile_region_sid01.parquet

```

Что делает:

```text

группирует атомы пользовательской меры по user_id и геометрическим ключам;

суммирует event_weight в mass;

считает n_events;

сохраняет top-k областей на пользователя.

```

Например строка:

```text

user_id = 33

vertical_id = 0

category_ext_y = 4

region_id_y = 53

mass = 74.35

```

означает, что у пользователя 33 большая масса интереса лежит в области:

```text

vertical=0, category=4, region=53

```

Запуск:

```bash

python src/build_user_interest_profiles.py

```

---

### `src/build_candidate_indices.py`

Строит индексы кандидатов по геометрическим ключам.

Входы:

```text

data/interim/eval_events_geometry.parquet

data/interim/item_geometry_eval_verticals.parquet

```

Выходы:

```text

data/interim/item_popularity_eval_events.parquet

data/interim/candidate_index_vertical_category_region.parquet

data/interim/candidate_index_vertical_category.parquet

data/interim/candidate_index_vertical_sid01.parquet

data/interim/candidate_index_region_sid01.parquet

data/interim/candidate_index_global_popular.parquet

```

Что делает:

```text

считает item_popularity по eval history;

соединяет popularity с item geometry;

строит top item-ов для каждого geometry key;

строит global popular fallback.

```

Примеры индексов:

```text

(vertical_id, category_ext_y, region_id_y) -> top item_id

(vertical_id, category_ext_y)              -> top item_id

(vertical_id, sid_0_y, sid_1_y)            -> top item_id

(region_id_y, sid_0_y, sid_1_y)            -> top item_id

```

Запуск:

```bash

python src/build_candidate_indices.py

```

---

### `src/build_geometry_submission_v1.py`

Собирает финальный сабмит `geometry_v1`.

Входы:

```text

user profiles

candidate indices

eval_users.csv

eval_events_geometry.parquet

global popular fallback

```

Выходы:

```text

data/interim/geometry_candidates_v1.parquet

data/submissions/submission_geometry_v1.csv

```

Что делает:

```text

берёт top-области пользователя по mass;

достаёт item-ы из соответствующих candidate indices;

считает score;

склеивает кандидатов из нескольких источников;

агрегирует дубли user_id-item_id;

удаляет уже виденные пользователем item_id;

добавляет global popular fallback;

ранжирует кандидатов;

берёт top-160 на пользователя;

сохраняет CSV-сабмит.

```

Источники кандидатов в `geometry_v1`:

```text

vertical_category_region:

  key = (vertical_id, category_ext_y, region_id_y)

  source_weight = 1.00

  top_profile_keys = 5

  top_items_per_key = 50

vertical_category:

  key = (vertical_id, category_ext_y)

  source_weight = 0.60

  top_profile_keys = 5

  top_items_per_key = 60

vertical_sid01:

  key = (vertical_id, sid_0_y, sid_1_y)

  source_weight = 0.80

  top_profile_keys = 5

  top_items_per_key = 30

```

Запуск:

```bash

python src/build_geometry_submission_v1.py

```

---

### `src/validate_submission.py`

Проверяет корректность сабмита.

Входы:

```text

data/submissions/submission_geometry_v1.csv

data/raw/eval_users.csv

data/interim/item_geometry_eval_verticals.parquet

```

Что проверяет:

```text

число строк;

число пользователей;

число уникальных item-ов;

минимальное/среднее/максимальное число рекомендаций на пользователя;

наличие рекомендаций для всех eval-users;

наличие неизвестных user_id;

наличие дублей user_id-item_id;

наличие пользователей с более чем 160 рекомендациями;

наличие неизвестных item_id.

```

Запуск:

```bash

python src/validate_submission.py

```

Для `geometry_v1` результат:

```text

n_rows = 15,105,280

n_users = 94,408

n_items = 544,977

min_recs = 160

mean_recs = 160

max_recs = 160

n_missing_users = 0

n_unknown_users = 0

n_duplicate_pairs = 0

n_users_too_many = 0

n_unknown_items = 0

```

---

## 8. Установка окружения

Создать виртуальное окружение:

```bash

python3 -m venv .venv

source .venv/bin/activate

```

Установить зависимости:

```bash

python -m pip install --upgrade pip

python -m pip install -r requirements.txt

```

Проверить окружение:

```bash

python - <<'PY'

import polars as pl

import duckdb

import numpy as np

import pandas as pd

import scipy

import sklearn

print("Environment OK")

print("polars:", pl.__version__)

print("duckdb:", duckdb.__version__)

PY

```

---

## 9. Скачивание данных

Минимальный набор для воспроизведения `geometry_v1`:

```bash

cd data/raw

BASE=https://storage.yandexcloud.net/datafest2026/datafest_2026_v2_v4

curl -O $BASE/item_features.parquet

curl -O $BASE/contact_eids.csv

curl -O $BASE/eval_users.csv

curl -O $BASE/eval_user_events.zip

curl -O $BASE/prepare_local_eval.py

curl -O $BASE/popular.py

curl -O $BASE/submission_popular.csv

unzip eval_user_events.zip

```

После распаковки в `data/raw/` должны лежать:

```text

item_features.parquet

contact_eids.csv

eval_users.csv

eval_user_events.pq

eval_user_events.zip

prepare_local_eval.py

popular.py

submission_popular.csv

```

Полные train-архивы для будущих экспериментов:

```bash

for i in 000-019 020-039 040-059 060-079 080-099; do

    curl -O $BASE/train_${i}.zip

done

```

В `geometry_v1` train-архивы не использовались.

---

## 10. Полный порядок запуска `geometry_v1`

Из корня проекта:

```bash

python src/check_data.py

python src/analyze_item_space_light.py

python src/build_item_geometry.py

python src/build_eval_events_geometry.py

python src/build_user_interest_measure.py

python src/build_user_interest_profiles.py

python src/build_candidate_indices.py

python src/build_geometry_submission_v1.py

python src/validate_submission.py

```

После успешного запуска финальный файл:

```text

data/submissions/submission_geometry_v1.csv

```

---

## 11. Результат `geometry_v1`

Файл:

```text

data/submissions/submission_geometry_v1.csv

```

Валидация:

```text

94,408 пользователей

160 рекомендаций на каждого пользователя

0 дублей user_id-item_id

0 неизвестных user_id

0 неизвестных item_id

```

Public leaderboard:

```text

Recall@160 = 0.0090026262

```

---

## 12. Что хранится в Git, а что нет

В Git хранятся:

```text

код;

конфиги;

шаблоны экспериментов;

маленькие отчёты;

requirements.txt;

README.md;

.gitignore;

.gitkeep в data-папках.

```

В Git не хранятся:

```text

raw-данные;

interim parquet-файлы;

submission CSV;

архивы train/eval;

виртуальное окружение;

__pycache__;

.ipynb_checkpoints.

```

Это контролируется через `.gitignore`.

---

## 13. Текущая ветка

Основная рабочая ветка первого baseline:

```text

geometry-v1

```

Рекомендуемый workflow для новых экспериментов:

```bash

git checkout geometry-v1

git checkout -b geometry-v2

```

После нового результата:

```bash

git add configs src experiments reports README.md

git commit -m "Add geometry v2 experiment"

git push -u origin geometry-v2

```

---

## 14. Следующие идеи

Ближайшие гипотезы для улучшения:

```text

1. Добавить source region_sid01.

2. Добавить source vertical_sid012 с небольшим top_k.

3. Подобрать веса событий, чтобы уменьшить доминирование eid=7.

4. Подобрать half_life_days.

5. Построить local validation через train-файлы.

6. Добавить ALS/collaborative retrieval.

7. Добавить LightGBM/CatBoost reranker.

8. Посчитать source contribution diagnostics.

9. Проверить diversity-aware top-160.

```

---

## 15. Краткое резюме

`geometry_v1` — это первый воспроизводимый геометрический baseline.

Он использует:

```text

item geometry;

user interest measure;

time decay;

event weights;

semantic sid-prefix;

category/region matching;

popularity prior;

seen-item filtering;

global fallback.

```


out.write_text(content, encoding="utf-8")

print(out)
