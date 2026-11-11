"""第03章 · 长期记忆三种落法的最小内存演示。

1. 实体 / 键值记忆：按实体名存取事实，命中精确；
2. 向量记忆：纯 Python 词袋相似度演示检索思路（生产替换为 Embedding + 向量库）；
3. 文件数据库记忆：JSON 文件持久化，演示跨会话落盘。

本脚本不调用模型、不依赖向量数据库；运行：python long_term_memory.py
"""
import json
import math
import os
import re
from collections import Counter

# ---------------------------------------------------------------------------
# 1. 实体 / 键值记忆：以实体名为键，事实列表为值
# ---------------------------------------------------------------------------


class KVMemory:
    def __init__(self) -> None:
        self.store: dict[str, list[str]] = {}

    def remember(self, entity: str, fact: str) -> None:
        self.store.setdefault(entity, []).append(fact)

    def recall(self, entity: str) -> list[str]:
        return self.store.get(entity, [])


# ---------------------------------------------------------------------------
# 2. 向量记忆：这里用词袋 TF 向量 + 余弦相似度最小演示
#    生产做法：OpenAI Embedding 生成稠密向量，存入 Chroma / Qdrant / pgvector 等
# ---------------------------------------------------------------------------


def tokenize(text: str) -> list[str]:
    """最小分词：英文/数字按词，中文按单字 + 相邻二元字组。

    仅用于演示相似度思路；生产环境直接使用 Embedding 向量，不做词袋匹配。
    """
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    tokens.extend(cjk)
    tokens.extend("".join(pair) for pair in zip(cjk, cjk[1:]))
    return tokens


class VectorMemory:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def add(self, text: str, meta: dict | None = None) -> None:
        self.records.append(
            {"text": text, "meta": meta or {}, "vector": dict(Counter(tokenize(text)))}
        )

    @staticmethod
    def _cosine(a: dict[str, int], b: dict[str, int]) -> float:
        common = set(a) & set(b)
        dot = sum(a[k] * b[k] for k in common)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query: str, top_k: int = 2) -> list[dict]:
        query_vec = dict(Counter(tokenize(query)))
        scored = [
            (self._cosine(query_vec, record["vector"]), record)
            for record in self.records
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for score, record in scored[:top_k] if score > 0]


# ---------------------------------------------------------------------------
# 3. 文件数据库记忆：JSON 文件落盘，进程重启后仍可读取
# ---------------------------------------------------------------------------


class FileMemory:
    def __init__(self, path: str) -> None:
        self.path = path
        self.data: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return []

    def add(self, key: str, value: str) -> None:
        self.data.append({"key": key, "value": value})
        self._save()

    def search(self, keyword: str) -> list[dict]:
        return [item for item in self.data if keyword in item["key"] or keyword in item["value"]]

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 键值记忆：按实体精确取事实
    kv = KVMemory()
    kv.remember("小林", "电商后台订单模块负责人")
    kv.remember("订单模块", "状态机：待支付 / 已支付 / 已发货 / 已完成")
    print("== 键值记忆 · recall(小林) ==")
    print(kv.recall("小林"))

    # 向量记忆：按语义相近度召回
    vm = VectorMemory()
    vm.add("待支付订单超时 15 分钟自动关闭并释放库存", meta={"topic": "订单"})
    vm.add("退款流程先走人工审核，暂不支持自动退款", meta={"topic": "售后"})
    vm.add("商品详情页需要展示价格、库存与促销标签", meta={"topic": "商品"})
    print("\n== 向量记忆 · search('订单超时怎么处理') ==")
    for hit in vm.search("订单超时怎么处理"):
        print("-", hit["text"])

    # 文件记忆：写入 JSON，重新读取验证持久化
    fm = FileMemory("long_term_memory.json")
    fm.add("deployment_note", "测试环境每日凌晨自动回收临时数据")
    print("\n== 文件记忆 · search('测试环境') ==")
    for item in fm.search("测试环境"):
        print("-", item)
    print(f"（已落盘到 {os.path.abspath('long_term_memory.json')}）")
