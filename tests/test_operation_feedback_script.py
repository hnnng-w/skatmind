"""Controlled-clock tests of the served workflow script's actual feedback lifecycle."""

import json
import shutil
import subprocess
from importlib.resources import files

import pytest

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Optional Node lifecycle runner unavailable")

HARNESS = r"""
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const events = {}, noticeEvents = {}, timers = new Map(), payloads = [], focusCalls = [];
let now = input.start || 0, serial = 0, hovered = !!input.hovered, focused = false;
const box = {left:700,right:900,top:100,bottom:150,width:200,height:50};
const control = {isConnected:true, name:'language', disabled:false,
  getClientRects:()=>[{}],getBoundingClientRect:()=>({left:0,right:100,top:0,bottom:30}),
  closest(){return this},focus(options){focusCalls.push(options);document.activeElement=this}};
const notice = {dataset:{feedbackRemainingMs:String(input.remaining ?? 8000),
  dismissLabel:'Dismiss'},
  hidden:!!input.continuation,isConnected:true,style:{},live:'polite',
  append(button){this.button=button},setAttribute(name,value){if(name==='aria-live')this.live=value},
  contains:element=>element===notice.button,
  matches:selector=>selector===':focus-within'?focused:hovered,
  getClientRects:()=>notice.hidden||!notice.isConnected?[]:[box],getBoundingClientRect:()=>box,
  addEventListener:(type,fn)=>{(noticeEvents[type]??=[]).push(fn)}};
if(input.continuation)notice.dataset.feedbackContinuation='';
const token='a'.repeat(64);
const meta = input.continuation?{content:JSON.stringify({token,view:null}),remove(){}}:null;
const document = {hidden:!!input.hidden,activeElement:control,
  documentElement:{classList:{add(){}}},
  querySelector:selector=>selector==='meta[name="language-return"]'?meta:
    selector==='main'?control:null,
  querySelectorAll:selector=>selector==='[data-operation-feedback]'?[notice]:
    selector.startsWith('input:not')?[control]:[],
  getElementById:()=>null,
  createElement:()=>({getBoundingClientRect:()=>box,addEventListener(type,fn){this[type]=fn}}),
  addEventListener:(type,fn)=>{(events[type]??=[]).push(fn)}};
const context = {console,TextEncoder,JSON,Set,Array,Error,Math,Number,document,
  scrollX:0,scrollY:0,innerHeight:900,
  performance:{now:()=>now,getEntriesByType:()=>[{type:input.navigation||'navigate'}]},
  location:{pathname:'/sessions/current',search:input.wrongReturn?'':`?_language_return=${token}`},
  history:{state:null,replaceState(){}},
  setTimeout:(fn,delay)=>{const id=++serial;timers.set(id,{fn,at:now+delay});return id},
  clearTimeout:id=>timers.delete(id),
  addEventListener:(type,fn)=>{(events[type]??=[]).push(fn)}};
context.window=context;
vm.createContext(context);vm.runInContext(input.script,context);
const emit=(type,event={})=>(events[type]||[]).forEach(fn=>fn(event));
const emitNotice=type=>(noticeEvents[type]||[]).forEach(fn=>fn());
const advance=delta=>{
  const end=now+delta;
  while(true){
    const due=[...timers].filter(([,timer])=>timer.at<=end).sort((a,b)=>a[1].at-b[1].at)[0];
    if(!due)break;
    now=due[1].at;timers.delete(due[0]);due[1].fn();
  }
  now=end;
};
emit('DOMContentLoaded');
for(const step of input.steps||[]){
  if('advance' in step)advance(step.advance);
  if('hover' in step){hovered=step.hover;emit('pointermove',
    {clientX:hovered?800:0,clientY:hovered?120:0,target:null})}
  if('hidden' in step){document.hidden=step.hidden;emit('visibilitychange')}
  if('focus' in step){focused=step.focus;document.activeElement=focused?notice.button:control;
    emitNotice(focused?'focusin':'focusout');advance(0)}
  if(step.dismiss)notice.button.click();
  if(step.withdraw){control.getBoundingClientRect=()=>box;emit('focusin',{target:control})}
  if(step.detach)notice.isConnected=false;
  if(step.pagehide)emit('pagehide');
  if(step.pageshow)emit('pageshow',{persisted:true});
  if(step.submit){
    const error={focus(){},hidden:true};
    const form={dataset:{},matches:()=>true,querySelector:selector=>
      selector==='.language-error'?error:null,append:field=>payloads.push(JSON.parse(field.value))};
    emit('submit',{target:form,submitter:{name:'language',value:step.invalid?'fr':'de'},
      preventDefault(){payloads.push('rejected')}});
  }
}
process.stdout.write(JSON.stringify({payloads,hidden:notice.hidden,live:notice.live,
  timers:[...timers.values()].map(timer=>timer.at-now),focusCalls,now}));
"""


def run_script(**changes):
    data = {"script": files("skatmind.app_web").joinpath("assets/workflow.js").read_text(),
            **changes}
    result = subprocess.run([NODE, "-e", HARNESS], input=json.dumps(data), text=True,
                            capture_output=True, check=True, timeout=10)
    return json.loads(result.stdout)


def test_capture_once_and_resume_remaining_budget_excluding_navigation_time():
    first = run_script(steps=[{"advance": 3000}, {"submit": True}])
    assert first["payloads"][0]["feedback_remaining_ms"] == 5000
    assert first["hidden"] and first["timers"] == []
    second = run_script(continuation=True, remaining=5000, start=28000,
                        steps=[{"advance": 2000}, {"submit": True}])
    assert second["payloads"][0]["feedback_remaining_ms"] == 3000
    final = run_script(continuation=True, remaining=3000, start=50000,
                       steps=[{"advance": 2999}])
    assert not final["hidden"] and final["timers"] == [1]
    assert run_script(continuation=True, remaining=3000, steps=[{"advance": 3000}])["hidden"]


@pytest.mark.parametrize("pause", ("hover", "focus", "hidden"))
def test_existing_pause_arithmetic_and_fresh_document_state(pause):
    result = run_script(steps=[{"advance": 1000}, {pause: True}, {"advance": 20000},
                               {pause: False}, {"advance": 2000}, {"submit": True}])
    assert result["payloads"][0]["feedback_remaining_ms"] == 5000
    resumed = run_script(continuation=True, remaining=5000, steps=[{"advance": 5000}])
    assert resumed["hidden"] and resumed["focusCalls"] == []


@pytest.mark.parametrize("state", ("hovered", "hidden"))
def test_return_evaluates_current_hover_and_document_visibility(state):
    result = run_script(continuation=True, remaining=1500, **{state: True},
                        steps=[{"advance": 5000}, {"submit": True}])
    assert result["payloads"][0]["feedback_remaining_ms"] == 1500


@pytest.mark.parametrize("step", ({"dismiss": True}, {"advance": 8000},
    {"withdraw": True}, {"detach": True}, {"pagehide": True}, {"pageshow": True}))
def test_closed_expired_withdrawn_or_absent_feedback_is_not_submitted(step):
    result = run_script(steps=[step, {"submit": True}])
    assert "feedback_remaining_ms" not in result["payloads"][0]


@pytest.mark.parametrize("changes", ({"navigation": "reload"},
    {"navigation": "back_forward"}, {"wrongReturn": True}))
def test_unintended_navigation_never_reveals_continuation(changes):
    result = run_script(continuation=True, remaining=5000, **changes,
                        steps=[{"submit": True}])
    assert result["hidden"] and result["timers"] == []
    assert "feedback_remaining_ms" not in result["payloads"][0]


def test_capture_failure_withdraws_old_success_for_the_new_error():
    result = run_script(steps=[{"submit": True, "invalid": True}])
    assert result["payloads"] == ["rejected"]
    assert result["hidden"] and result["timers"] == []
