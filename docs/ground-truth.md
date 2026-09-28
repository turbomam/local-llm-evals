# Ground truth

Where the reference answers for each task come from.

## Photosynthesis

Two parts:

1. **A 10-item completeness checklist** for the free-form explanation, written from general biology and listed in [`results/2026-09-28-photosynthesis/`](../results/2026-09-28-photosynthesis/README.md). It is scored yes/no per item.
2. **Multiple-choice questions with fixed answers**, so no judge is needed. Candidates:

| source | what it has | status |
|---|---|---|
| [SciQ](https://huggingface.co/datasets/allenai/sciq), Allen Institute for AI | 13,679 crowdsourced science questions, 4 options each, most with a supporting paragraph | license not yet checked |
| ARC, Allen Institute for AI | 7,787 grade-school science questions, Easy and Challenge sets | license not yet checked |
| ProPara, Allen Institute for AI | paragraphs describing processes, photosynthesis among them, with questions about how entities change | license and format not yet checked |

Not used: OpenStax *Biology 2e*, chapter 8. A search summary reports that its terms forbid feeding the book to LLMs without OpenStax's permission; the terms page itself was not read.

## NMDC env triad

Five studies named in the NMDC suggester's success-criteria decision record, with their curated `env_broad_scale`, `env_local_scale` and `env_medium` values, and the GOLD ecosystem path already on each biosample. Whether the curated triads are sound enough to serve as ground truth is an open question and is reported, not assumed.

## BRIDGE CSV mapping

A small set of column-to-slot pairs drawn from nmdc-ai-eval's `submission-metadata-prediction` data and checked by hand. Before anything from that set is committed here, it must be confirmed to come from released, public submissions.

## BERIL questions

No fixed answers. Each response is checked claim by claim against the passages retrieved for it, so the passages are the reference.

## Capability cases

Twelve self-contained cases in five skill buckets, each with an exact answer, a set, or a correct refusal, in [`cases/capability-cases.yaml`](../cases/capability-cases.yaml). They were written in the private repository `turbomam/langfuse-notes` and copied here on 2026-09-28 from `evals/cases.yaml` at commit `7f6a3cc`. Because this repository is public, two things were changed in the copy: real account handles became neutral owner names with made-up counts, and a quoted pull request comment that could be traced became a paraphrase. The file's header records the same.
