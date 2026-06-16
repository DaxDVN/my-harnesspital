#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, re, shutil, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AGENTFLOW = ROOT / ".agentflow"
STATE_PATH = AGENTFLOW / "state.json"
CONFIG_PATH = AGENTFLOW / "config.yaml"
ROUNDS = AGENTFLOW / "rounds"
STATES = {"IDLE","TESTING","BUG_PACKET_READY","RCA_RUNNING","RCA_PLAN_READY","CODEX_REVIEW_REQUIRED","CODEX_REVIEWING","CODEX_REJECTED","CODEX_APPROVED","DIRECT_PATCH_APPROVED","IMPLEMENTING","IMPLEMENTED","RETESTING","RETEST_PASSED","RETEST_FAILED","PLAN_MISMATCH","NEEDS_MORE_EVIDENCE","HUMAN_DECISION_REQUIRED","DONE","FAILED"}
EXPECTED_EXECUTOR_MODEL = "mimo-v2.5"
EXPECTED_EXECUTOR_PROVIDER = "xiaomi-token-plan-sgp"
EXPECTED_EXECUTOR_CLI_MODEL = "xiaomi-token-plan-sgp/mimo-v2.5"
TRANSITIONS = {
 "IDLE":{"TESTING","IDLE","FAILED"}, "TESTING":{"BUG_PACKET_READY","RETEST_FAILED","FAILED"},
 "BUG_PACKET_READY":{"RCA_RUNNING","DIRECT_PATCH_APPROVED","NEEDS_MORE_EVIDENCE","FAILED"},
 "RCA_RUNNING":{"RCA_PLAN_READY","NEEDS_MORE_EVIDENCE","HUMAN_DECISION_REQUIRED","FAILED"},
 "RCA_PLAN_READY":{"DIRECT_PATCH_APPROVED","CODEX_REVIEW_REQUIRED","NEEDS_MORE_EVIDENCE","HUMAN_DECISION_REQUIRED","FAILED"},
 "CODEX_REVIEW_REQUIRED":{"CODEX_REVIEWING","FAILED"},
 "CODEX_REVIEWING":{"CODEX_APPROVED","CODEX_REJECTED","RCA_RUNNING","FAILED"},
 "CODEX_REJECTED":{"RCA_RUNNING","HUMAN_DECISION_REQUIRED","FAILED"},
 "CODEX_APPROVED":{"IMPLEMENTING","FAILED"}, "DIRECT_PATCH_APPROVED":{"IMPLEMENTING","FAILED"},
 "IMPLEMENTING":{"IMPLEMENTED","PLAN_MISMATCH","FAILED"}, "IMPLEMENTED":{"RETESTING","FAILED"},
 "PLAN_MISMATCH":{"RCA_RUNNING","HUMAN_DECISION_REQUIRED","FAILED"},
 "RETESTING":{"RETEST_PASSED","RETEST_FAILED","FAILED"}, "RETEST_PASSED":{"DONE","FAILED"},
 "RETEST_FAILED":{"RCA_RUNNING","TESTING","HUMAN_DECISION_REQUIRED","FAILED"},
 "NEEDS_MORE_EVIDENCE":{"TESTING","HUMAN_DECISION_REQUIRED","FAILED"},
 "HUMAN_DECISION_REQUIRED":{"IDLE","FAILED"}, "DONE":{"IDLE"}, "FAILED":{"IDLE"}
}
ARTIFACT_KEYS = {"bug_packet","rca_plan","codex_review","approved_plan","implementation_report","retest_report"}
BUG_STATUS={"PASS","FAIL"}; REPRO={"ALWAYS","INTERMITTENT","UNKNOWN","NOT_APPLICABLE"}; RCA_VERDICTS={"DIRECT_PATCH","CODEX_REQUIRED","MORE_EVIDENCE","HUMAN_DECISION"}; RISK={"LOW","MEDIUM","HIGH"}; CODEX_VERDICTS={"APPROVE","APPROVE_WITH_CHANGES","REJECT"}; IMPL_STATUS={"IMPLEMENTED","PLAN_MISMATCH","FAILED"}; CMD_STATUS={"PASS","FAIL","NOT_RUN"}; VALIDATION_STATUS={"PASS","FAIL","NOT_RUN"}; RETEST_STATUS={"PASS","FAIL"}; FAIL_REL={"SAME_BUG","NEW_BUG","UNKNOWN","NOT_APPLICABLE"}
class ValidationError(Exception): pass

def load_json(path: Path) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc: raise ValidationError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc: raise ValidationError(f"invalid JSON: {path}: {exc}") from exc

def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

def require(obj: dict[str,Any], fields: list[str], ctx: str) -> None:
    for f in fields:
        if f not in obj: raise ValidationError(f"{ctx}: missing required field {f}")
def enum(value: Any, allowed: set[str], ctx: str) -> None:
    if value not in allowed: raise ValidationError(f"{ctx}: invalid value {value!r}; allowed={sorted(allowed)}")
def is_list(value: Any, ctx: str) -> None:
    if not isinstance(value, list): raise ValidationError(f"{ctx}: expected list")
def is_dict(value: Any, ctx: str) -> None:
    if not isinstance(value, dict): raise ValidationError(f"{ctx}: expected object")

def validate_bug_packet(d: dict[str,Any]) -> None:
    require(d,["round_id","scenario","status","route","steps_to_reproduce","expected","actual","evidence","reproducibility","executor_notes"],"bug-packet")
    enum(d["status"],BUG_STATUS,"bug-packet.status"); enum(d["reproducibility"],REPRO,"bug-packet.reproducibility"); is_list(d["steps_to_reproduce"],"bug-packet.steps_to_reproduce"); is_dict(d["evidence"],"bug-packet.evidence")
    require(d["evidence"],["browser_snapshot_excerpt","console_errors","network_errors","screenshot_paths","video_path","agent_browser_logs"],"bug-packet.evidence")
    is_dict(d["executor_notes"],"bug-packet.executor_notes")
    if d["executor_notes"].get("root_cause_hypothesis") is not None: raise ValidationError("bug-packet.executor_notes.root_cause_hypothesis must be null")
    if d["executor_notes"].get("classification") is not None: raise ValidationError("bug-packet.executor_notes.classification must be null")
    if d["status"]=="FAIL" and (not d["expected"] or not d["actual"] or not d["steps_to_reproduce"]): raise ValidationError("FAIL bug-packet requires expected, actual, and steps_to_reproduce")

def validate_rca_plan(d: dict[str,Any]) -> None:
    require(d,["round_id","verdict","root_cause","evidence_supporting_root_cause","affected_files","allowed_files_to_modify","files_to_inspect_but_not_modify","forbidden_changes","implementation_plan","validation_plan","risk_level","requires_codex_review","codex_review_questions"],"rca-plan")
    enum(d["verdict"],RCA_VERDICTS,"rca-plan.verdict"); enum(d["risk_level"],RISK,"rca-plan.risk_level")
    for f in ["evidence_supporting_root_cause","affected_files","allowed_files_to_modify","files_to_inspect_but_not_modify","forbidden_changes","implementation_plan","validation_plan","codex_review_questions"]: is_list(d[f],f"rca-plan.{f}")
    if not isinstance(d["requires_codex_review"], bool): raise ValidationError("rca-plan.requires_codex_review must be boolean")
    if d["verdict"] in {"DIRECT_PATCH","CODEX_REQUIRED"} and (not d["root_cause"] or not d["implementation_plan"] or not d["validation_plan"]): raise ValidationError("patchable rca-plan requires root_cause, implementation_plan, validation_plan")

def validate_codex_review(d: dict[str,Any]) -> None:
    require(d,["round_id","verdict","summary","blocking_issues","required_changes","optional_suggestions","checked_files","risk_assessment","final_instruction_to_claude"],"codex-review")
    enum(d["verdict"],CODEX_VERDICTS,"codex-review.verdict"); enum(d["risk_assessment"],RISK,"codex-review.risk_assessment")
    for f in ["blocking_issues","required_changes","optional_suggestions","checked_files"]: is_list(d[f],f"codex-review.{f}")

def validate_executor_model(executor: dict[str,Any], ctx: str) -> None:
    is_dict(executor,ctx); require(executor,["runtime","model","call_method"],ctx)
    if executor.get("runtime")!="opencode": raise ValidationError(f"{ctx}.runtime must be opencode")
    if executor.get("model")!=EXPECTED_EXECUTOR_MODEL: raise ValidationError(f"{ctx}.model must be {EXPECTED_EXECUTOR_MODEL}")
    if executor.get("call_method")!="bash-wrapper": raise ValidationError(f"{ctx}.call_method must be bash-wrapper")

def validate_implementation_report(d: dict[str,Any]) -> None:
    require(d,["round_id","status","executor","plan_version","files_changed","steps_completed","commands_run","validation_result","remaining_issues"],"implementation-report")
    enum(d["status"],IMPL_STATUS,"implementation-report.status"); validate_executor_model(d["executor"],"implementation-report.executor")
    for f in ["files_changed","steps_completed","commands_run","remaining_issues"]: is_list(d[f],f"implementation-report.{f}")
    enum(d["validation_result"],VALIDATION_STATUS,"implementation-report.validation_result")
    for i,c in enumerate(d["commands_run"]): is_dict(c,f"implementation-report.commands_run[{i}]"); require(c,["command","status","summary"],f"implementation-report.commands_run[{i}]"); enum(c["status"],CMD_STATUS,f"implementation-report.commands_run[{i}].status")

def validate_retest_report(d: dict[str,Any]) -> None:
    require(d,["round_id","status","executor","scenario","result","evidence","failure_relation"],"retest-report")
    enum(d["status"],RETEST_STATUS,"retest-report.status"); validate_executor_model(d["executor"],"retest-report.executor")
    is_dict(d["result"],"retest-report.result"); require(d["result"],["expected","actual"],"retest-report.result"); is_dict(d["evidence"],"retest-report.evidence"); require(d["evidence"],["browser_snapshot_excerpt","console_errors","network_errors","screenshot_paths"],"retest-report.evidence"); enum(d["failure_relation"],FAIL_REL,"retest-report.failure_relation")

def validate_state(d: dict[str,Any]) -> None:
    require(d,["current_round","state","scenario","executor","codex_review_count","max_codex_reviews","rca_revision_count","max_rca_revisions","budget","artifacts","last_error"],"state"); enum(d["state"],STATES,"state.state"); validate_executor_model(d["executor"],"state.executor")
    if d["executor"].get("provider")!=EXPECTED_EXECUTOR_PROVIDER: raise ValidationError(f"state.executor.provider must be {EXPECTED_EXECUTOR_PROVIDER}")
    is_dict(d["artifacts"],"state.artifacts")
    for k in ARTIFACT_KEYS:
        if k not in d["artifacts"]: raise ValidationError(f"state.artifacts missing {k}")
VALIDATORS={"bug-packet":validate_bug_packet,"rca-plan":validate_rca_plan,"codex-review":validate_codex_review,"implementation-report":validate_implementation_report,"retest-report":validate_retest_report,"state":validate_state}

def validate_artifact(kind: str, path: Path) -> None:
    if kind not in VALIDATORS: raise ValidationError(f"unknown artifact kind {kind!r}; expected one of {sorted(VALIDATORS)}")
    data=load_json(path)
    if not isinstance(data,dict): raise ValidationError(f"{kind}: top-level JSON must be object")
    VALIDATORS[kind](data)

def current_utc() -> str: return datetime.now(timezone.utc).isoformat()
def init_state() -> dict[str,Any]:
    return {"current_round":None,"state":"IDLE","scenario":None,"executor":{"runtime":"opencode","model":EXPECTED_EXECUTOR_MODEL,"provider":EXPECTED_EXECUTOR_PROVIDER,"call_method":"bash-wrapper"},"codex_review_count":0,"max_codex_reviews":2,"rca_revision_count":0,"max_rca_revisions":2,"budget":{"max_rounds":5,"max_total_minutes":180,"max_opencode_iterations_per_round":2},"artifacts":{"bug_packet":None,"rca_plan":None,"codex_review":None,"approved_plan":None,"implementation_report":None,"retest_report":None},"last_error":None}
def read_state() -> dict[str,Any]:
    if not STATE_PATH.exists():
        st=init_state(); save_json(STATE_PATH,st); return st
    d=load_json(STATE_PATH)
    if not isinstance(d,dict): raise ValidationError("state file top-level must be object")
    validate_state(d); return d

def transition_allowed(old: str, new: str) -> bool: return new==old or new in TRANSITIONS.get(old,set())
def config_value(key: str) -> str|None:
    if not CONFIG_PATH.exists(): return None
    stack=[]; values={}
    for raw in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or ":" not in raw: continue
        indent=len(raw)-len(raw.lstrip(" ")); line=raw.strip(); k,v=line.split(":",1)
        while stack and stack[-1][0]>=indent: stack.pop()
        stack.append((indent,k.strip())); full=".".join(x[1] for x in stack)
        if v.strip(): values[full]=v.strip().strip('"').strip("'")
    return values.get(key)

def command_validate(argv):
    if len(argv)!=3: print("usage: validate-artifact <kind> <path>", file=sys.stderr); return 2
    try: validate_artifact(argv[1],Path(argv[2]))
    except ValidationError as exc: print(f"INVALID {argv[1]}: {exc}", file=sys.stderr); return 1
    print(f"VALID {argv[1]}: {argv[2]}"); return 0

def command_update_state(argv):
    if len(argv)<3: print("usage: update-state <round-id> <new-state> [artifact_key=path ...] [error=CODE]", file=sys.stderr); return 2
    round_id,new_state=argv[1],argv[2]
    if new_state not in STATES: print(f"invalid state {new_state}", file=sys.stderr); return 2
    try: state=read_state()
    except ValidationError as exc: print(f"invalid existing state: {exc}", file=sys.stderr); return 1
    old=state["state"]
    if not transition_allowed(old,new_state): print(f"invalid transition: {old} -> {new_state}", file=sys.stderr); return 1
    state["current_round"]=round_id; state["state"]=new_state; err=None
    for item in argv[3:]:
        if item.startswith("error="): err=item.split("=",1)[1]; continue
        if "=" not in item: print(f"invalid update token {item!r}; expected key=path", file=sys.stderr); return 2
        key,value=item.split("=",1)
        if key=="scenario": state["scenario"]=value
        elif key in ARTIFACT_KEYS: state["artifacts"][key]=value
        else: print(f"invalid artifact key {key!r}", file=sys.stderr); return 2
    state["last_error"]=err; save_json(STATE_PATH,state); print(f"STATE {old} -> {new_state} ({round_id})"); return 0

def command_init_round(argv):
    if len(argv)<2: print("usage: init-round <round-id> [scenario]", file=sys.stderr); return 2
    round_id=argv[1]; scenario=argv[2] if len(argv)>2 else None; rd=ROUNDS/round_id; (rd/"logs").mkdir(parents=True, exist_ok=True)
    save_json(rd/"00-round-meta.json", {"round_id":round_id,"scenario":scenario,"created_at":current_utc(),"executor_usage":{"model":EXPECTED_EXECUTOR_MODEL,"provider":EXPECTED_EXECUTOR_PROVIDER,"estimated_credits_used":None,"input_tokens":None,"output_tokens":None,"cache_hit_tokens":None,"cache_miss_tokens":None}})
    st=read_state()
    if st["state"] not in {"IDLE","DONE","FAILED"}: print(f"cannot init round while state is {st['state']}", file=sys.stderr); return 1
    st=init_state(); st["current_round"]=round_id; st["scenario"]=scenario; save_json(STATE_PATH,st); print(f"Initialized {round_id} at {rd}"); return 0

def command_summarize_round(argv):
    if len(argv)!=2: print("usage: summarize-round <round-id>", file=sys.stderr); return 2
    round_id=argv[1]; rd=ROUNDS/round_id
    if not rd.exists(): print(f"round does not exist: {round_id}", file=sys.stderr); return 1
    files={"bug_packet":rd/"01-bug-packet.json","rca_plan":rd/"02-rca-plan.json","codex_review":rd/"03-codex-review.json","approved_plan":rd/"04-approved-plan.md","implementation_report":rd/"05-implementation-report.json","retest_report":rd/"06-retest-report.json"}
    lines=[f"# Final Round Summary - {round_id}","",f"Generated: {current_utc()}","","## Artifacts"]
    for k,p in files.items(): lines.append(f"- {k}: {'present' if p.exists() else 'missing'} ({p.relative_to(ROOT)})")
    retest="UNKNOWN"
    if files["retest_report"].exists():
        try: retest=load_json(files["retest_report"]).get("status","UNKNOWN")
        except ValidationError: retest="INVALID"
    lines += ["","## Result",f"- Retest status: {retest}"]
    if files["implementation_report"].exists():
        lines += ["","## Changed Files"]
        try:
            changed=load_json(files["implementation_report"]).get("files_changed",[])
            lines += [f"- `{x.get('path','<unknown>')}`: {x.get('summary','')}" for x in changed] if changed else ["- None reported"]
        except ValidationError: lines.append("- Implementation report invalid")
    summary=rd/"07-final-round-summary.md"; summary.write_text("\n".join(lines)+"\n", encoding="utf-8")
    try:
        st=read_state()
        if st["state"]=="RETEST_PASSED" and retest=="PASS": st["state"]="DONE"; save_json(STATE_PATH,st); print("STATE RETEST_PASSED -> DONE")
    except ValidationError as exc: print(f"warning: could not update DONE state: {exc}", file=sys.stderr)
    print(f"Wrote {summary}"); return 0

def command_config_value(argv):
    if len(argv)!=2: print("usage: config-value <dot.key>", file=sys.stderr); return 2
    val=config_value(argv[1])
    if val is None: return 1
    print(val); return 0

def command_doctor(argv):
    req=["README.md","WORKFLOW.md","IMPLEMENTATION_NOTES.md","package.json",".opencode/opencode.jsonc",".opencode/skills/agent-browser/SKILL.md",".agentflow/state.json",".agentflow/config.yaml",".agentflow/bin/agent-browser",".agentflow/bin/test-with-opencode",".agentflow/bin/implement-with-opencode",".agentflow/bin/retest-with-opencode",".agentflow/bin/validate-artifact",".agentflow/bin/update-state",".agentflow/bin/init-round",".agentflow/bin/summarize-round",".agentflow/bin/doctor",".agentflow/bin/capabilities",".agentflow/bin/probe-web-with-opencode",".agentflow/bin/probe-browser-with-opencode",".agentflow/bin/probe-agent-browser-with-opencode",".agentflow/vendor/agent-browser-package/bin/agent-browser.js",".agentflow/vendor/agent-browser-package/skill-data/core/SKILL.md","tests/mock-opencode","tests/run-smoke-tests"]
    ok=True; print("progressive-test doctor")
    for rel in req:
        p=ROOT/rel
        if not p.exists(): print(f"FAIL missing {rel}"); ok=False
        else: print(f"OK   {rel}")
    for rel in [".agentflow/bin/agent-browser",".agentflow/bin/test-with-opencode",".agentflow/bin/implement-with-opencode",".agentflow/bin/retest-with-opencode",".agentflow/bin/validate-artifact",".agentflow/bin/update-state",".agentflow/bin/init-round",".agentflow/bin/summarize-round",".agentflow/bin/doctor",".agentflow/bin/capabilities",".agentflow/bin/probe-web-with-opencode",".agentflow/bin/probe-browser-with-opencode",".agentflow/bin/probe-agent-browser-with-opencode","tests/mock-opencode","tests/run-smoke-tests"]:
        p=ROOT/rel
        if p.exists() and not os.access(p,os.X_OK): print(f"FAIL not executable {rel}"); ok=False
    try: validate_artifact("state",STATE_PATH); print("OK   state.json valid")
    except ValidationError as exc: print(f"FAIL state invalid: {exc}"); ok=False
    model=config_value("executor.model")
    if model!=EXPECTED_EXECUTOR_MODEL: print(f"FAIL executor.model expected {EXPECTED_EXECUTOR_MODEL}, got {model!r}"); ok=False
    else: print(f"OK   config executor.model={EXPECTED_EXECUTOR_MODEL}")
    provider=config_value("executor.provider")
    if provider!=EXPECTED_EXECUTOR_PROVIDER: print(f"FAIL executor.provider expected {EXPECTED_EXECUTOR_PROVIDER}, got {provider!r}"); ok=False
    else: print(f"OK   config executor.provider={EXPECTED_EXECUTOR_PROVIDER}")
    cli_model=config_value("executor.cli_model")
    if cli_model!=EXPECTED_EXECUTOR_CLI_MODEL: print(f"FAIL executor.cli_model expected {EXPECTED_EXECUTOR_CLI_MODEL}, got {cli_model!r}"); ok=False
    else: print(f"OK   config executor.cli_model={EXPECTED_EXECUTOR_CLI_MODEL}")
    local_path=str(ROOT/".agentflow/bin")+os.pathsep+os.environ.get("PATH","")
    oc=shutil.which("opencode"); ab=shutil.which("agent-browser", path=local_path)
    print(f"OK   opencode found: {oc}" if oc else "WARN opencode not found; use AGENTFLOW_MOCK_OPENCODE=1 for smoke/MVP contract tests")
    print(f"OK   agent-browser found: {ab}" if ab else "FAIL agent-browser shim not found"); ok = ok and bool(ab)
    ab_chrome=Path.home()/".agent-browser/browsers/chrome-149.0.7827.115"
    print(f"OK   agent-browser Chrome installed: {ab_chrome}" if ab_chrome.exists() else "WARN agent-browser Chrome missing; run .agentflow/bin/agent-browser install")
    shim=config_value("capabilities.browser.shim_path")
    print(f"OK   browser shim configured: {shim}" if shim else "WARN no capabilities.browser.shim_path configured")
    if (ROOT/"tests/mock-opencode").exists(): print("OK   mock smoke test readiness")
    print("DOCTOR PASS" if ok else "DOCTOR FAIL"); return 0 if ok else 1

# --- Envelope layer (orchestrator reads ONLY these short receipts, never the long payloads) ---
ENVELOPE_KINDS={"bug-packet","rca-plan","codex-review","approved-plan","implementation-report","retest-report"}
ENVELOPE_REQUIRED=["round_id","artifact_type","artifact_path","author","intended_recipient","verdict","risk_level","requires_codex_review","status","summary_for_router","content_sha256","created_at","next"]

def sha256_file(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def envelope_path_for(payload: Path) -> Path: return payload.with_name(payload.stem + ".envelope.json")
def _rel(path: Path) -> str:
    try: return str(path.resolve().relative_to(ROOT))
    except ValueError: return str(path)
def _md_round_id(text: str):
    m=re.search(r"round-[A-Za-z0-9._-]+", text); return m.group(0) if m else None

def derive_envelope(kind: str, payload: Path) -> dict[str,Any]:
    base={"artifact_type":kind.replace("-","_"),"artifact_path":_rel(payload),"status":"READY","content_sha256":sha256_file(payload),"created_at":current_utc(),"requires_codex_review":False,"risk_level":None}
    if kind=="approved-plan":
        text=payload.read_text(encoding="utf-8",errors="ignore")
        base.update({"round_id":_md_round_id(text),"author":"agentflow-orchestrator","intended_recipient":"opencode-executor","verdict":"APPROVED","next":"IMPLEMENT","summary_for_router":"Approved plan ready for IMPLEMENT_ONLY."}); return base
    d=load_json(payload); base["round_id"]=d.get("round_id")
    if kind=="bug-packet":
        st=d.get("status"); base.update({"author":"opencode-executor","intended_recipient":"agentflow-orchestrator","verdict":st,"next":("CLASSIFY" if st=="FAIL" else "DONE"),"summary_for_router":f"bug {st} on {d.get('route')}"})
    elif kind=="rca-plan":
        v=d.get("verdict"); rcx=bool(d.get("requires_codex_review")); nxt={"DIRECT_PATCH":"BUILD_PLAN","CODEX_REQUIRED":"CODEX_REVIEW","MORE_EVIDENCE":"TESTING","HUMAN_DECISION":"HUMAN_DECISION"}.get(v,"HUMAN_DECISION")
        base.update({"author":"claude-rca-subagent","intended_recipient":("codex-reviewer" if rcx else "agentflow-orchestrator"),"verdict":v,"risk_level":d.get("risk_level"),"requires_codex_review":rcx,"next":nxt,"summary_for_router":f"RCA {v} risk {d.get('risk_level')}"})
    elif kind=="codex-review":
        v=d.get("verdict"); nxt={"APPROVE":"BUILD_PLAN","APPROVE_WITH_CHANGES":"BUILD_PLAN","REJECT":"RCA_REVISE"}.get(v,"HUMAN_DECISION")
        base.update({"author":"codex-reviewer","intended_recipient":"agentflow-orchestrator","verdict":v,"risk_level":d.get("risk_assessment"),"next":nxt,"summary_for_router":(d.get("final_instruction_to_claude") or v or "")[:120]})
    elif kind=="implementation-report":
        st=d.get("status"); nxt={"IMPLEMENTED":"RETEST","PLAN_MISMATCH":"RCA","FAILED":"FAIL"}.get(st,"FAIL")
        base.update({"author":"opencode-executor","intended_recipient":"agentflow-orchestrator","verdict":st,"next":nxt,"summary_for_router":f"impl {st} validation {d.get('validation_result')}"})
    elif kind=="retest-report":
        st=d.get("status"); nxt={"PASS":"DONE","FAIL":"RETEST_FAILED"}.get(st,"FAIL")
        base.update({"author":"opencode-executor","intended_recipient":"agentflow-orchestrator","verdict":st,"next":nxt,"summary_for_router":f"retest {st} ({d.get('failure_relation')})"})
    else: raise ValidationError(f"unknown envelope kind {kind!r}")
    return base

def validate_envelope(path: Path) -> None:
    d=load_json(path)
    if not isinstance(d,dict): raise ValidationError("envelope: top-level must be object")
    require(d,ENVELOPE_REQUIRED,"envelope")
    p=Path(d["artifact_path"]); p=p if p.is_absolute() else (ROOT/p)
    if not p.exists(): raise ValidationError(f"envelope.artifact_path missing: {d['artifact_path']}")
    actual=sha256_file(p)
    if actual!=d["content_sha256"]: raise ValidationError(f"envelope.content_sha256 mismatch: payload changed (env {d['content_sha256'][:12]} != actual {actual[:12]})")

def command_write_envelope(argv):
    if len(argv)!=3: print("usage: write-envelope <kind> <payload-path>", file=sys.stderr); return 2
    kind,payload=argv[1],Path(argv[2])
    if kind not in ENVELOPE_KINDS: print(f"unknown kind {kind!r}; expected {sorted(ENVELOPE_KINDS)}", file=sys.stderr); return 2
    if not payload.exists(): print(f"payload missing: {payload}", file=sys.stderr); return 1
    try: env=derive_envelope(kind,payload)
    except ValidationError as exc: print(f"ENVELOPE_DERIVE_FAILED: {exc}", file=sys.stderr); return 1
    ep=envelope_path_for(payload); save_json(ep,env); print(f"Wrote {ep}"); return 0

def command_validate_envelope(argv):
    if len(argv)!=2: print("usage: validate-envelope <envelope-path>", file=sys.stderr); return 2
    try: validate_envelope(Path(argv[1]))
    except ValidationError as exc: print(f"INVALID envelope: {exc}", file=sys.stderr); return 1
    print(f"VALID envelope: {argv[1]}"); return 0

# --- P3: deterministic hybrid triage (NARROW whitelist; when in doubt -> Opus RCA) ---
_TRIVIAL_RE=re.compile(r"['\"]?([A-Za-z_$][\w$]*)['\"]? is not defined|can't find variable:\s*([A-Za-z_$][\w$]*)|cannot find name ['\"]([A-Za-z_$][\w$]*)['\"]", re.I)
def classify_bug(bp: dict[str,Any]):
    if bp.get("status")!="FAIL": return ("NEEDS_RCA",None)
    console=" ".join(str(x) for x in ((bp.get("evidence") or {}).get("console_errors") or []))
    m=_TRIVIAL_RE.search(console)
    if m and re.search(r"import|not defined|find variable|find name", console, re.I):
        sym=next((g for g in m.groups() if g), None)
        if sym: return ("TRIVIAL",{"class":"missing-import-or-undefined-symbol","symbol":sym})
    return ("NEEDS_RCA",None)

_TRIVIAL_PLAN="""# Approved Plan - {rid}

## Approval Source
DIRECT_PATCH_BY_CLAUDE

## Executor Runtime
OpenCode
## Executor Model
mimo-v2.5
## Executor Call Method
Bash wrapper script:
.agentflow/bin/implement-with-opencode

## Scope
Trivial deterministic fix (no RCA, no Codex): resolve undefined symbol / missing import `{sym}`.

## Root Cause Summary
Browser evidence shows `{sym}` is not defined — a missing or incorrect import / undefined reference.

## Files Allowed To Modify
- The single source file in the failing route that references `{sym}` (locate it; add/fix ONLY its import).

## Files Forbidden To Modify
- Every file except the one that needs the `{sym}` import.

## Forbidden Changes
- Do not change API contract, schema, business logic, or styling.
- Do not add a dependency. Do not refactor or touch unrelated code.
- ONLY add or correct the import for `{sym}`.

## Implementation Steps
1. Find the source file in the failing route that references `{sym}`.
2. Add or correct the import for `{sym}` (and nothing else).

## Validation Commands
- Type-check / build the affected package.

## E2E Retest Scenario
- Re-run the failing scenario via agent-browser; confirm the `{sym}` error is gone and expected behavior appears.

## Stop Conditions
- If you cannot find a single clear file for `{sym}`, stop with PLAN_MISMATCH (escalate to RCA).
- If the fix needs more than an import change, stop with PLAN_MISMATCH.
"""
def command_classify(argv):
    if len(argv)!=2: print("usage: classify <round-id>", file=sys.stderr); return 2
    rid=argv[1]; bp_p=ROUNDS/rid/"01-bug-packet.json"
    if not bp_p.exists(): print(f"missing bug-packet: {bp_p}", file=sys.stderr); return 1
    route,info=classify_bug(load_json(bp_p))
    if route=="TRIVIAL":
        (ROUNDS/rid/"04-approved-plan.md").write_text(_TRIVIAL_PLAN.format(rid=rid,sym=info["symbol"]), encoding="utf-8")
        print(f"ROUTE: TRIVIAL ({info['class']}: {info['symbol']}) -> wrote 04-approved-plan.md"); return 0
    print("ROUTE: NEEDS_RCA"); return 0

# --- P4: build the approved plan from the RCA plan (+ optional Codex review) ---
def command_build_approved_plan(argv):
    if len(argv)!=2: print("usage: build-approved-plan <round-id>", file=sys.stderr); return 2
    rid=argv[1]; rd=ROUNDS/rid; rca_p=rd/"02-rca-plan.json"
    if not rca_p.exists(): print(f"missing rca-plan: {rca_p}", file=sys.stderr); return 1
    rca=load_json(rca_p); approval="DIRECT_PATCH_BY_CLAUDE"
    codex_p=rd/"03-codex-review.json"
    if codex_p.exists():
        cx=load_json(codex_p)
        if cx.get("verdict")=="REJECT": print("codex verdict REJECT — cannot build approved plan", file=sys.stderr); return 1
        approval="APPROVED_BY_CODEX"
    def bl(items): return "\n".join(f"- {x}" for x in items) if items else "- (none)"
    def fl(items): return "\n".join(f"- `{x.get('path','?')}` — {x.get('reason','')}" for x in items) if items else "- (none)"
    forb=rca.get("forbidden_changes") or ["Do not change API contract.","Do not change schema.","Do not add a dependency.","Do not refactor unrelated code."]
    md=f"# Approved Plan - {rid}\n\n## Approval Source\n{approval}\n\n## Executor Runtime\nOpenCode\n## Executor Model\nmimo-v2.5\n## Executor Call Method\nBash wrapper script:\n.agentflow/bin/implement-with-opencode\n\n## Scope\n{rca.get('root_cause','')}\n\n## Root Cause Summary\n{rca.get('root_cause','')}\n\n## Files Allowed To Modify\n{bl(rca.get('allowed_files_to_modify',[]))}\n\n## Files Forbidden To Modify\n{fl(rca.get('files_to_inspect_but_not_modify',[]))}\n\n## Forbidden Changes\n{bl(forb)}\n\n## Implementation Steps\n{bl(rca.get('implementation_plan',[]))}\n\n## Validation Commands\n{bl(rca.get('validation_plan',[]))}\n\n## E2E Retest Scenario\n- Re-run the failing scenario via agent-browser and confirm expected behavior.\n\n## Stop Conditions\n- If a required file does not exist, stop with PLAN_MISMATCH.\n- If implementation requires modifying files outside the allowlist, stop with PLAN_MISMATCH.\n- If validation failure is unrelated to the plan, stop and report.\n"
    (rd/"04-approved-plan.md").write_text(md, encoding="utf-8"); print(f"Wrote {rd/'04-approved-plan.md'} (approval={approval})"); return 0

def main(argv):
    prog=Path(argv[0]).name
    if prog=="validate-artifact": return command_validate(argv)
    if prog=="update-state": return command_update_state(argv)
    if prog=="init-round": return command_init_round(argv)
    if prog=="summarize-round": return command_summarize_round(argv)
    if prog=="doctor": return command_doctor(argv)
    if prog=="write-envelope": return command_write_envelope(argv)
    if prog=="validate-envelope": return command_validate_envelope(argv)
    if prog=="classify": return command_classify(argv)
    if prog=="build-approved-plan": return command_build_approved_plan(argv)
    if len(argv)>=2 and argv[1]=="config-value": return command_config_value([argv[0],*argv[2:]])
    print(f"unknown command entrypoint: {prog} {argv[1:]}", file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main(sys.argv))
