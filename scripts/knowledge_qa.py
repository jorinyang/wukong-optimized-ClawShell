#!/usr/bin/env python3
"""
Knowledge QA - 知识问答主脚本
功能：
1. 接收用户问题
2. 意图解析
3. 语义搜索
4. 答案生成
5. 返回结果

用法:
    python3 knowledge_qa.py "问题内容"
    echo "问题" | python3 knowledge_qa.py --stdin
"""

import sys
import json
import os
from pathlib import Path

# 添加脚本目录到路径
SCRIPT_DIR = Path(__file__).parent

# 导入模块
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from qa_intent_parser import parse_intent, format_intent_report
    from qa_semantic_search import search_knowledge, format_search_results
    from qa_answer_generator import generate_answer, format_final_response
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)

# ==================== 主函数 ====================

def process_question(question: str) -> dict:
    """处理问题"""
    if not question or not question.strip():
        return {
            "success": False,
            "error": "问题不能为空"
        }
    
    question = question.strip()
    
    # 1. 意图解析
    parsed = parse_intent(question)
    
    # 2. 语义搜索
    search_results = search_knowledge(
        query=parsed["search_query"],
        intent=parsed["primary_intent"]
    )
    
    # 3. 答案生成
    qa_result = generate_answer(
        question=question,
        intent=parsed["primary_intent"],
        search_results=search_results
    )
    
    # 4. 格式化最终回复
    final_response = format_final_response(qa_result, question)
    
    return {
        "success": True,
        "question": question,
        "intent": parsed["primary_intent"],
        "search_query": parsed["search_query"],
        "result_count": len(search_results),
        "answer": final_response,
        "confidence": qa_result["confidence"],
        "sources": qa_result["sources"]
    }

def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--stdin":
            # 从stdin读取
            question = sys.stdin.read().strip()
        elif sys.argv[1] == "--help":
            print("用法:")
            print("  python3 knowledge_qa.py \"问题\"")
            print("  echo \"问题\" | python3 knowledge_qa.py --stdin")
            print("  python3 knowledge_qa.py --json '{\"question\": \"...\"}'")
            sys.exit(0)
        elif sys.argv[1] == "--json":
            # JSON格式输入
            try:
                data = json.loads(sys.argv[2])
                question = data.get("question", "")
            except:
                print("❌ JSON格式错误")
                sys.exit(1)
        else:
            question = " ".join(sys.argv[1:])
    else:
        # 交互模式
        print("=" * 60)
        print("  Knowledge QA - 知识问答")
        print("=" * 60)
        print("输入问题（输入 q 退出）:")
        question = input("\n> ").strip()
        if question.lower() == "q":
            sys.exit(0)
    
    if not question:
        print("❌ 问题不能为空")
        sys.exit(1)
    
    # 处理问题
    result = process_question(question)
    
    # 输出结果
    if result["success"]:
        print("\n" + "=" * 60)
        print(f"问题: {result['question']}")
        print(f"意图: {result['intent']}")
        print(f"置信度: {result['confidence']:.0%}")
        print("=" * 60)
        print("\n" + result["answer"])
    else:
        print(f"❌ 处理失败: {result.get('error')}")

if __name__ == "__main__":
    main()
