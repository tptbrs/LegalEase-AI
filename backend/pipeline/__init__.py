"""LegalEase AI retrieval-augmented generation pipeline.

Modules in this package implement the seven-stage RAG flow:
    ingestion -> classifier -> retriever -> reranker
        -> prompt_builder -> llm_caller -> postprocessor

Each module is independently importable and unit-testable.
"""
