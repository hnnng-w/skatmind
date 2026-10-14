"""Exercise the actual scoped enhancement with controlled preparation responses."""

import json
import shutil
import subprocess
from importlib.resources import files

import pytest

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Optional Node script runner unavailable")

HARNESS = r"""
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const submits=[], requests=[], installed=[], scrolls=[], removed=[];
const scope='a'.repeat(64);
const context={console, URLSearchParams, scrollX:0, scrollY:900};
const control=(name,value,type='text')=>({name,value,type,disabled:false,checked:false,
  tagName:type==='select'?'SELECT':'INPUT'});
function form(kind,decision,token){
  const route=kind==='selection'?'/matches/select-decision':kind==='rollout'?
    '/matches/review-whole-game':'/matches/api/v1/analysis';
  const elements=kind==='selection'?[control('decision_index',decision,'select'),
    control('selection_context',token,'hidden'),control('managed_handle','handle','hidden'),
    control('expected_revision','2','hidden'),control('match_position','2','hidden'),
    control('return_to','/matches/review/2','hidden')]:[
    control('decision_index',decision,'hidden'),control('visible_decision_index',decision,'hidden'),
    ...(kind==='rollout'?[control('objective','complete_settlement','select'),
      control('analysis_matadors',''),control('requested_worlds','100'),control('random_seed','0')]:
      [control('recommendation_method','immediate_expected_value','select'),
       control('immediate_sample_count','100'),control('use_profile_presets','on','checkbox')])];
  const button=control('','', 'submit');button.hidden=false;elements.push(button);
  const fields=elements.filter(e=>!['hidden','submit'].includes(e.type)).map(e=>e.name);
  const f={kind,elements,button,hidden:false,action:'http://local'+route,
    dataset:{languageForm:token+kind,preserveFields:fields.join(' '),
      preserveLimits:JSON.stringify(Object.fromEntries(fields.map(n=>[n,[2048,1]])))},
    getAttribute:()=>route,querySelector:s=>s==='[data-apply-decision]'?button:
      elements.find(e=>e.name===s.match(/name="([^"]+)"/)?.[1]),
    querySelectorAll:()=>elements.filter(e=>e.type==='hidden')};
  return f;
}
function page(decision,token='initial',source=scope,ready='true'){
  const s=form('selection',decision,token),r=form('rollout',decision,token),
    l=form('legacy',decision,token);
  const selector=s.elements[0];selector.handlers={};
  selector.addEventListener=(type,fn)=>selector.handlers[type]=fn;
  selector.getBoundingClientRect=()=>({top:430});
  selector.focus=()=>context.document.activeElement=selector;
  const details=[{open:false},{open:false},{open:false}];
  const body={forms:[r,l],hidden:true,contains:e=>[r,l,...r.elements,...l.elements].includes(e),
    querySelectorAll:q=>q.startsWith('form')?[r,l]:q==='details'?details:
      q.includes('visible_decision_index')?[r.elements[1],l.elements[1]]:[...r.elements,...l.elements],
    replaceWith:replacement=>{main.body=replacement;installed.push(replacement.forms[0].elements[0].value)}};
  const language={buttons:[control('language','de','submit'),control('language','en','submit')],
    token,querySelectorAll:()=>language.buttons,
    replaceWith:replacement=>context.language=replacement};
  const label={textContent:'Decision '+decision},status={hidden:true,textContent:''};
  const native=[{hidden:false},{hidden:true}];
  const root={dataset:{source,applied:decision,ready,loadingLabel:'loading',failedLabel:'failed'},
    body,selectorForm:s,label,status,querySelector:q=>q==='form[data-decision-selector]'?s:
      q==='[data-match-analysis-controls]'?root.body:q==='[data-selection-status]'?status:
      q==='[data-applied-decision]'?label:null,
    querySelectorAll:q=>q==='form[data-language-form]'?root.body.forms:
      q.includes('details')?details:native,setAttribute:()=>{}};
  const document={querySelector:q=>q==='[data-match-selection]'?root:
    q==='form.language-selector'?language:null};
  return {root,language,document};
}
const initial=page('1');const main=initial.root;
const summary={matches:()=>true,remove:()=>removed.push('summary')};
main.selectorForm.previousElementSibling={matches:()=>true,previousElementSibling:summary,
  remove:()=>{removed.push('anchor');main.selectorForm.previousElementSibling=null}};
const selector=main.selectorForm.elements[0];
const elem=(kind,name)=>main.body.forms.find(f=>f.kind===kind).elements.find(e=>e.name===name);
elem('rollout','analysis_matadors').value='2';elem('rollout','requested_worlds').value='1';
context.language=initial.language;
context.document={activeElement:selector,querySelector:q=>q==='form.language-selector'?context.language:null,
  addEventListener:(_type,fn)=>submits.push(fn),importNode:e=>e};
context.window=context;context.scrollTo=value=>scrolls.push(value);
context.FormData=class {
  constructor(f){this.entries=f.elements.filter(e=>e.name).map(e=>[e.name,e.value])}
  [Symbol.iterator](){return this.entries[Symbol.iterator]()}};
context.fetch=(url,options)=>new Promise((resolve,reject)=>
  requests.push({url,options,resolve,reject}));
context.DOMParser=class {parseFromString(raw){const p=JSON.parse(raw);return page(p.decision,
  p.token||'new',p.source||scope,p.ready||'true').document}};
if(input.unavailable)context.fetch=undefined;
if(input.nativeReady){main.selectorForm.hidden=true;main.body.hidden=false;}
vm.createContext(context);
const start=input.script.indexOf('function safePresentationValues(');
const end=input.script.indexOf('\ndocument.addEventListener("DOMContentLoaded"',start);
vm.runInContext(input.script.slice(start,end),context);
context.initializeMatchDecisionSelection(main);
const snapshot=()=>({visible:selector.value,applied:main.dataset.applied,ready:main.dataset.ready,
  matadors:elem('rollout','analysis_matadors').value,worlds:elem('rollout','requested_worlds').value,
  disabled:main.body.forms.map(f=>f.button.disabled),manual:!main.selectorForm.button.hidden,
  selectorHidden:main.selectorForm.hidden,controlsHidden:main.body.hidden,
  languageToken:context.language.token,formToken:main.selectorForm.dataset.languageForm,
  focus:context.document.activeElement===selector});
const submit=target=>{let prevented=false;for(const fn of submits)fn({target,
  preventDefault:()=>prevented=true,stopImmediatePropagation:()=>{}});return prevented};
const change=value=>{selector.value=value;selector.handlers.input();selector.handlers.change()};
const settle=()=>new Promise(resolve=>setImmediate(resolve));
async function answer(index,decision,extra={}){
  requests[index].resolve({ok:extra.ok!==false,text:async()=>JSON.stringify({decision,...extra})});
  await settle();await settle();
}
(async()=>{
  const result={initial:snapshot()};
  if(input.unavailable){process.stdout.write(JSON.stringify(result));return;}
  change('3');
  result.pending=snapshot();
  result.blocked=main.body.forms.map(submit);
  result.languageBlocked=submit(context.language);
  if(input.mode==='rapid'){
    change('1');
    result.beforeResponse=requests.length;
    await answer(0,'3',{token:'intermediate'});
    result.intermediate=snapshot();
    result.nextBinding=requests[1].options.body.get('selection_context');
    await answer(1,'1',{token:'latest'});
  }else if(input.mode==='preview'){
    selector.value='1';selector.handlers.input();
    await answer(0,'3');
  }else if(input.mode==='network'){
    requests[0].reject(Error('network'));await settle();
  }else if(input.mode==='foreign'){
    await answer(0,'3',{source:'foreign'});
  }else if(input.mode==='wrong'){
    await answer(0,'2');
  }else if(input.mode==='failure'){
    await answer(0,'1',{ok:false,ready:'false',token:'failed-context'});
    result.failedLanguageBlocked=submit(context.language);
    result.failedAnalysisBlocked=main.body.forms.map(submit);
  }else{
    await answer(0,'3',{token:'alex'});
    result.alex=snapshot();
    elem('rollout','analysis_matadors').value='1';elem('rollout','requested_worlds').value='2';
    change('1');await answer(1,'1',{token:'bea'});result.bea=snapshot();
    change('3');await answer(2,'3',{token:'alex-again'});
    result.readyBlocked=main.body.forms.map(submit);
  }
  result.final=snapshot();result.installed=installed;result.scrolls=scrolls;
  result.removed=removed;
  result.requests=requests.map(r=>({url:r.url,body:Object.fromEntries(r.options.body),
    method:r.options.method,
    headers:r.options.headers}));
  process.stdout.write(JSON.stringify(result));
})().catch(error=>{console.error(error);process.exitCode=1});
"""


def run_script(**options):
    raw = files("skatmind.app_web").joinpath("assets/workflow.js").read_text()
    result = subprocess.run([NODE, "-e", HARNESS], input=json.dumps({"script": raw, **options}),
        text=True, capture_output=True, check=True, timeout=15)
    return json.loads(result.stdout)


def test_loading_blocks_both_actions_without_queuing_and_restores_decision_local_values():
    result = run_script()
    assert result["blocked"] == [True, True] and result["languageBlocked"]
    assert result["pending"]["visible"] == "3" and result["pending"]["applied"] == "1"
    assert result["pending"]["disabled"] == [True, True]
    assert result["alex"]["matadors"] == "" and result["alex"]["worlds"] == "100"
    assert result["bea"]["matadors"] == "2" and result["bea"]["worlds"] == "1"
    assert result["final"]["matadors"] == "1" and result["final"]["worlds"] == "2"
    assert result["final"]["languageToken"] == "alex-again"
    assert result["final"]["formToken"] == "alex-againselection"
    assert result["readyBlocked"] == [False, False] and result["final"]["focus"]
    assert result["removed"] == ["anchor", "summary"]
    assert all(row["url"] == "http://local/matches/select-decision" and row["method"] == "POST"
               and row["headers"] == {"X-SkatMind-Selection": "prepare"}
               for row in result["requests"])
    assert all(set(row["body"]) == {"decision_index", "selection_context", "managed_handle",
        "expected_revision", "match_position", "return_to"} for row in result["requests"])
    assert all(row == {"left": 0, "top": 900, "behavior": "instant"} for row in result["scrolls"])


def test_rapid_a_b_a_never_installs_late_b_and_uses_returned_transport_binding():
    result = run_script(mode="rapid")
    assert result["beforeResponse"] == 1
    assert result["intermediate"]["applied"] == "1"
    assert result["intermediate"]["ready"] == "false"
    assert result["installed"] == ["1"]
    assert result["nextBinding"] == "intermediate"
    assert result["final"]["matadors"] == "2"
    assert result["final"]["ready"] == "true"


def test_uncommitted_input_preview_does_not_queue_a_preparation_request():
    result = run_script(mode="preview")
    assert len(result["requests"]) == 1 and result["installed"] == []
    assert result["final"]["ready"] == "false" and result["final"]["manual"]


@pytest.mark.parametrize("mode", ("network", "foreign", "wrong"))
def test_failed_or_inconsistent_response_cannot_reenable_old_context_or_retry(mode):
    result = run_script(mode=mode)
    assert result["final"]["ready"] == "false" and result["final"]["manual"]
    assert result["final"]["visible"] == "3" and result["installed"] == []
    assert result["final"]["disabled"] == [True, True]
    assert len(result["requests"]) == 1


def test_current_source_preparation_error_keeps_analysis_blocked_and_language_usable():
    result = run_script(mode="failure")
    assert result["final"]["ready"] == "false" and result["final"]["controlsHidden"]
    assert result["final"]["visible"] == "3"
    assert result["failedAnalysisBlocked"] == [True, True]
    assert not result["failedLanguageBlocked"]
    assert result["final"]["languageToken"] == "failed-context"


@pytest.mark.parametrize("native_ready", (False, True))
def test_unavailable_enhancement_keeps_the_usable_native_stage(native_ready):
    result = run_script(unavailable=True, nativeReady=native_ready)["initial"]
    assert result["manual"]
    assert result["selectorHidden"] == native_ready
    assert result["controlsHidden"] != native_ready
