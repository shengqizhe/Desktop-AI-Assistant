import os
import re
import json
import sys
from math import log, sqrt

def get_resource_path(relative_path):
    """ 获取打包进 EXE 内部的只读资源路径 """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_app_data_path(filename):
    """ 获取持久化数据路径（EXE 同级目录，实现绿色便携模式） """
    if hasattr(sys, '_MEIPASS'):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    
    data_dir = os.path.join(base_path, "data")
    target_path = os.path.join(data_dir, filename)
    
    # 确保目标目录存在
    target_dir = os.path.dirname(target_path)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    # 如果目标文件不存在，但打包资源中存在初始模板，则从 EXE 内部复制出来
    if not os.path.exists(target_path):
        bundled_path = get_resource_path(filename)
        if os.path.exists(bundled_path):
            import shutil
            shutil.copy2(bundled_path, target_path)
    
    return target_path

class KnowledgeBase:
    def __init__(self, root=None, index_file=None, chunk_size=500, overlap=50):
        self.root = root or get_resource_path("knowledge")
        self.index_file = index_file or get_app_data_path(os.path.join("knowledge", "kb_index.json"))
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.vocab = {}
        self.docs = []
        self.loaded = False

    def _list_files(self):
        exts = (".txt", ".md")
        files = []
        for dirpath, _, filenames in os.walk(self.root):
            for f in filenames:
                if f.lower().endswith(exts):
                    files.append(os.path.join(dirpath, f))
        return sorted(files)

    def _read_text(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            try:
                with open(path, "r", encoding="gbk") as f:
                    return f.read()
            except:
                return ""

    def _chunk(self, text):
        chunks = []
        n = self.chunk_size
        o = self.overlap
        start = 0
        L = len(text)
        while start < L:
            end = min(start + n, L)
            chunks.append(text[start:end])
            if end == L:
                break
            start = end - o
            if start < 0:
                start = 0
        return chunks

    def _tokens(self, s):
        parts = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", s)
        return [p.lower() for p in parts if p.strip()]

    def _build(self, files):
        docs = []
        df = {}
        for p in files:
            txt = self._read_text(p)
            if not txt:
                continue
            for ch in self._chunk(txt):
                tks = self._tokens(ch)
                if not tks:
                    continue
                tf = {}
                for t in tks:
                    tf[t] = tf.get(t, 0) + 1
                docs.append({"text": ch, "path": p, "tf": tf})
                seen = set()
                for t in tf:
                    if t not in seen:
                        df[t] = df.get(t, 0) + 1
                        seen.add(t)
        N = max(len(docs), 1)
        idf = {}
        for t, d in df.items():
            idf[t] = log((N + 1) / (d + 1)) + 1.0
        for d in docs:
            w = {}
            norm = 0.0
            for t, c in d["tf"].items():
                val = (c * idf.get(t, 0.0))
                w[t] = val
                norm += val * val
            d["w"] = w
            d["norm"] = sqrt(norm) if norm > 0 else 1.0
            del d["tf"]
        self.vocab = idf
        self.docs = docs

    def ingest(self):
        files = self._list_files()
        self._build(files)
        os.makedirs(os.path.dirname(self.index_file), exist_ok=True)
        data = {"vocab": self.vocab, "docs": self.docs}
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        self.loaded = True

    def load(self):
        if not os.path.exists(self.index_file):
            return False
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.vocab = data.get("vocab", {})
            self.docs = data.get("docs", [])
            for d in self.docs:
                if "norm" not in d:
                    w = d.get("w", {})
                    s = 0.0
                    for _, val in w.items():
                        s += val * val
                    d["norm"] = sqrt(s) if s > 0 else 1.0
            self.loaded = True
            return True
        except:
            return False

    def load_or_build(self):
        if not self.load():
            self.ingest()
        return True

    def query(self, text, k=3):
        if not self.loaded:
            self.load_or_build()
        q_tokens = self._tokens(text)
        q_tf = {}
        for t in q_tokens:
            q_tf[t] = q_tf.get(t, 0) + 1
        q_w = {}
        q_norm = 0.0
        for t, c in q_tf.items():
            val = c * self.vocab.get(t, 0.0)
            if val > 0:
                q_w[t] = val
                q_norm += val * val
        q_norm = sqrt(q_norm) if q_norm > 0 else 1.0
        scores = []
        for i, d in enumerate(self.docs):
            dot = 0.0
            w = d["w"]
            for t, v in q_w.items():
                dv = w.get(t)
                if dv:
                    dot += v * dv
            if dot > 0:
                sim = dot / (q_norm * d["norm"])
                scores.append((sim, i))
        scores.sort(key=lambda x: x[0], reverse=True)
        out = []
        for s, idx in scores[:k]:
            dd = self.docs[idx]
            out.append({"score": s, "text": dd["text"], "path": dd["path"]})
        return out
    
    def stats(self):
        files = self._list_files()
        return {
            "file_count": len(files),
            "chunk_count": len(self.docs),
            "vocab_size": len(self.vocab),
        }
