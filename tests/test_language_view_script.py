"""Optional JS lifecycle tests; served-Edge evidence separately exercises actual layout."""

import json
import shutil
import subprocess
from importlib.resources import files

import pytest

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(
    NODE is None, reason="Optional Node JS lifecycle runner unavailable")

HARNESS = r"""
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const events = {}, calls = [], classes = [], observers = [];
let ready = false, payload = null, metaRemoved = false;
const target = {id:'session-recording', getClientRects:()=>[{}],
  getBoundingClientRect:()=>({top:2000-context.scrollY,bottom:4000-context.scrollY,width:500,height:2000})};
const button = {value:'de', focus:options=>calls.push({kind:'focus',options})};
const meta = {content:JSON.stringify({token:'a'.repeat(64),view:input.view}),
  remove:()=>{metaRemoved=true}};
const context = {console,TextEncoder,JSON,Set,Array,Error,Math,
  scrollX:0,scrollY:input.y||0,innerHeight:900,
  location:{pathname:'/sessions/current',search:input.search,hash:'#session-recording'},
  performance:{getEntriesByType:()=>[{type:input.navigation}]},
  history:{state:null,replaceState:(_state,_title,url)=>calls.push({kind:'history',url})},
  MutationObserver:class {constructor(fn){this.fn=fn;observers.push(this)}
    observe(){this.active=true}disconnect(){this.active=false}},
  document:{documentElement:{classList:{add:value=>classes.push(value)}},
    querySelector:selector=>selector==='meta[name="language-return"]'?meta:null,
    querySelectorAll:selector=>selector==='[id]'?[target]:
      selector.includes('.language-selector button')?[button]:[],
    getElementById:()=>ready?{}:null,
    createElement:()=>({}),
    addEventListener:(type,fn)=>{(events[type]??=[]).push(fn)}},
};
context.window=context;
context.scrollTo=options=>{calls.push({kind:'scroll',options});context.scrollY=options.top};
vm.createContext(context);
vm.runInContext(input.script,context);
const emit=(type,event={})=>(events[type]||[]).forEach(fn=>fn(event));
if(input.cancel)emit(input.cancel);
ready=true;
observers.forEach(observer=>{if(observer.active)observer.fn()});
emit('DOMContentLoaded');
// Later lifecycle events and even a second readiness callback cannot restore twice.
emit('pageshow',{persisted:true});emit('scroll');
observers.forEach(observer=>{if(observer.active)observer.fn()});
if(input.capture){
  context.scrollY=input.y;
  const form={dataset:{},matches:()=>true,querySelector:()=>null,
    append:field=>{payload=JSON.parse(field.value)}};
  emit('submit',{target:form,submitter:{name:'language',value:'de'},
    preventDefault:()=>{throw Error('unexpected rejection')}});
}
process.stdout.write(JSON.stringify({calls,classes,metaRemoved,payload,observing:observers.some(o=>o.active)}));
"""


def run_script(**changes):
    data = {"script": files("skatmind.app_web").joinpath("assets/workflow.js").read_text(),
        "view": {"anchor": "id:session-recording", "offset": -100.5, "x": 0, "focus": "de"},
        "search": "?_language_return=" + "a" * 64, "navigation": "navigate", **changes}
    completed = subprocess.run([NODE, "-e", HARNESS], input=json.dumps(data),
        text=True, capture_output=True, check=True, timeout=10)
    return json.loads(completed.stdout)


def test_restore_before_dom_ready_once_and_focus_without_scrolling():
    result = run_script()
    assert result["calls"] == [
        {"kind": "history", "url": "/sessions/current"},
        {"kind": "scroll", "options": {"left": 0, "top": 2100.5, "behavior": "instant"}},
        {"kind": "focus", "options": {"preventScroll": True}},
    ]
    assert result["classes"] == ["operation-overlays"]
    assert result["metaRemoved"] and not result["observing"]


def test_top_is_explicit_and_does_not_focus_last_edited_field():
    result = run_script(view={"anchor": "top", "offset": 0, "x": 0, "focus": "de"})
    assert result["calls"][1]["options"]["top"] == 0
    assert result["calls"][2] == {"kind": "focus", "options": {"preventScroll": True}}


@pytest.mark.parametrize("cancel", ("pointerdown", "keydown", "wheel", "touchstart", "input"))
def test_resumed_interaction_cancels_restoration(cancel):
    result = run_script(cancel=cancel)
    assert [call["kind"] for call in result["calls"]] == ["history"]
    assert not result["observing"]


@pytest.mark.parametrize("navigation", ("reload", "back_forward"))
def test_history_and_refresh_do_not_scroll_focus_or_rewrite_history(navigation):
    assert run_script(navigation=navigation)["calls"] == []


@pytest.mark.parametrize("search", ("", "?_language_return=" + "b" * 64))
def test_unintended_navigation_never_restores(search):
    assert not any(call["kind"] in {"scroll", "focus"}
                   for call in run_script(search=search)["calls"])


@pytest.mark.parametrize("y,anchor,offset", ((0, "top", 0), (2100, "id:session-recording", -100)))
def test_capture_uses_current_content_position(y, anchor, offset):
    result = run_script(view=None, capture=True, y=y)
    assert result["payload"] == {"forms": [], "disclosures": [],
        "view": {"anchor": anchor, "offset": offset, "x": 0, "focus": "de"}}
