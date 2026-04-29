"""
Auto Responder - ClawShell v0.1
================================

自动响应器。
根据分析结果执行自动响应动作。

响应类型：
- 策略切换
- 告警通知
- 错误恢复
- 降级处理
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ResponseAction:
    """响应动作"""
    action_type: str           # action类型：switch_strategy, alert, retry, fallback
    target: str                 # 目标
    params: Dict[str, Any]     # 参数
    executed: bool = False     # 是否已执行
    executed_at: str = None    # 执行时间


class AutoResponder:
    """
    自动响应器
    ==========
    
    根据分析结果执行自动响应。
    
    使用示例：
        responder = AutoResponder()
        
        # 注册响应处理器
        @responder.on_action("switch_strategy")
        def handle_switch_strategy(action):
            switcher.switch_to(action.target)
        
        # 执行响应
        result = analyzer.analyze(metrics)
        responder.respond(result)
    """
    
    def __init__(self):
        # 动作处理器
        self._handlers: Dict[str, List[Callable]] = {}
        
        # 动作历史
        self._action_history: List[ResponseAction] = []
        
        # 是否启用
        self._enabled = True
        
        # 初始化默认处理器
        self._init_default_handlers()
        
        logger.info("AutoResponder initialized")
    
    def _init_default_handlers(self):
        """初始化默认处理器"""
        # 策略切换处理器
        @self.on_action("switch_strategy")
        def handle_switch_strategy(action: ResponseAction):
            try:
                from strategies import get_switcher
                switcher = get_switcher()
                success = switcher.switch_to(
                    action.target,
                    reason=f"Auto switch: {action.params.get('reason', 'unknown')}"
                )
                action.executed = True
                action.executed_at = datetime.now().isoformat()
                
                if success:
                    logger.info(f"Auto-switched to {action.target}")
                else:
                    logger.warning(f"Failed to auto-switch to {action.target}")
            except Exception as e:
                logger.error(f"Error in switch_strategy handler: {e}")
        
        # 告警处理器
        @self.on_action("alert")
        def handle_alert(action: ResponseAction):
            try:
                # 发布告警事件
                from eventbus import Publisher
                pub = Publisher(source="adaptor")
                
                severity = action.params.get("severity", "medium")
                message = action.params.get("message", "")
                
                pub.publish(
                    event_type=None,  # 使用自定义事件
                    payload={
                        "event_name": "auto_alert",
                        "severity": severity,
                        "message": message,
                        "triggered_at": datetime.now().isoformat(),
                    },
                    tags=["alert", severity],
                )
                
                action.executed = True
                action.executed_at = datetime.now().isoformat()
                
                logger.warning(f"Alert triggered: [{severity}] {message}")
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
        
        # 重试处理器
        @self.on_action("retry")
        def handle_retry(action: ResponseAction):
            # 重试逻辑由调用者实现
            action.executed = True
            action.executed_at = datetime.now().isoformat()
            logger.info(f"Retry action: {action.target}")
        
        # 降级处理器
        @self.on_action("fallback")
        def handle_fallback(action: ResponseAction):
            try:
                # 执行降级
                from eventbus import Publisher
                pub = Publisher(source="adaptor")
                
                pub.error_occurred(
                    error_type="fallback_triggered",
                    message=f"Fallback to {action.target}",
                    severity="high"
                )
                
                action.executed = True
                action.executed_at = datetime.now().isoformat()
                
                logger.warning(f"Fallback triggered: {action.target}")
            except Exception as e:
                logger.error(f"Error in fallback handler: {e}")
    
    def on_action(self, action_type: str) -> Callable:
        """
        装饰器：注册动作处理器
        
        Args:
            action_type: 动作类型
        
        Returns:
            装饰器函数
        """
        def decorator(handler: Callable[[ResponseAction], None]) -> Callable:
            if action_type not in self._handlers:
                self._handlers[action_type] = []
            self._handlers[action_type].append(handler)
            return handler
        return decorator
    
    def respond(self, analysis_result) -> List[ResponseAction]:
        """
        根据分析结果执行响应
        
        Args:
            analysis_result: AnalysisResult对象
        
        Returns:
            执行的响应动作列表
        """
        if not self._enabled:
            logger.debug("AutoResponder is disabled, skipping response")
            return []
        
        actions = []
        
        if analysis_result.should_switch:
            # 生成策略切换动作
            action = ResponseAction(
                action_type="switch_strategy",
                target=analysis_result.target_strategy,
                params={
                    "reason": analysis_result.reason,
                    "issues": analysis_result.issues,
                    "confidence": analysis_result.confidence,
                }
            )
            actions.append(action)
        
        # 检查是否需要告警
        if self._should_alert(analysis_result):
            alert_action = ResponseAction(
                action_type="alert",
                target="notification",
                params={
                    "severity": "high" if analysis_result.confidence > 0.8 else "medium",
                    "message": f"Issues detected: {', '.join(analysis_result.issues)}",
                    "issues": analysis_result.issues,
                }
            )
            actions.append(alert_action)
        
        # 执行动作
        executed_actions = []
        for action in actions:
            executed = self._execute_action(action)
            if executed:
                executed_actions.append(action)
        
        # 记录历史
        self._action_history.extend(executed_actions)
        
        # 保留最近100条
        self._action_history = self._action_history[-100:]
        
        return executed_actions
    
    def _execute_action(self, action: ResponseAction) -> bool:
        """
        执行单个动作
        
        Args:
            action: 响应动作
        
        Returns:
            是否执行成功
        """
        handlers = self._handlers.get(action.action_type, [])
        
        if not handlers:
            logger.warning(f"No handler for action type: {action.action_type}")
            return False
        
        for handler in handlers:
            try:
                handler(action)
            except Exception as e:
                logger.error(f"Handler error for {action.action_type}: {e}")
                return False
        
        return True
    
    def _should_alert(self, analysis_result) -> bool:
        """判断是否需要告警"""
        # 高置信度的策略切换需要告警
        if analysis_result.should_switch and analysis_result.confidence > 0.85:
            return True
        
        # 多问题同时发生需要告警
        if len(analysis_result.issues) > 2:
            return True
        
        return False
    
    def get_action_history(self, limit: int = 20) -> List[Dict]:
        """
        获取动作历史
        
        Args:
            limit: 返回数量限制
        
        Returns:
            动作历史列表
        """
        history = self._action_history[-limit:]
        return [
            {
                "action_type": a.action_type,
                "target": a.target,
                "executed": a.executed,
                "executed_at": a.executed_at,
            }
            for a in history
        ]
    
    def enable(self):
        """启用自动响应"""
        self._enabled = True
        logger.info("AutoResponder enabled")
    
    def disable(self):
        """禁用自动响应"""
        self._enabled = False
        logger.info("AutoResponder disabled")
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled


# 全局单例
_responder: Optional[AutoResponder] = None


def get_responder() -> AutoResponder:
    """获取全局自动响应器实例"""
    global _responder
    if _responder is None:
        _responder = AutoResponder()
    return _responder
