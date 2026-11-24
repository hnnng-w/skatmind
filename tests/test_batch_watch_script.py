"""Drive the packaged polling client through bounded, deterministic GET sequences."""

import json
import shutil
import subprocess
from importlib.resources import files

import pytest

NODE = shutil.which("node")

HARNESS = r"""
const {script, scenario} = JSON.parse(require("node:fs").readFileSync(0, "utf8"));
const assert = require("node:assert/strict"), events = [], timers = [];
const a = "a".repeat(64), b = "b".repeat(64), url = "/bound/watch/"+a;
const watch = {dataset:{batchWatch:url, unavailable:"unavailable"}}, fallback = {};
const results = {dataset:{}, contains:()=>false, replaceChildren(){this.innerHTML=""}};
const nodes = {"[data-batch-watch]":watch, "[data-batch-results]":results,
  "[data-batch-native]":fallback};
const document = {querySelector:s=>nodes[s]};
const window = {addEventListener:(s,fn)=>{if(s==="pagehide") window.exit=fn},
  setTimeout:(fn,ms)=>{assert(ms>=100); timers.push(fn)}};
let projections=0, polls=0;
async function fetch(path, init) {
  assert(!init.method || init.method==="GET"); assert(!init.signal.aborted);
  assert.equal(init.cache, "no-store"); events.push(path);
  if(path===url+"/status"){
    polls++;
    if(scenario==="foreign" && polls>1) return {ok:false,status:409};
    const initial=polls===1 && ["replace","later","abort"].includes(scenario);
    return {ok:true,json:async()=>({processed:1,phase:initial?"working":"finished",
      label:initial?"working":"finished",revision:initial?a:b})};
  }
  assert.equal(path,url+"/results"); projections++;
  if(scenario==="persistent" || scenario==="foreign" || scenario==="recover" && projections===1)
    return {ok:false,status:409};
  const rev=scenario==="replace" && projections===1?a:b;
  return {ok:true,headers:{get:()=>rev},text:async()=>rev===a?"timeout":"complete"};
}
async function run(){
  eval(script.slice(script.indexOf('const watch = document.querySelector("[data-batch-watch]")'),
    script.indexOf("// Product operations, legality,")));
  await new Promise(setImmediate);
  if(scenario==="abort") window.exit();
  if(scenario==="replace") assert.equal(results.innerHTML,"timeout");
  while(timers.length){assert(polls<=5); await timers.shift()()}
  console.log(JSON.stringify({polls,projections,html:results.innerHTML,fallback:fallback.hidden}));
}
run().catch(e=>{console.error(e);process.exitCode=1});
"""


@pytest.mark.skipif(NODE is None, reason="Optional Node script runner unavailable")
@pytest.mark.parametrize(("scenario", "polls", "reads", "html", "native"), (
    ("replace", 2, 2, "complete", False),  # One processed timeout becomes one complete original.
    ("later", 2, 1, "complete", False),  # Projection was already newer than the status response.
    ("recover", 2, 2, "complete", False),
    ("persistent", 4, 4, "", True),
    ("foreign", 2, 1, "", True),
    ("abort", 1, 1, "complete", False),
))
def test_pinned_client(scenario, polls, reads, html, native):
    script = files("skatmind.app_web").joinpath("assets/workflow.js").read_text(encoding="utf-8")
    run = subprocess.run([NODE, "-e", HARNESS], input=json.dumps(dict(
        script=script, scenario=scenario)), capture_output=True, text=True, check=True, timeout=15)
    assert json.loads(run.stdout) == dict(polls=polls, projections=reads, html=html,
                                          fallback=not native)
