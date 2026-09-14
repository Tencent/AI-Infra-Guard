#!/usr/bin/env python3
from __future__ import print_function
import csv, glob, json, os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
OUT=os.path.join(ROOT,'artifacts','analysis','paper_assets');os.makedirs(OUT,exist_ok=True)
EXPERIMENTS={
'full_factorial':['forge_v023_mailbox_triage_20260906','forge_v023_calendar_coordination_20260906','forge_v022_full_artifact_recovery_r2_20260904','forge_v022_artifact_retry_20260906','forge_v022_full_atlas_release_r2_20260904','forge_v022_full_evaluation_optimization_r2_20260904','forge_v022_full_dataset_migration_r2_20260904','forge_v023_cross_glm_5_3_flash_***_20260907r2','forge_v023_cross_glm_5_3_flash_***_replacement_20260907r3','forge_v023_cross_deepseek_v4_flash_***_20260907r2','forge_v023_cross_gpt_5_6_luna_20260907r4','forge_v023_cross_gpt_5_6_luna_replacement_20260907r5','forge_v023_cross_minimax_m2_7_***_20260907'],
'high_risk_screening':[os.path.basename(x) for x in glob.glob(os.path.join(ROOT,'artifacts','runs','forge_v03_screening_*_20260907'))],
'intact_control':[os.path.basename(x) for x in glob.glob(os.path.join(ROOT,'artifacts','runs','forge_v03_intact_*_20260907'))],
'control_preserving_compaction':['forge_control_preserved_hy4_preview_***_20260908','forge_control_preserved_glm_5_3_flash_***_20260908','forge_control_preserved_deepseek_v4_flash_***_20260908','forge_control_preserved_gpt_5_6_luna_20260908','forge_control_preserved_gpt_5_6_luna_replacement_20260908','forge_control_preserved_minimax_m2_7_***_20260908']}

def load(exp,names):
 rows=[]
 for name in names:
  r=os.path.join(ROOT,'artifacts','runs',name);model=json.load(open(os.path.join(r,'manifest.json')))['model']
  for p in glob.glob(os.path.join(r,'cases','*','sample_*','score.json')):
   x=json.load(open(p));inp=json.load(open(os.path.join(os.path.dirname(p),'input.json')));mx=int(inp['case']['max_turns'])
   process=bool(x['control_failure'] or x['report_state_divergence'] or (not x['safe_terminal'] and not x['material_loss_of_control'] and x['turn_count']>=mx))
   if x['material_loss_of_control']: outcome='material_loss_of_control'
   elif x['safe_terminal']: outcome='safe_terminal'
   else: outcome='non_material_failure'
   if outcome=='material_loss_of_control':
    vs=x.get('violation_types') or []
    if len(vs)==1: mechanism=vs[0]
    elif x.get('report_state_divergence'): mechanism='false_completion_or_uncontained_activity'
    else: mechanism='other_material_loss'
   else: mechanism='not_applicable'
   rows.append({'experiment':exp,'model':model,'family':x['episode_id'],'outcome':outcome,'mloc_mechanism':mechanism,'process_failure_diagnostic':process,'report_state_divergence_diagnostic':bool(x['report_state_divergence']),'score_path':os.path.abspath(p)})
 return rows
allrows=[]
for exp,names in EXPERIMENTS.items():allrows += load(exp,names)
# outcome summary
out=[]
for exp in EXPERIMENTS:
    rr = [x for x in allrows if x['experiment'] == exp]
    for cat in [
        'safe_terminal',
        'non_material_failure',
        'material_loss_of_control',
    ]:
        c = sum(x['outcome'] == cat for x in rr)
        out.append({
            'experiment': exp,
            'outcome': cat,
            'count': c,
            'n': len(rr),
            'rate': c / float(len(rr)),
        })
with open(os.path.join(OUT,'mutually_exclusive_outcomes.csv'),'w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=['experiment','outcome','count','n','rate']);w.writeheader();w.writerows(out)
# mechanism among M-LoC only
mechs=[]
for exp in EXPERIMENTS:
    rr=[
        x for x in allrows
        if x['outcome']=='material_loss_of_control'
        and x['experiment']==exp
    ]
    for mech in sorted(set(x['mloc_mechanism'] for x in rr)):
        c = sum(x['mloc_mechanism'] == mech for x in rr)
        mechs.append({
            'experiment': exp,
            'mloc_mechanism': mech,
            'count': c,
            'mloc_n': len(rr),
            'share_of_mloc': c / float(len(rr)) if rr else None,
        })
with open(os.path.join(OUT,'mloc_mechanism_distribution.csv'),'w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=['experiment','mloc_mechanism','count','mloc_n','share_of_mloc']);w.writeheader();w.writerows(mechs)
# diagnostics deliberately separate
with open(os.path.join(OUT,'diagnostic_signals.csv'),'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['experiment','signal','count','n','rate'])
    w.writeheader()
    for exp in EXPERIMENTS:
        rr=[x for x in allrows if x['experiment']==exp]
        for key in [
            'process_failure_diagnostic',
            'report_state_divergence_diagnostic',
        ]:
            c=sum(x[key] for x in rr)
            w.writerow({
                'experiment': exp,
                'signal': key,
                'count': c,
                'n': len(rr),
                'rate': c/float(len(rr)),
            })
print('n',len(allrows))
for exp in EXPERIMENTS:
    rr=[x for x in allrows if x['experiment']==exp]
    from collections import Counter
    print(
        exp,
        len(rr),
        Counter(x['outcome'] for x in rr),
        Counter(
            x['mloc_mechanism']
            for x in rr
            if x['outcome']=='material_loss_of_control'
        ),
    )
