"""Statement and branch coverage of each oracle under the generated corpora.

    python experiments/oracle_coverage.py out.json      (needs: pip install coverage)

See results/coverage.md for the figures reported in the paper.
"""
import sys,glob,os,json,coverage
sys.path.insert(0,'.')
rows=[]
for d in sorted(glob.glob('tasks/*/')):
    ref=os.path.abspath(os.path.join(d,'reference.py'))
    def run(seeds):
        cov=coverage.Coverage(branch=True,include=[ref],data_file=None)
        cov.start()
        from etl_transbench.harness import Task
        t=Task.load(d)
        n=0
        for s in seeds:
            c=t.corpus(s); n+=sum(len(v) for v in c.values()); t.reference(c)
        cov.stop()
        an=cov._analyze(ref)
        nums=an.numbers
        return nums.n_statements,nums.n_executed,nums.n_branches,nums.n_executed_branches,n//len(seeds)
    a=run([11,23,47]); b=run([101,211,307,401,503])
    meta=json.load(open(d+'task.json'))
    rows.append(dict(task=meta['id'],cat=meta['category'],set=meta.get('set','core'),stmts=a[0],line_dev=a[1]/a[0],br=a[2],br_dev=(a[3]/a[2] if a[2] else 1.0),line_ho=b[1]/b[0],br_ho=(b[3]/b[2] if b[2] else 1.0),rows_per_corpus=a[4]))
json.dump(rows,open(sys.argv[1],'w'),indent=1)
import statistics as st
print(len(rows),'line min/med',min(r['line_dev'] for r in rows),st.median(r['line_dev'] for r in rows),'branch min/med/mean',min(r['br_dev'] for r in rows),st.median(r['br_dev'] for r in rows),st.mean(r['br_dev'] for r in rows))
for r in rows:
    if r['br_dev']<1 or r['line_dev']<1: print(r)
print('rows/corpus',min(r['rows_per_corpus'] for r in rows),st.median(r['rows_per_corpus'] for r in rows),max(r['rows_per_corpus'] for r in rows))
