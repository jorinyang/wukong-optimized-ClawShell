"""
N8N Integration - TaskMarket 与 n8n 集成模块
ClawShell v0.8 核心模块

负责将 TaskMarket 任务分发到 n8n 工作流。
"""

import requests
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from organizer import Task, TaskMarket

logger = logging.getLogger(__name__)


class N8NIntegration:
    """
    N8N 集成器
    
    负责 TaskMarket 与 n8n 工作流的集成。
    
    Example:
        integration = N8NIntegration(
            base_url="http://localhost:5678",
            api_key="your-api-key"
        )
        
        # 触发工作流
        integration.trigger_workflow(
            workflow_id="workflow-id",
            data={"task_id": "task-123"}
        )
    """
    
    def __init__(self, base_url: str = "http://localhost:5678", 
                 api_key: str = None):
        """
        初始化 N8N 集成器
        
        Args:
            base_url: n8n 基础 URL
            api_key: n8n API 密钥
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({
                "X-N8N-API-KEY": api_key
            })
        
        logger.info(f"N8NIntegration initialized: {base_url}")
    
    def trigger_workflow(self, workflow_id: str, data: Dict = None) -> bool:
        """
        触发工作流
        
        Args:
            workflow_id: 工作流 ID
            data: 触发数据
        
        Returns:
            是否成功触发
        """
        try:
            url = f"{self.base_url}/api/v1/workflows/{workflow_id}/execute"
            
            response = self.session.post(
                url,
                json={"data": data or {}}
            )
            
            if response.status_code == 200:
                logger.info(f"Triggered workflow: {workflow_id}")
                return True
            else:
                logger.warning(f"Failed to trigger workflow: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Error triggering workflow: {e}")
            return False
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """
        获取工作流状态
        
        Args:
            workflow_id: 工作流 ID
        
        Returns:
            工作流状态或 None
        """
        try:
            url = f"{self.base_url}/api/v1/workflows/{workflow_id}"
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get workflow status: {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"Error getting workflow status: {e}")
            return None
    
    def list_workflows(self) -> List[Dict]:
        """
        列出工作流
        
        Returns:
            工作流列表
        """
        try:
            url = f"{self.base_url}/api/v1/workflows"
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                logger.warning(f"Failed to list workflows: {response.status_code}")
                return []
        
        except Exception as e:
            logger.error(f"Error listing workflows: {e}")
            return []
    
    def activate_workflow(self, workflow_id: str) -> bool:
        """
        激活工作流
        
        Args:
            workflow_id: 工作流 ID
        
        Returns:
            是否成功激活
        """
        try:
            url = f"{self.base_url}/api/v1/workflows/{workflow_id}/activate"
            
            response = self.session.post(url)
            
            if response.status_code == 200:
                logger.info(f"Activated workflow: {workflow_id}")
                return True
            else:
                logger.warning(f"Failed to activate workflow: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Error activating workflow: {e}")
            return False
    
    def deactivate_workflow(self, workflow_id: str) -> bool:
        """
        停用工作流
        
        Args:
            workflow_id: 工作流 ID
        
        Returns:
            是否成功停用
        """
        try:
            url = f"{self.base_url}/api/v1/workflows/{workflow_id}/deactivate"
            
            response = self.session.post(url)
            
            if response.status_code == 200:
                logger.info(f"Deactivated workflow: {workflow_id}")
                return True
            else:
                logger.warning(f"Failed to deactivate workflow: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Error deactivating workflow: {e}")
            return False


class TaskMarketN8NBridge:
    """
    TaskMarket 与 n8n 桥接器
    
    负责将 TaskMarket 任务自动分发到 n8n 工作流。
    """
    
    def __init__(self, task_market: TaskMarket, n8n_integration: N8NIntegration):
        """
        初始化桥接器
        
        Args:
            task_market: 任务市场
            n8n_integration: n8n 集成器
        """
        self.task_market = task_market
        self.n8n = n8n_integration
        self._workflow_mapping: Dict[str, str] = {}  # category -> workflow_id
        
        logger.info("TaskMarketN8NBridge initialized")
    
    def register_workflow(self, category: str, workflow_id: str) -> None:
        """
        注册类别对应的工作流
        
        Args:
            category: 任务类别
            workflow_id: 工作流 ID
        """
        self._workflow_mapping[category] = workflow_id
        logger.info(f"Registered workflow for {category}: {workflow_id}")
    
    def submit_task_to_n8n(self, name: str, description: str = "",
                          category: str = "general", data: Dict = None) -> Optional[Task]:
        """
        提交任务到 n8n
        
        Args:
            name: 任务名称
            description: 任务描述
            category: 任务类别
            data: 附加数据
        
        Returns:
            创建的任务或 None
        """
        # 提交到 TaskMarket
        task = self.task_market.submit(
            name=name,
            description=description,
            category=category,
            metadata=data or {}
        )
        
        # 触发对应的 n8n 工作流
        workflow_id = self._workflow_mapping.get(category)
        if workflow_id:
            success = self.n8n.trigger_workflow(
                workflow_id=workflow_id,
                data={
                    "task_id": task.id,
                    "task_name": task.name,
                    "task_category": task.category,
                    "task_data": data
                }
            )
            
            if success:
                logger.info(f"Task {task.id} triggered n8n workflow {workflow_id}")
            else:
                logger.warning(f"Failed to trigger n8n workflow for task {task.id}")
        else:
            logger.info(f"No n8n workflow registered for category: {category}")
        
        return task
    
    def get_bridge_stats(self) -> Dict:
        """
        获取桥接统计
        
        Returns:
            统计字典
        """
        return {
            "registered_categories": len(self._workflow_mapping),
            "category_mapping": self._workflow_mapping.copy(),
            "market_stats": self.task_market.get_market_stats(),
        }
