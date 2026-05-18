import pickle
import os
import subprocess
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

spark = SparkSession.builder \
    .appName("GenerateCandidates") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

sc = spark.sparkContext
sqlContext = spark.sqlContext

# Читаем S3-настройки из .env.
# Секретные ключи здесь НЕ хранятся: они лежат в AWS profile.
load_dotenv(Path(".env"))

S3_ENDPOINT_URL = os.environ["S3_ENDPOINT_URL"]
S3_BUCKET = os.environ["S3_BUCKET"]
AWS_PROFILE = os.environ["AWS_PROFILE"]

BUCKET = f"s3a://{S3_BUCKET}"
S3_URI = f"s3://{S3_BUCKET}"

print("Читаем данные из S3...")
print("BUCKET:", BUCKET)
print("S3_URI:", S3_URI)
print("AWS_PROFILE:", AWS_PROFILE)

# Читаем eval_users.csv
eval_users_df = spark.read.csv(f"{BUCKET}/eval_users.csv", header=True)
eval_users = eval_users_df.collect()

# Читаем eval_user_events.pq
eval_events_df = spark.read.parquet(f"{BUCKET}/eval_user_events.pq")
eval_events = eval_events_df.collect()

# Для item_factors и словарей скачиваем файлы через awscli.
# Это работает с Yandex Object Storage через endpoint-url.
def aws_s3_cp(src: str, dst: str) -> None:
    cmd = [
        "aws", "s3", "cp",
        src,
        dst,
        "--endpoint-url", S3_ENDPOINT_URL,
        "--profile", AWS_PROFILE,
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


aws_s3_cp(f"{S3_URI}/item_factors.npy", "/tmp/item_factors.npy")
aws_s3_cp(f"{S3_URI}/item_to_idx_full.pkl", "/tmp/item_to_idx_full.pkl")
aws_s3_cp(f"{S3_URI}/idx_to_item_full.pkl", "/tmp/idx_to_item_full.pkl")

item_factors = np.load("/tmp/item_factors.npy", mmap_mode='r')
with open("/tmp/item_to_idx_full.pkl", "rb") as f:
    item_to_idx = pickle.load(f)
with open("/tmp/idx_to_item_full.pkl", "rb") as f:
    idx_to_item = pickle.load(f)

print("Группируем историю eval-пользователей по user_id...")
user_to_items = {}

for event in eval_events:
    uid = event["user_id"]
    item_id = event["item_id"]
    user_to_items.setdefault(uid, []).append(item_id)

print(f"Пользователей с событиями в eval_user_events: {len(user_to_items)}")

print("Вычисляем эмбеддинги пользователей...")
user_embeddings = {}
cold_users = []

for uid_row in eval_users:
    uid = uid_row["user_id"]
    user_items = user_to_items.get(uid, [])

    indices = []
    for item_id in user_items:
        idx = item_to_idx.get(item_id)
        if idx is not None:
            indices.append(idx)

    if indices:
        user_embeddings[uid] = np.mean(item_factors[indices], axis=0).astype(np.float32)
    else:
        cold_users.append(uid)

print(f"Пользователей с эмбеддингом: {len(user_embeddings)}")
print(f"Cold users: {len(cold_users)}")

uid_list = list(user_embeddings.keys())

# Параметры тяжёлого retrieval.
# Можно переопределять при запуске:
# BATCH_SIZE=100 CHUNK_SIZE=1000000 TOP_K=1000 python -m src.generate_candidates_als_v4
batch_size = int(os.getenv("BATCH_SIZE", "100"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000000"))
TOP_K = int(os.getenv("TOP_K", "1000"))

print(f"BATCH_SIZE: {batch_size}")
print(f"CHUNK_SIZE: {CHUNK_SIZE}")
print(f"TOP_K: {TOP_K}")

def process_batch(uids):
    import numpy as np
    item_factors = np.load("/tmp/item_factors.npy", mmap_mode='r')
    batch_embs = np.array([user_embeddings[uid] for uid in uids], dtype=np.float32)
    chunk_size = CHUNK_SIZE
    num_items = item_factors.shape[0]
    batch_candidates = {uid: [] for uid in uids}
    
    for i_start in range(0, num_items, chunk_size):
        i_end = min(i_start + chunk_size, num_items)
        chunk = np.array(item_factors[i_start:i_end])
        scores = np.dot(batch_embs, chunk.T)
        
        for i, uid in enumerate(uids):
            top_indices = np.argpartition(scores[i], -TOP_K)[-TOP_K:]
            for idx in top_indices:
                batch_candidates[uid].append((i_start + idx, float(scores[i, idx])))
    
    result = {}
    for uid in uids:
        cands = batch_candidates[uid]
        cands.sort(key=lambda x: x[1], reverse=True)
        result[uid] = [int(idx) for idx, _ in cands[:TOP_K]]
    return result

batches = [uid_list[i:i+batch_size] for i in range(0, len(uid_list), batch_size)]
print(f"Обрабатываем {len(batches)} батчей...")

rdd = sc.parallelize(batches, len(batches))
results = rdd.map(process_batch).collect()

candidates = {}
for uid in cold_users:
    item_biases = np.dot(item_factors, item_factors.mean(axis=0))
    popular_indices = np.argsort(item_biases)[-TOP_K:][::-1]
    candidates[uid] = [int(idx_to_item[i]) for i in popular_indices]

for r in results:
    for uid, idx_list in r.items():
        candidates[uid] = [int(idx_to_item[idx]) for idx in idx_list]

# Сохраняем результат в S3 через pickle
import pickle as pk

output_path = "/tmp/als_candidates_full.pkl"

with open(output_path, "wb") as f:
    pk.dump(candidates, f)

aws_s3_cp(output_path, f"{S3_URI}/als_candidates_full.pkl")
print(f"Кандидаты для {len(candidates)} пользователей сохранены в S3!")

spark.stop()
