# src/utils/rag.py
# v0.1 - 간단한 RAG 유틸 (2025-08-28)
# - 로컬 텍스트 파일 임베딩/검색
# - LangChain Retriever 래퍼 제공
# - 섹션/타이틀 생성기에서 선택적으로 주입 가능

from typing import List, Optional
from pathlib import Path
import glob

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter


class SimpleRAG:
    """
    간단한 로컬 파일 기반 RAG 헬퍼

    사용 예시:
        rag = SimpleRAG(docs_dir="data")
        rag.build()
        context = rag.query("바이브코딩 핵심")
    """

    def __init__(
        self, docs_dir: str = "data", chunk_size: int = 900, chunk_overlap: int = 150
    ):
        self.docs_dir = Path(docs_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vs: Optional[FAISS] = None

    def _load_texts(self) -> List[str]:
        paths = [
            *glob.glob(str(self.docs_dir / "*.txt")),
            *glob.glob(str(self.docs_dir / "*.md")),
        ]
        texts: List[str] = []
        for p in paths:
            try:
                texts.append(Path(p).read_text(encoding="utf-8"))
            except Exception:
                continue
        return texts

    def build(self) -> None:
        texts = self._load_texts()
        if not texts:
            self.vs = None
            return
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        docs = []
        for t in texts:
            docs.extend(splitter.create_documents([t]))

        embeddings = OpenAIEmbeddings()
        self.vs = FAISS.from_documents(docs, embeddings)

    def query(self, q: str, k: int = 4) -> str:
        if not self.vs:
            return ""
        results = self.vs.similarity_search(q, k=k)
        joined = "\n\n".join([d.page_content for d in results])
        return f"[RAG 컨텍스트]\n{joined}\n\n[질문]\n{q}"
