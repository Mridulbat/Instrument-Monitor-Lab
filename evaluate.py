"""Regenerate default numerical evidence. Run from the project root."""
import csv
import json
from pathlib import Path
from src.engine import RUN

root = Path(__file__).resolve().parent
result = RUN({})
(root/'examples'/'default-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
with (root/'examples'/'default-samples.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=list(result['rows'][0]))
    writer.writeheader();writer.writerows(result['rows'])
print(json.dumps(result['metrics'],indent=2))
