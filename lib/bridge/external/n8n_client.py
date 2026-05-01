#!/usr/bin/env python3
"""
ClawShell N8N 客户端
版本: v0.2.2-A
功能: N8N工作流触发、状态回调、结果获取
"""

import os
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import urllib.request
import urllib.error
import urllib.parse

# ============ 配置 ============

N8N_CONFIG_PATH = Path("~/.real/.n8n_config.json").expanduser()
N8N_STATE_PATH = Path("~/.real/.n8n_state.json").expanduser()


# ============ 数据结构 ============

class WorkflowStatus(Enum):
    """工作流状态"""
    UNKNOWN = "unknown"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class WorkflowInfo:
    """工作流信息"""
    id: str
    name: str
    status: WorkflowStatus
    active: bool
    nodes_count: int = 0
    last_execution: Optional[float] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class ExecutionInfo:
    """执行信息"""
    execution_id: str
    workflow_id: str
    status: str  # started, running, success, error, waiting
    started_at: float
    finished_at: Optional[float] = None
    mode: str = "manual"  # manual, triggered, webhook
    result: Optional[Dict] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "mode": self.mode,
            "result": self.result,
            "error": self.error
        }


@dataclass
class TriggerResult:
    """触发结果"""
    success: bool
    execution_id: Optional[str] = None
    message: str = ""
    data: Optional[Dict] = None
    error: Optional[str] = None


# ============ N8N 客户端 ============

class N8NClient:
    """N8N客户端"""
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        # 加载配置
        config = self._load_config()
        
        self.base_url = (base_url or config.get("base_url", "http://localhost:5680")).rstrip("/")
        self.api_key = api_key or config.get("api_key", "")
        self.timeout = config.get("timeout", 30)
        
        self._executions: Dict[str, ExecutionInfo] = {}
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if N8N_CONFIG_PATH.exists():
            try:
                with open(N8N_CONFIG_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_config(self):
        """保存配置"""
        config = {
            "base_url": self.base_url,
            "api_key": self.api_key,
            "timeout": self.timeout
        }
        with open(N8N_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        
        req = urllib.request.Request(url, method=method)
        req.add_header("Content-Type", "application/json")
        
        if self.api_key:
            req.add_header("X-N8N-API-KEY", self.api_key)
        
        if data:
            req.data = json.dumps(data).encode("utf-8")
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8")
                if content:
                    return json.loads(content)
                return {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise N8NError(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise N8NError(f"Connection failed: {e}")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = self._make_request("GET", "/healthz")
            return response.get("status") == "ok"
        except:
            return False
    
    # ---- 工作流管理 ----
    
    def list_workflows(self) -> List[WorkflowInfo]:
        """列出所有工作流"""
        try:
            response = self._make_request("GET", "/workflows")
            workflows = response.get("data", []) if isinstance(response, dict) else response
            
            result = []
            for wf in workflows:
                result.append(WorkflowInfo(
                    id=wf.get("id", ""),
                    name=wf.get("name", "Unknown"),
                    status=WorkflowStatus.ACTIVE if wf.get("active") else WorkflowStatus.INACTIVE,
                    active=wf.get("active", False),
                    nodes_count=len(wf.get("nodes", []))
                ))
            return result
        except N8NError as e:
            print(f"列出工作流失败: {e}")
            return []
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowInfo]:
        """获取工作流信息"""
        try:
            response = self._make_request("GET", f"/workflows/{workflow_id}")
            
            if isinstance(response, dict) and response.get("data"):
                wf = response["data"]
            else:
                wf = response
            
            return WorkflowInfo(
                id=wf.get("id", ""),
                name=wf.get("name", "Unknown"),
                status=WorkflowStatus.ACTIVE if wf.get("active") else WorkflowStatus.INACTIVE,
                active=wf.get("active", False),
                nodes_count=len(wf.get("nodes", [])),
                metadata=wf
            )
        except N8NError:
            return None
    
    def trigger_workflow(self, workflow_id: str, params: Optional[Dict] = None, 
                         wait_for_response: bool = True, timeout: int = 60) -> TriggerResult:
        """
        触发工作流
        
        Args:
            workflow_id: 工作流ID
            params: 传递给工作流的参数
            wait_for_response: 是否等待执行结果
            timeout: 等待超时（秒）
        
        Returns:
            TriggerResult
        """
        try:
            # 准备负载
            payload = {
                "data": params or {},
                "executionId": str(uuid.uuid4())
            }
            
            # 触发工作流
            response = self._make_request("POST", f"/webhook/{workflow_id}", payload)
            
            if not wait_for_response:
                return TriggerResult(
                    success=True,
                    message="Workflow triggered"
                )
            
            # 轮询执行状态
            execution_id = response.get("executionId") or response.get("data", {}).get("executionId")
            
            if not execution_id:
                # 可能工作流直接返回了结果
                return TriggerResult(
                    success=True,
                    message="Workflow completed",
                    data=response
                )
            
            # 等待执行完成
            start_time = time.time()
            while time.time() - start_time < timeout:
                exec_info = self.get_execution_status(execution_id)
                if not exec_info:
                    return TriggerResult(success=False, error="Execution not found")
                
                if exec_info.status in ["success", "error", "finished"]:
                    return TriggerResult(
                        success=exec_info.status == "success",
                        execution_id=execution_id,
                        message=f"Execution {exec_info.status}",
                        result=exec_info.result,
                        error=exec_info.error
                    )
                
                time.sleep(1)
            
            return TriggerResult(
                success=False,
                execution_id=execution_id,
                error="Timeout waiting for execution"
            )
            
        except N8NError as e:
            return TriggerResult(success=False, error=str(e))
    
    # ---- 执行管理 ----
    
    def get_execution_status(self, execution_id: str) -> Optional[ExecutionInfo]:
        """获取执行状态"""
        try:
            response = self._make_request("GET", f"/executions/{execution_id}")
            
            if isinstance(response, dict):
                data = response.get("data", response)
            else:
                data = response
            
            return ExecutionInfo(
                execution_id=execution_id,
                workflow_id=data.get("workflowId", ""),
                status=data.get("status", "unknown"),
                started_at=data.get("startedAt", time.time()),
                finished_at=data.get("finishedAt"),
                mode=data.get("mode", "manual"),
                result=data.get("data", {}).get("resultData"),
                error=data.get("data", {}).get("error", {}).get("message") if data.get("data") else None
            )
        except N8NError:
            return None
    
    def list_executions(self, workflow_id: Optional[str] = None, limit: int = 10) -> List[ExecutionInfo]:
        """列出执行记录"""
        try:
            endpoint = "/executions"
            if workflow_id:
                endpoint += f"?workflowId={workflow_id}"
            
            response = self._make_request("GET", endpoint)
            
            executions = response.get("data", []) if isinstance(response, dict) else response
            
            result = []
            for exec_data in executions[:limit]:
                if isinstance(exec_data, dict):
                    result.append(ExecutionInfo(
                        execution_id=exec_data.get("id", ""),
                        workflow_id=exec_data.get("workflowId", ""),
                        status=exec_data.get("status", "unknown"),
                        started_at=exec_data.get("startedAt", time.time()),
                        finished_at=exec_data.get("finishedAt"),
                        mode=exec_data.get("mode", "manual")
                    ))
            
            return result
        except N8NError:
            return []
    
    def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        try:
            self._make_request("DELETE", f"/executions/{execution_id}")
            return True
        except:
            return False


class N8NError(Exception):
    """N8N错误"""
    pass


# ============ N8N Webhook 处理器 ============

class N8NWebhookHandler:
    """N8N Webhook处理器"""
    
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.registered_handlers: Dict[str, Callable] = {}
    
    def register(self, workflow_id: str, handler: Callable[[Dict], None]):
        """注册webhook处理器"""
        self.registered_handlers[workflow_id] = handler
    
    def unregister(self, workflow_id: str):
        """注销webhook处理器"""
        if workflow_id in self.registered_handlers:
            del self.registered_handlers[workflow_id]
    
    def handle(self, workflow_id: str, data: Dict) -> bool:
        """处理webhook回调"""
        handler = self.registered_handlers.get(workflow_id)
        
        if not handler:
            print(f"No handler registered for workflow {workflow_id}")
            return False
        
        try:
            handler(data)
            return True
        except Exception as e:
            print(f"Handler error: {e}")
            return False
    
    def handle_callback(self, execution_id: str, status: str, result: Optional[Dict] = None):
        """处理通用回调"""
        if self.callback:
            self.callback({
                "execution_id": execution_id,
                "status": status,
                "result": result
            })


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell N8N客户端")
    parser.add_argument("--url", default="http://localhost:5680", help="N8N URL")
    parser.add_argument("--list", action="store_true", help="列出工作流")
    parser.add_argument("--trigger", metavar="ID", help="触发工作流")
    parser.add_argument("--status", metavar="ID", help="查看执行状态")
    parser.add_argument("--health", action="store_true", help="健康检查")
    args = parser.parse_args()
    
    client = N8NClient(base_url=args.url)
    
    if args.health:
        health = client.health_check()
        print(f"{'✅' if health else '❌'} N8N {'正常' if health else '异常'}")
    
    elif args.list:
        workflows = client.list_workflows()
        print(f"工作流列表 ({len(workflows)} 个):")
        for wf in workflows:
            status_icon = "✅" if wf.active else "❌"
            print(f"  {status_icon} [{wf.id}] {wf.name}")
    
    elif args.trigger:
        result = client.trigger_workflow(args.trigger, wait_for_response=False)
        if result.success:
            print(f"✅ 工作流已触发: {result.message}")
            if result.execution_id:
                print(f"   执行ID: {result.execution_id}")
        else:
            print(f"❌ 触发失败: {result.error}")
    
    elif args.status:
        exec_info = client.get_execution_status(args.status)
        if exec_info:
            print(f"执行ID: {exec_info.execution_id}")
            print(f"状态: {exec_info.status}")
            print(f"模式: {exec_info.mode}")
            print(f"开始时间: {time.ctime(exec_info.started_at)}")
            if exec_info.finished_at:
                print(f"结束时间: {time.ctime(exec_info.finished_at)}")
            if exec_info.error:
                print(f"错误: {exec_info.error}")
        else:
            print(f"❌ 执行 {args.status} 不存在")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
