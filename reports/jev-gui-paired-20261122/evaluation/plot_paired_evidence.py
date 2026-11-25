"""Draw version-separated figures from a verified paired report."""

import argparse
from pathlib import Path
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle

from collect import HERE, VERSIONS, read, save, sha
from link import verify
from summarize import CONDITIONS


CONDITION_NAMES = dict(zip(CONDITIONS, ('Normal', 'Missing', 'White', 'Stale in transit', 'Buttons only')))
VERSION_NAMES = {'BF16-original':'Original BF16', 'BF16-envelope':'BF16 with action compatibility',
                 'NF4':'NF4 with BF16 compute'}
INK, MUTED, RULE = '#1d2939', '#4f6074', '#d6dfe7'
BLEED, RESTORE, MIRAGE = '#a44029', '#006d62', '#496595'


def header(fig, title, subtitle, progress):
    fig.text(.06,.96,title,ha='left',va='top',fontsize=13,fontweight='bold',color=INK)
    fig.text(.06,.90,subtitle,ha='left',va='top',fontsize=8,color=MUTED)
    if progress:
        fig.text(.94,.96,progress,ha='right',va='top',fontsize=8,color=BLEED,fontweight='bold')


def tint(color, share):
    base = to_rgb(color)
    blend = .07 + .25*share
    return tuple(1-(1-c)*blend for c in base)


def mechanism(groups, progress):
    cols = [('off','injected_change_reached_actor_actual_forward',BLEED),
            ('on','injected_change_reached_actor_actual_forward',BLEED),
            ('on','independently_normal_image_reached_actor_after_loop',RESTORE)]
    conditions=CONDITIONS[1:]
    fig=plt.figure(figsize=(8.9,4.6),facecolor='white')
    header(fig,'What reached the main model?',
           'Real first forwards and same-decision recovery, by main-model version',progress)
    axes=fig.subplots(1,len(VERSIONS),sharey=True,squeeze=False)[0]
    fig.subplots_adjust(left=.18,right=.95,bottom=.30,top=.76,wspace=.12)
    for j,(version,ax) in enumerate(zip(VERSIONS,axes,strict=True)):
        ax.set(xlim=(0,len(cols)),ylim=(len(conditions),0))
        for y, cond in enumerate(conditions):
            group=groups.get((version,cond))
            for x,(arm,key,color) in enumerate(cols):
                denom=group[arm]['attempts_with_real_injected_change'] if group else 0
                count=group[arm][key] if group else 0
                assert 0 <= count <= denom
                fill=tint(color,count/denom) if denom else '#f0f3f6'
                ax.add_patch(Rectangle((x+.04,y+.08),.92,.84,facecolor=fill,edgecolor='none'))
                ax.text(x+.5,y+.5,f'{count}/{denom}' if denom else '—',ha='center',va='center',
                        color=color if denom else MUTED,fontsize=11,fontweight='bold' if denom else 'normal')
        ax.set_title(VERSION_NAMES[version],color=INK,fontsize=8.5,pad=9)
        ax.set_xticks([.5,1.5,2.5],('Off: bad','On: bad','On: restored'),fontsize=7,color=MUTED)
        ax.set_yticks([i+.5 for i in range(len(conditions))],[CONDITION_NAMES[c] for c in conditions],
                      fontsize=8,color=INK)
        ax.tick_params(length=0,labelleft=j==0,pad=4)
        for s in ax.spines.values(): s.set_visible(False)
    fig.text(.06,.18,'Each cell: verified events / arms with an actual altered or missing initial image.',
             fontsize=8,color=INK)
    fig.text(.06,.12,'Restored = a newly captured, independently usable frame reached the same decision’s actual first forward.',
             fontsize=8,color=MUTED)
    fig.text(.06,.06,'— no actual exposure observed. One-shot injections; in-transit stale replacement does not model a correctly signed early capture.',
             fontsize=7.5,color=MUTED)
    return fig


def paired(groups, progress):
    rows=[]
    for v in VERSIONS:
        present=[(c,groups[v,c]) for c in CONDITIONS if (v,c) in groups]
        if present:
            rows.append((v,None,None))
            rows.extend((v,c,g['paired']) for c,g in present)
    n=len(rows)
    fig=plt.figure(figsize=(8.9,6.3),facecolor='white')
    header(fig,'Paired task outcomes and Mirage',
           'Defense on minus defense off, in percentage points. Each panel uses both-scored pairs.',progress)
    axes=fig.subplots(1,2,sharey=True,squeeze=False)[0]
    fig.subplots_adjust(left=.31,right=.91,bottom=.19,top=.79,wspace=.36)
    for ax,title in zip(axes,('Official task success','Trajectory Mirage'),strict=True):
        ax.set(xlim=(-105,105),ylim=(n-.4,-.6))
        ax.set_xticks([-100,-50,0,50,100])
        ax.tick_params(axis='x',labelsize=8,colors=MUTED)
        ax.tick_params(axis='y',left=False,labelleft=False)
        ax.axvline(0,color=RULE,lw=1,zorder=0)
        ax.grid(axis='x',color=RULE,alpha=.5,lw=.5,zorder=0)
        ax.set_title(title,fontsize=10,fontweight='bold',color=INK,pad=9)
        for s in ('right','left','top'): ax.spines[s].set_visible(False)
        ax.spines['bottom'].set_color(RULE)
    left,right=axes
    for y,(version,condition,p) in enumerate(rows):
        if not condition:
            left.text(-.04,y,VERSION_NAMES[version],ha='right',va='center',
                      transform=left.get_yaxis_transform(),fontsize=8,color=INK,fontweight='bold')
            continue
        label=f"{CONDITION_NAMES[condition]}  ({p['official_comparable_pairs']}/{p['assigned_pairs']})"
        left.text(-.04,y,label,ha='right',va='center',transform=left.get_yaxis_transform(),fontsize=8,color=MUTED)
        value=p['official_mean_on_minus_off']
        lo,hi=p['all_both_scored_pairs_Mirage']['task_weighted_on_minus_off_bounds']
        if value is None:
            for a in axes: a.text(0,y,'—',ha='center',va='center',fontsize=9,color=MUTED)
            continue
        rng=p['official_task_cluster_percentile_95_interval_descriptive']
        if rng: left.hlines(y,100*rng[0],100*rng[1],color=RESTORE,lw=1.8,zorder=2)
        left.scatter(100*value,y,s=16,color=RESTORE,zorder=3)
        assert lo is not None and lo<=hi
        if lo==hi:
            right.scatter(100*lo,y,s=16,color=MIRAGE,zorder=3)
        else:
            right.hlines(y,100*lo,100*hi,color=MIRAGE,lw=1.8,zorder=2)
            right.scatter([100*lo,100*hi],[y,y],s=9,color=MIRAGE,zorder=3)
    fig.text(.06,.105,'Counts in parentheses: both scored / assigned. Official lines show descriptive 95% task-resampling intervals.',
             fontsize=8,color=INK)
    fig.text(.06,.055,'Mirage lines are uncertainty bounds for unresolved labels, not confidence intervals; higher Mirage is worse.',
             fontsize=8,color=MUTED)
    return fig


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('report',type=Path)
    p.add_argument('--progress',action='store_true',help='Allow the figures to show a watermarked partial result.')
    a=p.parse_args()
    verify(a.report)
    data=read(a.report/'condition-by-version.json')
    totals=data['overall_counts_only_no_pooled_effect_estimate']
    if not data['is_final'] and not a.progress:
        p.error('the report is partial; use --progress for a clearly marked internal view')
    progress=None if data['is_final'] else f"INTERIM   {totals['sealed_terminals']} / {totals['assigned']}"
    groups={(g['version'],g['condition']):g for g in data['separate_version_condition_results']}
    out=HERE/'evidence-figures'/str(time.time_ns());out.mkdir(parents=True,exist_ok=False)
    with plt.rc_context({'font.family':'DejaVu Sans','svg.fonttype':'none','axes.unicode_minus':True}):
        for name,build in (('mechanism',mechanism),('paired-effects',paired)):
            fig=build(groups,progress)
            fig.savefig(out/(name+'.svg'),facecolor='white')
            fig.savefig(out/(name+'.png'),dpi=160,facecolor='white')
            plt.close(fig)
    save(out/'index.json',{'summary_report_seal_sha256':sha(a.report/'seal.json'),
                          'summary_report':str(a.report.resolve()), 'interim':progress is not None,
                          'plotter_sha256':sha(Path(__file__)),'no_pooled_effect':True})
    save(out/'seal.json',{f.name:sha(f) for f in out.iterdir() if f.is_file()})
    print(out)


if __name__=='__main__':
    main()
