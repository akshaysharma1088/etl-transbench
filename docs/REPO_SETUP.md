# Repo setup checklist

Cosmetic and metadata steps to do once, in the GitHub UI.

## 1. Replace the OWNER placeholder

Two badge URLs in `README.md` and one field in `CITATION.cff` contain `OWNER`
or `<you>`. Replace with your GitHub handle:

```bash
grep -rn "OWNER\|<you>" README.md CITATION.cff
sed -i 's/OWNER/your-handle/g; s|<you>|your-handle|g' README.md CITATION.cff
```

## 2. About panel (top right of the repo page)

**Description**

> Benchmark and agentic framework for legacy ETL to PySpark translation,
> verified by data equivalence. 32 executable tasks, 8 construct families,
> adversarial input generation.

**Website:** the paper DOI once published.

**Topics** (GitHub allows 20; these are the ones people actually search):

```
etl  data-engineering  benchmark  llm  large-language-models  agents
code-translation  pyspark  apache-spark  sql  data-migration  legacy-modernization
differential-testing  program-repair  semantic-equivalence  data-quality
llm-evaluation  ai-agents  dataflow  reproducible-research
```

## 3. Social preview

Settings → General → Social preview → upload `docs/social-preview.png`
(1280x640). This is the card that renders when the repo is shared on
LinkedIn, X, or Slack, and it is the single highest-leverage cosmetic item.

## 4. Repository settings

- Enable **Discussions** if you want task proposals and results reports from
  other people. Issues alone tends to discourage open-ended contributions.
- Enable **Issues** templates for two cases: "new task proposal" and
  "results report for another model".
- Branch protection on `main` requiring the CI check to pass. The CI runs the
  defect probes, so this literally prevents merging a task that does not
  discriminate.
- Pin the repo to your profile.

## 5. Release

Tag `v1.0.0` once the paper is submitted, and attach nothing: the repo itself
is the artifact. Use the release notes to state the model versions and the
measured numbers, so a reader landing on the release page sees what was
actually run.

Consider archiving the tagged release to Zenodo for a citable DOI. This is
worth doing before submission, because reviewers can then cite a fixed version
rather than a moving `main`.

## 6. Before making it public

- Confirm your employer's open-source and IP-assignment policy covers this.
- Re-run `grep -rn "sk-ant" .` and confirm the only hit is the documented
  placeholder in the README.
- Run the full test suite once more from a clean clone.
