#!/usr/bin/env python3
"""
QA Integration - 智能问答集成脚本
功能：
1. 集成所有QA模块
2. 统一入口
3. 错误处理
4. 性能优化
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ==================== 配置 ====================

SCRIPT_DIR = Path.home() / ".openclaw/scripts"
LOG_DIR = Path.home() / ".openclaw/logs"
OUTPUT_DIR = Path.home() / ".openclaw/reports"

# ==================== 集成管理器 ====================

class QAIntegrator:
    def __init__(self):
        self.modules = {}
        self.load_modules()
        self.log_dir = LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def load_modules(self):
        """加载所有模块"""
        sys.path.insert(0, str(SCRIPT_DIR))
        
        try:
            from qa_intent_parser import parse_intent, format_intent_report
            self.modules["intent_parser"] = {
                "parse": parse_intent,
                "format": format_intent_report,
                "loaded": True
            }
        except Exception as e:
            self.modules["intent_parser"] = {"loaded": False, "error": str(e)}
        
        try:
            from qa_semantic_search import search_knowledge, format_search_results
            self.modules["semantic_search"] = {
                "search": search_knowledge,
                "format": format_search_results,
                "loaded": True
            }
        except Exception as e:
            self.modules["semantic_search"] = {"loaded": False, "error": str(e)}
        
        try:
            from qa_answer_generator import generate_answer, format_final_response
            self.modules["answer_generator"] = {
                "generate": generate_answer,
                "format": format_final_response,
                "loaded": True
            }
        except Exception as e:
            self.modules["answer_generator"] = {"loaded": False, "error": str(e)}
        
        try:
            from qa_conversation_manager import ConversationManager
            self.modules["conversation_manager"] = {
                "manager": ConversationManager(),
                "loaded": True
            }
        except Exception as e:
            self.modules["conversation_manager"] = {"loaded": False, "error": str(e)}
        
        try:
            from qa_context_memory import ContextMemory
            self.modules["context_memory"] = {
                "memory": ContextMemory(),
                "loaded": True
            }
        except Exception as e:
            self.modules["context_memory"] = {"loaded": False, "error": str(e)}
        
        try:
            from qa_multi_turn import MultiTurnHandler
            self.modules["multi_turn"] = {
                "handler": MultiTurnHandler(),
                "loaded": True
            }
        except Exception as e:
            self.modules["multi_turn"] = {"loaded": False, "error": str(e)}
    
    def check_health(self) -> Dict:
        """检查模块健康状态"""
        results = {}
        for name, module in self.modules.items():
            results[name] = {
                "loaded": module.get("loaded", False),
                "error": module.get("error", None)
            }
        return results
    
    def process_question(self, question: str, user_id: str = "default", use_multi_turn: bool = False) -> Dict:
        """处理问题"""
        start_time = time.time()
        
        # 1. 解析意图
        if "intent_parser" not in self.modules or not self.modules["intent_parser"].get("loaded"):
            return {"error": "意图解析模块未加载"}
        
        intent = self.modules["intent_parser"]["parse"](question)
        
        # 2. 搜索
        if "semantic_search" not in self.modules or not self.modules["semantic_search"].get("loaded"):
            return {"error": "搜索模块未加载"}
        
        results = self.modules["semantic_search"]["search"](
            query=intent["search_query"],
            intent=intent["primary_intent"]
        )
        
        # 3. 生成答案
        if "answer_generator" not in self.modules or not self.modules["answer_generator"].get("loaded"):
            return {"error": "答案生成模块未加载"}
        
        answer_result = self.modules["answer_generator"]["generate"](
            question=question,
            intent=intent["primary_intent"],
            search_results=results
        )
        
        elapsed = time.time() - start_time
        
        return {
            "success": True,
            "question": question,
            "user_id": user_id,
            "intent": intent["primary_intent"],
            "search_results_count": len(results),
            "answer": answer_result["answer"],
            "confidence": answer_result["confidence"],
            "sources": answer_result.get("sources", []),
            "elapsed_seconds": round(elapsed, 3),
            "timestamp": datetime.now().isoformat()
        }
    
    def run_diagnostics(self) -> Dict:
        """运行诊断"""
        health = self.check_health()
        
        all_loaded = all(m.get("loaded", False) for m in health.values())
        
        return {
            "status": "healthy" if all_loaded else "degraded",
            "all_modules_loaded": all_loaded,
            "modules": health,
            "timestamp": datetime.now().isoformat()
        }

# ==================== 主函数 ====================

def main():
    integrator = QAIntegrator()
    
    if len(sys.argv) < 2:
        # 诊断模式
        print("=" * 60)
        print("      QA System Diagnostics")
        print("=" * 60)
        
        diag = integrator.run_diagnostics()
        print(f"\n状态: {diag['status']}")
        print(f"所有模块加载: {'✅' if diag['all_modules_loaded'] else '❌'}")
        print("\n模块状态:")
        for name, status in diag["modules"].items():
            icon = "✅" if status["loaded"] else "❌"
            error = f" - {status['error']}" if status.get("error") else ""
            print(f"  {icon} {name}{error}")
        
        print("\n" + "=" * 60)
        return
    
    command = sys.argv[1]
    
    if command == "diagnose":
        diag = integrator.run_diagnostics()
        print(json.dumps(diag, ensure_ascii=False, indent=2))
    
    elif command == "ask":
        question = sys.argv[2] if len(sys.argv) > 2 else "测试问题"
        user_id = sys.argv[3] if len(sys.argv) > 3 else "default"
        
        result = integrator.process_question(question, user_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif command == "health":
        health = integrator.check_health()
        all_ok = all(m.get("loaded", False) for m in health.values())
        print("healthy" if all_ok else "degraded")
    
    else:
        print(f"未知命令: {command}")
        print("用法:")
        print("  python3 qa_integrate.py diagnose")
        print("  python3 qa_integrate.py ask <问题> [用户ID]")
        print("  python3 qa_integrate.py health")

if __name__ == "__main__":
    main()
