"""NLP pipeline for ThesisTrace.

The pipeline is deliberately layered the same way CSR322 teaches NLP:

    classical NLP (regex, TF-IDF, POS)  ->  neural NLP (Hugging Face)
    ->  optional LLM layer (Gemini) grounded on retrieved evidence.

Every heavy dependency is imported lazily.  This keeps the pipeline testable with
the Python standard library alone and lets the application degrade gracefully on a
weak laptop instead of crashing when a model or library is missing.
"""

PIPELINE_VERSION = "0.2.0"
