#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速测试脚本"""
import asyncio
from agent_recheck.analyzer.llm.client import LLMClient
from agent_recheck.analyzer.parser.docx_parser import DocxParser
import json

async def test():
    # 加载 ground truth
    with open('tests/fixtures/sample_case_001.json', 'r', encoding='utf-8') as f:
        gt_data = json.load(f)

    gt_issues = [
        (item['text'], item['category'], item['severity'])
        for item in gt_data['expected_issues']
    ]

    print("=== Ground Truth (8个预期问题) ===")
    for i, (text, cat, sev) in enumerate(gt_issues, 1):
        print(f"{i}. [{sev}] {text}")
    print()

    # 解析并分析文档
    print("正在分析文档...")
    parser = DocxParser()
    doc = parser.parse('tests/fixtures/test_bid.docx')

    client = LLMClient()
    issues = await client.analyze(doc)

    detected = [(i.title, i.description, i.category, i.level.value) for i in issues]

    print(f"=== 检测到的问题 ({len(issues)}个) ===")
    for i, (title, desc, cat, level) in enumerate(detected, 1):
        print(f"{i}. [{level}] {title}")
        print(f"   {desc[:80]}...")
    print()

    # 漏报分析
    print("=== 漏报分析 ===")
    gt_keywords = [
        '深圳市本地业绩',
        '注册资本不低于1000万元',
        'ISO9001',
        '违约金按每日3‰',
        '预付款为合同金额的50%',
        '履约保证金为合同金额的15%',
        '中小企业价格扣除',
        '联系方式',
    ]

    # 合并所有检测到的描述和标题
    detected_combined = [(d[0] + ' ' + d[1]).lower() for d in detected]

    tp = 0
    for kw in gt_keywords:
        kw_lower = kw.lower()
        # 尝试多种匹配方式
        found = False
        for text in detected_combined:
            # 直接包含
            if kw_lower in text:
                found = True
                break
            # 去空格
            if kw_lower.replace(' ', '') in text.replace(' ', ''):
                found = True
                break
            # 部分匹配（关键词中的关键部分）
            key_parts = kw_lower.split('万元')[0].split('‰')[0].split('%')[0] if any(x in kw_lower for x in ['万元', '‰', '%']) else kw_lower
            if len(key_parts) > 5 and key_parts in text:
                found = True
                break
        status = '✓' if found else '✗'
        if found:
            tp += 1
        print(f"{status} {kw}")

    precision = tp / len(issues) if issues else 0
    recall = tp / len(gt_keywords)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print()
    print(f"=== 评估结果 ===")
    print(f"检测到: {len(issues)} 个")
    print(f"正确检测: {tp} / 8 个")
    print(f"Precision: {precision:.1%}")
    print(f"Recall: {recall:.1%}")
    print(f"F1 Score: {f1:.1%}")

if __name__ == '__main__':
    asyncio.run(test())
