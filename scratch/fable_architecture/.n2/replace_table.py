from pathlib import Path

rep = Path('scratch/fable_architecture/A11_PROTECTED_AND_LINEAGE.md')
tab = Path('scratch/fable_architecture/.n2/lineage_table.md').read_text(encoding='utf-8').strip()
t = rep.read_text(encoding='utf-8')
head = '| Run | Config | Start came from | Parent (parent best J) | First valid J | Seeded? | Evidence |'
start = t.index(head)
end = t.index('\n\n## Verdict against', start)
new = t[:start] + tab + t[end:]
rep.write_text(new, encoding='utf-8')
print('replaced; report bytes', rep.stat().st_size)
