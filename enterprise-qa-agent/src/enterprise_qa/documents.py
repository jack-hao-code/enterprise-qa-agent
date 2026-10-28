"""Read-only synthetic knowledge tools; no model routing decisions here."""
import copy
import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path

from .protocol import failure


def tokens(text):
    """Chinese bigrams + ASCII words; intentionally transparent, not semantic search."""
    result = set(re.findall(r'[a-z0-9_]+', text.lower()))
    for segment in re.findall(r'[\u4e00-\u9fff]+', text):
        if len(segment) == 1:
            continue
        result.update(segment[i:i + 2] for i in range(len(segment) - 1))
    return result


class DocumentStore:
    def __init__(self, path):
        self.path = Path(path)
        raw = self.path.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.documents = json.loads(raw)
        self._validate()
        self.by_id = {doc['id']: doc for doc in self.documents}

    def _validate(self):
        if not isinstance(self.documents, list) or len(self.documents) > 1000:
            raise ValueError('资料必须是至多 1000 篇文档的数组')
        ids = set()
        for doc in self.documents:
            if not isinstance(doc, dict):
                raise ValueError('文档必须是对象')
            for key in ('id', 'title', 'version_date'):
                if not isinstance(doc.get(key), str) or not doc[key].strip():
                    raise ValueError('缺少文档字段: ' + key)
            date.fromisoformat(doc['version_date'])
            if doc['id'] in ids:
                raise ValueError('重复文档 ID')
            ids.add(doc['id'])
            chunks = doc.get('chunks')
            if not isinstance(chunks, list) or not chunks:
                raise ValueError('文档缺少原文片段')
            chunk_ids = set()
            for chunk in chunks:
                if not isinstance(chunk, dict):
                    raise ValueError('片段必须是对象')
                for key in ('id', 'text'):
                    if not isinstance(chunk.get(key), str) or not chunk[key].strip():
                        raise ValueError('缺少片段字段: ' + key)
                if len(chunk['text']) > 20000 or chunk['id'] in chunk_ids:
                    raise ValueError('片段过长或 ID 重复')
                chunk_ids.add(chunk['id'])
                annotations = ('claim_key', 'claim_value', 'scope')
                if any(key in chunk for key in annotations):
                    if not all(isinstance(chunk.get(key), str) and chunk[key].strip() for key in annotations):
                        raise ValueError('事实标注需完整包含 key/value/scope')
                    if chunk['claim_value'] not in chunk['text']:
                        raise ValueError('标注的事实值必须出现在原文中')

    def search(self, query, limit=10):
        if not isinstance(query, str) or not query.strip() or len(query) > 2000:
            return failure('INVALID_QUERY', '检索词为空或过长')
        if type(limit) is not int or not 1 <= limit <= 20:
            return failure('INVALID_LIMIT', 'limit 必须为 1-20 的整数')
        query_tokens = tokens(query)
        indexed = [(doc, tokens(doc['title']), tokens(' '.join(c['text'] for c in doc['chunks'])))
                   for doc in self.documents]
        hits = []
        for doc, title_tokens, body_tokens in indexed:
            matched = query_tokens & (title_tokens | body_tokens)
            score = 0.0
            for token in matched:
                frequency = sum(token in (title | body) for _, title, body in indexed)
                idf = math.log(1 + (len(indexed) + 1) / (frequency + 1))
                score += idf * (3 if token in title_tokens else 1)
            if score:
                hits.append({'document_id': doc['id'], 'title': doc['title'],
                             'version_date': doc['version_date'], 'score': round(score, 4)})
        hits.sort(key=lambda hit: (-hit['score'], hit['document_id']))
        return {'ok': True, 'query': query, 'hits': hits[:limit],
                'total_hits': len(hits), 'truncated': len(hits) > limit}

    def read(self, document_id):
        if document_id not in self.by_id:
            return failure('DOCUMENT_NOT_FOUND', '未找到文档: ' + str(document_id))
        return {'ok': True, 'document': copy.deepcopy(self.by_id[document_id])}
