"""Assemble index.html at the repository root (what GitHub Pages serves): the
house style shared with Anatomy of a Fill (doc/head.html, doc/tail.html), the
body, every source file inline and escaped, and the charts drawn from the
benchmark output. usage: python3 doc/build.py"""
import html, os, re, sys
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(H, "..")
sys.path.insert(0, H)
from charts import CHARTS

head = open(os.path.join(H, "head.html")).read()
head += """
<style>
/* port-opt-stack: note colours for this document's callouts */
#one-shape{--bar:var(--lav);background:var(--lav-t)!important}
#units{--bar:var(--apricot);background:var(--apricot-t)!important}
#handles{--bar:var(--euc);background:var(--euc-t)!important}
#pr-stall{--bar:var(--rose);background:var(--rose-t)!important}
#pr-backends{--bar:var(--mauve);background:var(--mauve-t)!important}
.code pre[data-lang] .c{color:var(--muted)}
/* Weights in Motion: sub-headings 1.1 … 1.7, and equations with labelled terms */
.part h5.bar{font-family:var(--sans);font-size:15.5px;font-weight:600;margin:22px 0 6px;color:var(--fg);clear:none}.part h5.bar .n{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--accent);margin-right:9px;font-weight:500}
.part h4.sub{font-family:var(--display);font-variant-caps:small-caps;letter-spacing:.03em;font-weight:600;font-size:19px;margin:22px 0 6px;color:var(--fg)}
.part h4.sub .n{font-family:"JetBrains Mono",monospace;font-variant-caps:normal;font-size:13px;color:var(--accent);margin-right:10px;letter-spacing:0}
.eqfig{position:relative;margin:14px 0 22px;color:var(--fg)}
.eqlabels{display:flex;flex-wrap:nowrap;justify-content:flex-start;gap:0;font-family:"Schibsted Grotesk",sans-serif;font-size:15px;color:var(--fg)}
.eql{white-space:nowrap;position:relative}
.eql i{display:inline-block;width:15px;height:15px;border-radius:50%;background:var(--c);opacity:.55;border:1.2px solid var(--fg);margin-left:7px;vertical-align:-2px}
.eqmath{font-size:1.75em;padding:30px 0;overflow-x:auto;overflow-y:hidden}
.eqmath svg rect[fill]{fill-opacity:.24}
.eqarrows{position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;overflow:visible}
</style>"""
body = open(os.path.join(H, "body.html")).read()
body = body.replace("OSQP is a solver built to be asked the same question over and over",
                    'OSQP<sup><a href="#ref-osqp">2</a></sup> is a solver built to be asked the same question over and over')
body = body.replace("OSQP is not the fastest solver for this problem from a cold start; Clarabel is,",
                    'OSQP is not the fastest solver for this problem from a cold start; Clarabel<sup><a href="#ref-clarabel">3</a></sup> is,')

def lc(p): return str(sum(1 for _ in open(os.path.join(ROOT, p))))
def sub_src(m):
    t = open(os.path.join(ROOT, m.group(1))).read().rstrip("\n")
    return html.escape(t, quote=False)
body = re.sub(r"\{\{LC:([^}]+)\}\}", lambda m: lc(m.group(1)), body)
body = re.sub(r"\{\{SRC:([^}]+)\}\}", sub_src, body)
body = re.sub(r"\{\{CHART:([^}]+)\}\}", lambda m: CHARTS[m.group(1)](), body)
assert "{{" not in body, body[body.index("{{"):body.index("{{") + 60]

# the original's scripts: MathJax, theme toggle, expand-all, q highlighting, copy buttons.
tail = open(os.path.join(H, "tail.html")).read()
tail = tail.replace('document.querySelectorAll(".code pre").forEach(function(pre){',
                    'document.querySelectorAll(".code pre").forEach(function(pre){\n    if(pre.dataset.lang) return;   /* C, shell and Python are not q */')
tail = tail.replace("localStorage.getItem('aof-theme')", "localStorage.getItem('wim-theme')").replace("localStorage.setItem('aof-theme',cur)", "localStorage.setItem('wim-theme',cur)")
assert "pre.dataset.lang" in tail and "MathJax" in tail
out = head + "\n" + body + "\n" + tail.replace("</body>", """
<script>
/* draw the arrows from each label's dot to its term, once MathJax has typeset */
function drawEq(){document.querySelectorAll('.eqfig').forEach(function(f,k){
  var s=f.querySelector('.eqarrows'),R=f.getBoundingClientRect(),o='',id='eqa'+k;
  s.setAttribute('viewBox','0 0 '+R.width+' '+R.height);
  f.querySelectorAll('.eql').forEach(function(l){            /* dots above sit right of their term, dots below left */
    var t=f.querySelector('.'+l.dataset.t),c=l.querySelector('i'); if(!t||!c) return;
    l.style.left='0px'; var a=c.getBoundingClientRect(),b=t.getBoundingClientRect();
    l.style.left=(b.left+b.width/2+(l.closest('.top')?36:-36)-(a.left+a.width/2))+'px';});
  f.querySelectorAll('.eql').forEach(function(l){
    var t=f.querySelector('.'+l.dataset.t),c=l.querySelector('i'); if(!t||!c) return;
    var a=c.getBoundingClientRect(),b=t.getBoundingClientRect(),up=!!l.closest('.top');
    var x1=a.left+a.width/2-R.left,x2=b.left+b.width/2-R.left;
    var y1=up?a.bottom-R.top:a.top-R.top, y2=up?b.top-R.top-3:b.bottom-R.top+3, m=(y1+y2)/2;
    o+='<path d="M'+x1+' '+y1+' C'+x1+' '+m+','+x2+' '+m+','+x2+' '+y2+'" fill="none" stroke="currentColor" stroke-width="1.3" marker-end="url(#'+id+')"/>';});
  s.innerHTML='<defs><marker id="'+id+'" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="currentColor"/></marker></defs>'+o;});}
(function w(){ if(window.MathJax&&MathJax.startup&&MathJax.startup.promise){ MathJax.startup.promise.then(drawEq);
  if(document.fonts&&document.fonts.ready) document.fonts.ready.then(function(){setTimeout(drawEq,50)}); } else setTimeout(w,100); })();
window.addEventListener('resize',drawEq);
document.querySelectorAll('.eqmath').forEach(function(m){m.addEventListener('scroll',drawEq)});
</script>\n</body>""")
open(os.path.join(ROOT, "index.html"), "w").write(out)
print("wrote index.html", len(out.split("\n")), "lines", len(out) // 1024, "KB")
