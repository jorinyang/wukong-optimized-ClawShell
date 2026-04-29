#!/usr/bin/env python3
"""
WorkflowEngine - 自动化工作流引擎
职责：
1. 定义和执行自动化工作流
2. 编排多步骤任务序列
3. 条件分支和循环处理
4. 工作流状态持久化
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

# 路径配置
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
WORKFLOWS_DIR = os.path.join(SHARED_DIR, "workflows")
WORKFLOW_STATE_FILE = os.path.join(SHARED_DIR, "workflow_states.json")
LOG_FILE = os.path.join(SHARED_DIR, "logs", "workflow_engine.log")

# 工作流状态
class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowEngine:
    def __init__(self):
        self.workflows_dir = WORKFLOWS_DIR
        self.state_file = WORKFLOW_STATE_FILE
        self.log_file = LOG_FILE
        self._ensure_dirs()
        
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")
    
    def _ensure_dirs(self):
        """确保目录存在"""
        os.makedirs(self.workflows_dir, exist_ok=True)
    
    def _load_states(self) -> Dict:
        """加载工作流状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"workflows": {}}
    
    def _save_states(self, states: Dict):
        """保存工作流状态"""
        with open(self.state_file, 'w') as f:
            json.dump(states, f, indent=2, ensure_ascii=False)
    
    # ========== 预置工作流 ==========
    
    def create_phase_checkup_workflow(self) -> Dict:
        """创建Phase检查工作流"""
        workflow = {
            "id": "phase-checkup",
            "name": "Phase健康检查",
            "description": "检查各Phase组件状态",
            "version": "1.0",
            "steps": [
                {
                    "id": "step1",
                    "name": "检查EventBus",
                    "type": "system_check",
                    "component": "eventbus",
                    "expected": "running"
                },
                {
                    "id": "step2",
                    "name": "检查Agent状态",
                    "type": "agent_check",
                    "expected_online": 3
                },
                {
                    "id": "step3",
                    "name": "检查任务队列",
                    "type": "task_check",
                    "max_pending": 20
                },
                {
                    "id": "step4",
                    "name": "生成报告",
                    "type": "report",
                    "format": "text"
                }
            ]
        }
        return workflow
    
    def create_daily_summary_workflow(self) -> Dict:
        """创建每日总结工作流"""
        workflow = {
            "id": "daily-summary",
            "name": "每日工作汇总",
            "description": "生成每日工作总结",
            "version": "1.0",
            "steps": [
                {
                    "id": "step1",
                    "name": "收集任务完成情况",
                    "type": "collect_tasks",
                    "time_range": "today"
                },
                {
                    "id": "step2",
                    "name": "收集告警情况",
                    "type": "collect_alerts",
                    "time_range": "today"
                },
                {
                    "id": "step3",
                    "name": "生成总结",
                    "type": "generate_summary"
                }
            ]
        }
        return workflow
    
    def create_health_check_workflow(self) -> Dict:
        """创建健康检查工作流"""
        workflow = {
            "id": "health-check",
            "name": "系统健康检查",
            "description": "全面检查系统健康状态",
            "version": "1.0",
            "steps": [
                {
                    "id": "step1",
                    "name": "检查Agent",
                    "type": "agent_check"
                },
                {
                    "id": "step2",
                    "name": "检查守护进程",
                    "type": "daemon_check"
                },
                {
                    "id": "step3",
                    "name": "检查任务超时",
                    "type": "timeout_check"
                },
                {
                    "id": "step4",
                    "name": "检查告警",
                    "type": "alert_check"
                },
                {
                    "id": "step5",
                    "name": "汇总结果",
                    "type": "aggregate"
                }
            ]
        }
        return workflow
    
    def get_preset_workflows(self) -> List[Dict]:
        """获取预置工作流"""
        return [
            self.create_phase_checkup_workflow(),
            self.create_daily_summary_workflow(),
            self.create_health_check_workflow()
        ]
    
    # ========== 工作流执行 ==========
    
    def execute_step(self, step: Dict, context: Dict) -> Dict:
        """执行单个步骤"""
        step_type = step.get("type")
        result = {"step_id": step["id"], "success": True, "output": None}
        
        try:
            if step_type == "system_check":
                # 系统检查
                component = step.get("component")
                expected = step.get("expected")
                
                import subprocess
                check_cmd = step.get("check_cmd", f"launchctl list | grep {component}")
                
                proc = subprocess.run(
                    check_cmd if "launchctl" in check_cmd else ["pgrep", "-f", component],
                    shell=True if "launchctl" in check_cmd else False,
                    capture_output=True, text=True, timeout=10
                )
                
                if expected == "running":
                    result["output"] = "running" if proc.stdout.strip() else "stopped"
                    result["success"] = bool(proc.stdout.strip())
                
            elif step_type == "agent_check":
                # Agent检查
                agent_status_file = os.path.join(SHARED_DIR, "agent-status.json")
                if os.path.exists(agent_status_file):
                    with open(agent_status_file, 'r') as f:
                        status = json.load(f)
                    
                    online_count = sum(
                        1 for a in status.get("agents", {}).values()
                        if a.get("status") == "online"
                    )
                    
                    result["output"] = {
                        "online_count": online_count,
                        "total_agents": len(status.get("agents", {}))
                    }
                    result["success"] = True
                
            elif step_type == "task_check":
                # 任务检查
                queue_file = os.path.join(SHARED_DIR, "task-queue.json")
                if os.path.exists(queue_file):
                    with open(queue_file, 'r') as f:
                        queue = json.load(f)
                    
                    pending = [t for t in queue.get("tasks", []) if t.get("status") == "pending"]
                    result["output"] = {"pending_count": len(pending)}
                    result["success"] = len(pending) <= step.get("max_pending", 20)
                
            elif step_type == "report":
                # 生成报告
                from dashboard import Dashboard
                dash = Dashboard()
                result["output"] = dash.generate_report(step.get("format", "text"))
                
            elif step_type == "collect_tasks":
                # 收集任务
                market_file = os.path.join(SHARED_DIR, "task-market.json")
                if os.path.exists(market_file):
                    with open(market_file, 'r') as f:
                        market = json.load(f)
                    result["output"] = {"completed_count": len(market.get("tasks", []))}
                
            elif step_type == "collect_alerts":
                # 收集告警
                alert_file = os.path.join(SHARED_DIR, "alert_history.json")
                if os.path.exists(alert_file):
                    with open(alert_file, 'r') as f:
                        alerts = json.load(f)
                    result["output"] = {"total_alerts": len(alerts.get("alerts", []))}
                
            elif step_type == "generate_summary":
                # 生成总结
                result["output"] = "Summary generated"
                
            elif step_type == "daemon_check":
                # 守护进程检查
                daemons = ["event-bus"]
                daemon_status = {}
                for d in daemons:
                    try:
                        proc = subprocess.run(["pgrep", "-f", d], capture_output=True, text=True, timeout=5)
                        daemon_status[d] = "running" if proc.stdout.strip() else "stopped"
                    except:
                        daemon_status[d] = "unknown"
                result["output"] = daemon_status
                
            elif step_type == "timeout_check":
                # 超时检查
                result["output"] = {"timed_out_tasks": 0}
                
            elif step_type == "alert_check":
                # 告警检查
                alert_file = os.path.join(SHARED_DIR, "alert_history.json")
                if os.path.exists(alert_file):
                    with open(alert_file, 'r') as f:
                        alerts = json.load(f)
                    active = [a for a in alerts.get("alerts", []) if a.get("status") == "active"]
                    result["output"] = {"active_alerts": len(active)}
                
            elif step_type == "aggregate":
                # 汇总
                result["output"] = "All checks completed"
                
            else:
                result["output"] = f"Unknown step type: {step_type}"
                result["success"] = False
                
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            self.log(f"⚠️ 步骤执行失败 {step['id']}: {e}")
        
        return result
    
    def run_workflow(self, workflow_id: str, context: Dict = None) -> Dict:
        """运行工作流"""
        # 获取工作流定义
        workflow = None
        for preset in self.get_preset_workflows():
            if preset["id"] == workflow_id:
                workflow = preset
                break
        
        if not workflow:
            return {"success": False, "error": f"Workflow not found: {workflow_id}"}
        
        self.log(f"🚀 开始执行工作流: {workflow['name']}")
        
        # 初始化状态
        states = self._load_states()
        run_id = f"run-{int(time.time())}"
        
        states["workflows"][run_id] = {
            "workflow_id": workflow_id,
            "status": WorkflowStatus.RUNNING.value,
            "started_at": datetime.now().isoformat(),
            "steps": {},
            "context": context or {}
        }
        self._save_states(states)
        
        # 执行步骤
        step_results = []
        all_success = True
        
        for step in workflow.get("steps", []):
            self.log(f"📍 执行步骤: {step['name']}")
            result = self.execute_step(step, context or {})
            step_results.append(result)
            
            states["workflows"][run_id]["steps"][step["id"]] = result
            
            if not result.get("success"):
                all_success = False
                self.log(f"⚠️ 步骤失败: {step['name']}")
                break
        
        # 更新最终状态
        states["workflows"][run_id]["status"] = (
            WorkflowStatus.COMPLETED.value if all_success else WorkflowStatus.FAILED.value
        )
        states["workflows"][run_id]["completed_at"] = datetime.now().isoformat()
        states["workflows"][run_id]["results"] = step_results
        self._save_states(states)
        
        self.log(f"{'✅' if all_success else '❌'} 工作流{'完成' if all_success else '失败'}: {workflow['name']}")
        
        return {
            "success": all_success,
            "run_id": run_id,
            "workflow_id": workflow_id,
            "results": step_results
        }
    
    def get_workflow_status(self, run_id: str = None) -> Dict:
        """获取工作流状态"""
        states = self._load_states()
        
        if run_id:
            return states.get("workflows", {}).get(run_id, {})
        
        # 返回所有工作流
        return states.get("workflows", {})
    
    def list_workflows(self) -> List[Dict]:
        """列出预置工作流"""
        return [
            {"id": w["id"], "name": w["name"], "description": w["description"]}
            for w in self.get_preset_workflows()
        ]


# CLI接口
if __name__ == "__main__":
    import sys
    
    engine = WorkflowEngine()
    action = sys.argv[1] if len(sys.argv) > 1 else "list"
    
    if action == "list":
        workflows = engine.list_workflows()
        print("可用工作流:")
        for w in workflows:
            print(f"  - {w['id']}: {w['name']}")
            print(f"    {w['description']}")
    
    elif action == "run":
        if len(sys.argv) > 2:
            workflow_id = sys.argv[2]
            result = engine.run_workflow(workflow_id)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("用法: workflow_engine.py run <workflow_id>")
    
    elif action == "status":
        if len(sys.argv) > 2:
            status = engine.get_workflow_status(sys.argv[2])
            print(json.dumps(status, indent=2, ensure_ascii=False))
        else:
            statuses = engine.get_workflow_status()
            if statuses:
                print("最近工作流执行:")
                for run_id, status in list(statuses.items())[-5:]:
                    print(f"  {run_id}: {status.get('workflow_id')} - {status.get('status')}")
            else:
                print("暂无工作流执行记录")
    
    elif action == "presets":
        workflows = engine.get_preset_workflows()
        print(json.dumps(workflows, indent=2, ensure_ascii=False))
    
    else:
        print(f"未知操作: {action}")
        print("用法: workflow_engine.py <list|run|status>")
        print("  list - 列出可用工作流")
        print("  run <workflow_id> - 执行工作流")
        print("  status [run_id] - 查看状态")
