import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
INK='#0b0b0b'; SEC='#52514e'; MUT='#898781'; GRID='#e1e0d9'; BG='#ffffff'
C1,C2,C3='#2a78d6','#eb6834','#1baf7a'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.edgecolor':MUT,'axes.labelcolor':SEC,
 'xtick.color':SEC,'ytick.color':SEC,'axes.titlesize':10,'axes.titleweight':'bold','axes.titlecolor':INK})
fig,(a,b)=plt.subplots(1,2,figsize=(10,4.8),gridspec_kw={'width_ratios':[1,1.15]})
fig.patch.set_facecolor(BG)
# (a) Study A, values from studyA_headline.md
models=['E2B','E4B','12B','31B']; x=range(4)
G0=[32.66,36.88,40.00,46.41]; G1=[57.27,64.84,91.56,96.41]; G2=[58.44,61.72,91.25,96.09]; G3=[46.72,54.61,89.84,93.75]; G4=[50.08,53.98,87.66,92.81]
for ys,c,lab,ls in [(G1,C1,'G1 true, real names','-'),(G2,C3,'G2 true, neutral','--'),(G3,C2,'G3 swapped, real','-'),(G4,'#8a5cc7','G4 swapped, neutral','--'),(G0,MUT,'G0 no graph',':')]:
    a.plot(x,ys,color=c,lw=2,ls=ls,marker='o',ms=5,label=lab,markeredgecolor=BG,markeredgewidth=1)
a.axhline(25,color=MUT,lw=1,ls=(0,(2,2)))
a.text(-0.15,26.2,'chance (25%)',va='bottom',ha='left',color=MUT,fontsize=7.5)
a.set_xticks(list(x)); a.set_xticklabels(models); a.set_ylim(15,127); a.set_xlim(-0.2,3.2); a.set_yticks(range(20,101,20))
a.set_ylabel('Accuracy (%)'); a.set_yticklabels([str(v) for v in range(20,101,20)]); a.set_title('(a) Study A: the shown graph drives accuracy',loc='left')
a.grid(axis='y',color=GRID,lw=0.6); a.set_axisbelow(True)
for s in ['top','right']: a.spines[s].set_visible(False)
a.legend(frameon=False,fontsize=7.5,loc='upper left',labelcolor=SEC,ncol=2,columnspacing=1.0,handlelength=2.2)
# (b) Study B forest, values from studyB_headline.md (stratified 95% CI)
rows=[('B1 real − renamed names',8.02,4.92,11.12,True),
      ('B2 true − rewired (renamed, anchored)',-2.16,-4.17,-0.29,True),
      ('B3 graph value, renamed − real',-2.30,-5.03,0.43,False),
      ('B4 names effect, 31B − E4B',1.35,-6.31,9.01,False),
      ('B5 scorer, true − rewired',-1.15,-2.87,0.00,False),
      ('Within-module rewiring (expl.)',-0.72,-2.87,1.44,False)]
ctrl=[('Equal density: true − random',(-0.3,-1.4,0.6),(0.3,-2.0,2.6)),
      ('Equal sparsity: thinned true − rewired',(0.9,-0.3,2.3),(-1.4,-3.2,0.3)),
      ('With hint: true − rewired (19 tasks)',(-5.3,-18.4,5.3),(-2.6,-7.9,0.0)),
      ('JSON vs line format (Study A, G1)',(1.1,-0.2,2.3),(-0.2,-2.7,2.2))]
n=len(rows)+len(ctrl)+1
b.axvspan(-5,5,color='#eef3fb',zorder=0)
b.axvline(0,color=MUT,lw=1,zorder=1)
for i,(lab,e,lo,hi,conf) in enumerate(rows):
    y=n-1-i
    b.plot([lo,hi],[y,y],color=INK,lw=2,solid_capstyle='round',zorder=2)
    b.plot(e,y,'o',ms=7,color=INK if conf else BG,markeredgecolor=INK,markeredgewidth=1.6,zorder=3)
    b.text(hi+0.4,y,f'{e:+.1f}'.replace('-','−'),va='center',ha='left',fontsize=8,color=SEC)
XMIN=-8
labels=[r[0] for r in rows]+['Exploratory controls (Sections 4.3, 5)']+[c[0] for c in ctrl]
for j,(lab,m31,m4) in enumerate(ctrl):
    y=n-1-(len(rows)+1+j)
    for (e,lo,hi),dy,mk in [(m31,0.14,'s'),(m4,-0.14,'^')]:
        lo2=max(lo,XMIN+0.05)
        b.plot([lo2,hi],[y+dy,y+dy],color=SEC,lw=1.6,solid_capstyle='round',zorder=2)
        if lo<XMIN: b.annotate('',xy=(XMIN+0.05,y+dy),xytext=(XMIN+0.9,y+dy),arrowprops=dict(arrowstyle='->',color=SEC,lw=1.2))
        b.plot(e,y+dy,mk,ms=6,color=BG,markeredgecolor=SEC,markeredgewidth=1.4,zorder=3)
yh=n-1-len(rows)
b.axhline(yh+0.5,color=GRID,lw=0.8)
b.set_yticks(range(n)); b.set_yticklabels(labels[::-1],fontsize=8)
b.get_yticklabels()[n-1-len(rows)].set_fontweight('bold')
b.set_xlim(-8,13); b.set_ylim(-0.75,n-0.1)
b.set_xlabel('Acc@1 difference, points (95% CI)')
b.text(-4.8,-0.6,'±5-point equivalence band',ha='left',va='bottom',fontsize=7,color=SEC)
b.set_title('(b) Study B: names help, true edges do not',loc='left')
for s in ['top','right','left']: b.spines[s].set_visible(False)
b.tick_params(axis='y',length=0)
b.set_xticks([-5,0,5,10]); b.set_xticklabels(['−5','0','+5','+10'])
b.text(13,n-0.45,'filled: confirmatory; open: secondary or exploratory',ha='right',va='bottom',fontsize=7,color=MUT)
b.text(13,-0.6,'controls: square 31B, triangle E4B',ha='right',va='bottom',fontsize=7,color=MUT)
fig.tight_layout()
fig.savefig('figure1.png',dpi=220,facecolor=BG)
