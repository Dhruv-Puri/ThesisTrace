from __future__ import annotations

import tempfile
from pathlib import Path

from api.pipeline.ingest import ingest_text

BASE_TMP = Path(__file__).resolve().parent / ".tmp"


def temp_dir() -> tempfile.TemporaryDirectory:
    BASE_TMP.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=str(BASE_TMP))


SAMPLE_PAPER = """SparseRoute: Adaptive Sparsity for Efficient Neural Machine Translation

Abstract
Neural machine translation models are accurate but expensive at inference time. We propose SparseRoute, a routing layer that activates only a subset of feed-forward blocks. On WMT14 English-German, SparseRoute reduces inference latency by 42% compared with the dense Transformer baseline while maintaining BLEU within 0.3 points of it. The method is evaluated on a single GPU and uses a publicly available dataset.

1. Introduction
Translation quality has improved rapidly with Transformer models. However, deployment is limited by inference cost. We address this problem with a learned router.

2. Method
We introduce a routing layer with a top-2 gate. The architecture uses 12 encoder layers, hidden size 768, and a learning rate of 0.0003 with batch size 64 for 30 epochs. We use a fixed random seed of 42. The implementation is available at https://github.com/example/sparseroute and the dataset is publicly available at https://huggingface.co/datasets/wmt14.

3. Experiments
We evaluate on WMT14 English-German. The baseline is the dense Transformer. SparseRoute achieves 28.4 BLEU compared with 28.7 BLEU for the baseline, and reduces latency from 120 ms to 70 ms per sentence. Results show a 42% reduction in latency. Accuracy of the router is 91.2%.

4. Discussion
The evaluation is limited to a single large-scale GPU environment. No field trial or production deployment was conducted.

5. Conclusion
SparseRoute can cut energy consumption by up to 60% in data-centre deployments. The approach may generalize to low-resource language pairs. Future work will study production deployment.

References
[1] Vaswani et al. Attention is all you need. 2017.
[2] Ott et al. fairseq. 2019.
"""


def sample_document():
    return ingest_text(SAMPLE_PAPER, "sample-paper.txt")


LAB_PAPER = """A Lab Study of a Routing Layer

Abstract
Inference is expensive. We propose a routing layer and study it in a controlled lab experiment.

1. Introduction
We address the problem of expensive inference in neural machine translation.

2. Method
We train a model with a learning rate of 0.001, batch size 32 and 10 epochs. The architecture has 6 layers.

3. Results
We evaluate the method on a benchmark. The baseline is a dense model, and our method outperforms the baseline on the test set.

4. Conclusion
The method is validated in a lab setting.
"""


FIELD_PAPER = LAB_PAPER.replace(
    "The method is validated in a lab setting.",
    "We conducted a field trial in a hospital and validated the method in a relevant clinical environment.",
)


REVIEW_PAPER = """A Survey of Neural Machine Translation Methods

Abstract
This survey reviews the literature on translation models.

1. Introduction
We review prior work and compare approaches.

2. Results
We compare a baseline and report that many methods outperform it.
"""
