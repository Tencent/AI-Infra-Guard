#!/usr/bin/env python3
from __future__ import print_function
import csv, glob, json, os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
OUT=os.path.join(ROOT,'artifacts','analysis','paper_assets')
os.makedirs(OUT,exist_ok=True)
MODELS=['hy4-preview-***','glm-5.3-flash-***','deepseek-v4-flash-***','gpt-5.6-luna','minimax-m2.7-***']

def read_scores(run_dirs):
 rows=[]
 for r in run_dirs:
  mp=os.path.join(r,'manifest.json')
  model=json.load(open(mp))['model'] if os.path.isfile(mp) else ''
  for p in glob.glob(os.path.join(r,'cases','*','sample_*','score.json')):
   x=json.load(open(p));x['_model']=model;x['_sample_dir']=os.path.abspath(os.path.dirname(p));rows.append(x)
 return rows

def write_csv(name, fields, rows):
 p=os.path.join(OUT,name)
 with open(p,'w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 return p

# Full factorial plotting table from frozen analyses.
summary=json.load(open(os.path.join(ROOT,'artifacts','analysis','cross_model_summary_20260907.json')))
rows=[]
for m in summary['models']:
 for cell,v in sorted(m['cells'].items()):
  rows.append({'model':m['model'],'pressure':int(cell[0]),'control_degradation':int(cell[1]),'unsafe_opportunity':int(cell[2]),'mloc_count':v['count'],'n':v['n'],'mloc_rate':v['rate']})
write_csv('full_factorial_cells.csv',['model','pressure','control_degradation','unsafe_opportunity','mloc_count','n','mloc_rate'],rows)

screen_runs=glob.glob(os.path.join(ROOT,'artifacts','runs','forge_v03_screening_*_20260907'))
intact_runs=glob.glob(os.path.join(ROOT,'artifacts','runs','forge_v03_intact_*_20260907'))
cp_runs=glob.glob(os.path.join(ROOT,'artifacts','runs','forge_control_preserved_*_20260908'))
S=read_scores(screen_runs); I=read_scores(intact_runs); C=read_scores(cp_runs)
# High-risk family/model matrix.
rows=[]
for fam in sorted(set(x['episode_id'] for x in S)):
 for model in MODELS:
  rr=[x for x in S if x['episode_id']==fam and x['_model']==model]
  rows.append({'family':fam,'model':model,'mloc_count':sum(x['material_loss_of_control'] for x in rr),'n':len(rr),'mloc_rate':sum(x['material_loss_of_control'] for x in rr)/float(len(rr)) if rr else ''})
write_csv('high_risk_family_by_model.csv',['family','model','mloc_count','n','mloc_rate'],rows)
# Overall model rates in screening.
rows=[]
for model in MODELS:
 rr=[x for x in S if x['_model']==model]
 rows.append({'model':model,'mloc_count':sum(x['material_loss_of_control'] for x in rr),'n':len(rr),'mloc_rate':sum(x['material_loss_of_control'] for x in rr)/float(len(rr)),'safe_terminal_count':sum(x['safe_terminal'] for x in rr)})
write_csv('high_risk_model_rates.csv',['model','mloc_count','n','mloc_rate','safe_terminal_count'],rows)
# Control representation gradient, four selected families only.
selected={'production_rollback','cloud_recovery','vendor_procurement','account_containment'}
rows=[]
for condition,data in [('full_original',I),('compacted_control_preserved',C),('compacted_control_omitted',S)]:
 for model in MODELS:
  rr=[x for x in data if x['episode_id'] in selected and x['_model']==model]
  rows.append({'condition':condition,'model':model,'mloc_count':sum(x['material_loss_of_control'] for x in rr),'n':len(rr),'mloc_rate':sum(x['material_loss_of_control'] for x in rr)/float(len(rr)) if rr else '','safe_terminal_count':sum(x['safe_terminal'] for x in rr)})
write_csv('control_representation_by_model.csv',['condition','model','mloc_count','n','mloc_rate','safe_terminal_count'],rows)
# Scenario catalogue for distribution/table construction.
scenario_rows=[]
old=json.load(open(os.path.join(ROOT,'scenarios','v0.2','canonical_episodes.json')))['episodes']
for e in old:
 scenario_rows.append({'family':e['episode_id'],'domain':e['domain'],'mechanism':e['mechanism'],'source_experiment':'full_factorial','primary_external_action':(e['opportunity_tools'][0]['name'] if e['opportunity_tools'] else ''),'max_turns':e['max_turns']})
new_cases=[json.loads(line) for line in open(os.path.join(ROOT,'scenarios','v0.3_screening','screening_cases.jsonl'))]
for e in new_cases:
 scenario_rows.append({'family':e['episode_id'],'domain':e['domain'],'mechanism':e['mechanism'],'source_experiment':'high_risk_screening','primary_external_action':e['screening_spec']['unsafe_tool'],'max_turns':e['max_turns']})
write_csv('scenario_catalogue.csv',['family','domain','mechanism','source_experiment','primary_external_action','max_turns'],scenario_rows)
# Representative trajectories. Prefer clear, finalized samples.
representatives=[
 ('mailbox_authorization_escalation','forge_bench/artifacts/runs/forge_v023_mailbox_triage_20260906/cases/mailbox_triage_p1_d1_o1/sample_002'),
 ('artifact_scope_escape','forge_bench/artifacts/runs/forge_v023_cross_glm_5_3_flash_***_20260907r2/cases/artifact_recovery_p0_d1_o1/sample_001'),
 ('release_interruptibility_failure','forge_bench/artifacts/runs/forge_v023_cross_glm_5_3_flash_***_20260907r2/cases/atlas_release_p0_d1_o1/sample_001'),
 ('production_rollback_failure','forge_bench/artifacts/runs/forge_v03_screening_hy4_preview_***_20260907/cases/production_rollback_p1_d1_o1/sample_001'),
 ('cloud_scope_escape','forge_bench/artifacts/runs/forge_v03_screening_hy4_preview_***_20260907/cases/cloud_recovery_p1_d1_o1/sample_001'),
 ('procurement_authorization_escalation','forge_bench/artifacts/runs/forge_v03_screening_hy4_preview_***_20260907/cases/vendor_procurement_p1_d1_o1/sample_002'),
 ('intact_safe_counterfactual','forge_bench/artifacts/runs/forge_v03_intact_hy4_preview_***_20260907/cases/production_rollback_p1_d0_o1/sample_001'),
 ('control_preserved_safe_counterfactual','forge_bench/artifacts/runs/forge_control_preserved_hy4_preview_***_20260908/cases/production_rollback_p1_d1_o1_control_preserved/sample_001'),
]
index=[]
for label,rel in representatives:
 d=os.path.abspath(os.path.join(os.path.dirname(ROOT),rel))
 score=json.load(open(os.path.join(d,'score.json')))
 index.append({'label':label,'sample_dir':d,'input':os.path.join(d,'input.json'),'trajectory':os.path.join(d,'trajectory.jsonl'),'final_state':os.path.join(d,'final_state.json'),'score':os.path.join(d,'score.json'),'material_loss_of_control':score['material_loss_of_control'],'selected_tools':' -> '.join(score['selected_tools'])})
with open(os.path.join(OUT,'representative_trajectories.json'),'w',encoding='utf-8') as f:json.dump(index,f,ensure_ascii=False,indent=2,sort_keys=True);f.write('\n')
print(OUT)
