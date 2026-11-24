#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BettaFish MD文档生成器
生成简洁的MD格式报告，减少token消耗
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path


def generate_collected_data_md(
    topic: str,
    query_results: List[Dict],
    media_results: List[Dict],
    insight_results: Dict,
    forum_discussion: List[Dict],
    output_path: Optional[str] = None
) -> str:
    """
    生成抓取信息整合MD文档
    
    Args:
        topic: 分析主题
        query_results: QueryAgent搜索结果
        media_results: MediaAgent媒体结果
        insight_results: InsightAgent分析结果
        forum_discussion: ForumEngine讨论记录
        output_path: 输出路径（可选）
        
    Returns:
        MD文档内容
    """
    lines = []
    
    lines.append(f"# {topic} - 数据采集报告")
    lines.append(f"\n> 采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"> 数据来源: WebSearch/WebFetch实时获取")
    lines.append("")
    
    lines.append("## 一、搜索结果汇总")
    lines.append("")
    
    if query_results:
        lines.append(f"共获取 {len(query_results)} 条搜索结果\n")
        
        for i, result in enumerate(query_results[:20], 1):
            title = result.get('title', '无标题')
            url = result.get('url', result.get('link', ''))
            snippet = result.get('snippet', result.get('content', ''))[:200]
            source = result.get('source', 'unknown')
            date = result.get('date', '')
            
            lines.append(f"### {i}. {title}")
            if url:
                lines.append(f"- 链接: [{url}]({url})")
            if source:
                lines.append(f"- 来源: {source}")
            if date:
                lines.append(f"- 时间: {date}")
            if snippet:
                lines.append(f"- 摘要: {snippet}...")
            lines.append("")
    else:
        lines.append("暂无搜索结果")
        lines.append("")
    
    lines.append("## 二、媒体内容分析")
    lines.append("")
    
    if media_results:
        lines.append(f"共分析 {len(media_results)} 条媒体内容\n")
        
        for i, media in enumerate(media_results[:10], 1):
            title = media.get('title', '无标题')
            url = media.get('url', '')
            platform = media.get('platform', 'unknown')
            analysis = media.get('analysis', '')
            
            lines.append(f"### {i}. {title}")
            if url:
                lines.append(f"- 链接: [{url}]({url})")
            if platform:
                lines.append(f"- 平台: {platform}")
            if analysis:
                lines.append(f"- 分析: {analysis[:300]}...")
            lines.append("")
    else:
        lines.append("暂无媒体内容")
        lines.append("")
    
    lines.append("## 三、洞察分析结果")
    lines.append("")
    
    if insight_results:
        sentiment = insight_results.get('sentiment', {})
        if sentiment:
            lines.append("### 情感分布")
            lines.append(f"- 正面: {sentiment.get('positive_count', 0)} ({sentiment.get('positive_pct', 0)}%)")
            lines.append(f"- 负面: {sentiment.get('negative_count', 0)} ({sentiment.get('negative_pct', 0)}%)")
            lines.append(f"- 中性: {sentiment.get('neutral_count', 0)} ({sentiment.get('neutral_pct', 0)}%)")
            lines.append("")
        
        keywords = insight_results.get('keywords', [])
        if keywords:
            lines.append("### 热门关键词")
            kw_list = []
            for kw in keywords[:15]:
                if isinstance(kw, tuple):
                    kw_list.append(f"{kw[0]}({kw[1]})")
                elif isinstance(kw, dict):
                    kw_list.append(f"{kw.get('keyword', '')}({kw.get('frequency', 0)})")
                else:
                    kw_list.append(str(kw))
            lines.append(", ".join(kw_list))
            lines.append("")
        
        risks = insight_results.get('risks', [])
        if risks:
            lines.append("### 风险预警")
            for risk in risks[:5]:
                lines.append(f"- {risk}")
            lines.append("")
    else:
        lines.append("暂无洞察分析")
        lines.append("")
    
    lines.append("## 四、Agent讨论记录")
    lines.append("")
    
    if forum_discussion:
        for round_num, discussion in enumerate(forum_discussion, 1):
            agent = discussion.get('agent', 'Unknown')
            findings = discussion.get('findings', {})
            key_points = findings.get('key_points', [])
            
            lines.append(f"### 第{round_num}轮 - {agent}")
            if key_points:
                for point in key_points[:5]:
                    lines.append(f"- {point}")
            lines.append("")
    else:
        lines.append("暂无讨论记录")
        lines.append("")
    
    lines.append("## 五、数据来源链接汇总")
    lines.append("")
    
    all_urls = []
    for r in query_results:
        url = r.get('url', r.get('link', ''))
        if url and url not in all_urls:
            all_urls.append(url)
    for m in media_results:
        url = m.get('url', '')
        if url and url not in all_urls:
            all_urls.append(url)
    
    if all_urls:
        lines.append(f"共 {len(all_urls)} 个数据源链接:\n")
        for i, url in enumerate(all_urls, 1):
            lines.append(f"{i}. [{url}]({url})")
    else:
        lines.append("暂无数据源链接")
    
    content = "\n".join(lines)
    
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return content


def generate_keywords_report_md(
    topic: str,
    keywords: List[Any],
    sentiment_data: Optional[Dict] = None,
    platform_stats: Optional[Dict] = None,
    output_path: Optional[str] = None
) -> str:
    """
    生成关键词报告MD文档
    
    Args:
        topic: 分析主题
        keywords: 关键词列表
        sentiment_data: 情感数据
        platform_stats: 平台统计
        output_path: 输出路径（可选）
        
    Returns:
        MD文档内容
    """
    lines = []
    
    lines.append(f"# {topic} - 关键词分析报告")
    lines.append(f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    
    lines.append("## 一、热门关键词TOP20")
    lines.append("")
    
    if keywords:
        lines.append("| 排名 | 关键词 | 频次 |")
        lines.append("|------|--------|------|")
        
        for i, kw in enumerate(keywords[:20], 1):
            if isinstance(kw, tuple):
                keyword, freq = kw[0], kw[1]
            elif isinstance(kw, dict):
                keyword = kw.get('keyword', '')
                freq = kw.get('frequency', 0)
            else:
                keyword = str(kw)
                freq = '-'
            lines.append(f"| {i} | {keyword} | {freq} |")
        lines.append("")
    else:
        lines.append("暂无关键词数据")
        lines.append("")
    
    if sentiment_data:
        lines.append("## 二、情感分析概览")
        lines.append("")
        lines.append("| 情感类型 | 数量 | 占比 |")
        lines.append("|----------|------|------|")
        
        total = sentiment_data.get('total', 0)
        pos = sentiment_data.get('positive_count', 0)
        neg = sentiment_data.get('negative_count', 0)
        neu = sentiment_data.get('neutral_count', 0)
        
        pos_pct = round(pos/total*100, 1) if total > 0 else 0
        neg_pct = round(neg/total*100, 1) if total > 0 else 0
        neu_pct = round(neu/total*100, 1) if total > 0 else 0
        
        lines.append(f"| 正面 | {pos} | {pos_pct}% |")
        lines.append(f"| 负面 | {neg} | {neg_pct}% |")
        lines.append(f"| 中性 | {neu} | {neu_pct}% |")
        lines.append(f"| **总计** | **{total}** | **100%** |")
        lines.append("")
    
    if platform_stats:
        lines.append("## 三、平台分布统计")
        lines.append("")
        lines.append("| 平台 | 提及量 | 占比 | 平均互动 |")
        lines.append("|------|--------|------|----------|")
        
        for platform, stats in platform_stats.items():
            count = stats.get('count', 0)
            pct = stats.get('percentage', 0)
            engagement = stats.get('avg_engagement', 0)
            lines.append(f"| {platform} | {count} | {pct}% | {engagement} |")
        lines.append("")
    
    lines.append("## 四、关键词建议")
    lines.append("")
    
    if keywords:
        top_keywords = []
        for kw in keywords[:5]:
            if isinstance(kw, tuple):
                top_keywords.append(kw[0])
            elif isinstance(kw, dict):
                top_keywords.append(kw.get('keyword', ''))
        
        if top_keywords:
            lines.append("**推荐关注关键词:**")
            lines.append(f"- {', '.join(top_keywords)}")
            lines.append("")
            lines.append("**内容创作建议:**")
            lines.append(f"- 围绕 \"{top_keywords[0]}\" 创建深度内容")
            lines.append(f"- 结合 \"{top_keywords[1] if len(top_keywords) > 1 else ''}\" 进行话题延伸")
            lines.append("- 关注负面关键词，及时进行舆情引导")
    
    content = "\n".join(lines)
    
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return content


def save_to_keywordsreco_folder(
    base_dir: str,
    topic: str,
    keywords: List[Any],
    sentiment_data: Optional[Dict] = None,
    platform_stats: Optional[Dict] = None
) -> str:
    """
    保存关键词报告到KeywordsRecoRe文件夹
    
    Args:
        base_dir: 调用技能的项目目录
        topic: 分析主题
        keywords: 关键词列表
        sentiment_data: 情感数据
        platform_stats: 平台统计
        
    Returns:
        保存的文件路径
    """
    safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_'))[:50]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{safe_topic}_关键词报告_{timestamp}.md"
    
    output_dir = Path(base_dir) / "KeywordsRecoRe"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / filename
    
    generate_keywords_report_md(
        topic=topic,
        keywords=keywords,
        sentiment_data=sentiment_data,
        platform_stats=platform_stats,
        output_path=str(output_path)
    )
    
    return str(output_path)


if __name__ == '__main__':
    print("BettaFish MD文档生成器")
    print("=" * 50)
    print()
    print("功能:")
    print("  1. generate_collected_data_md() - 生成抓取信息整合MD")
    print("  2. generate_keywords_report_md() - 生成关键词报告MD")
    print("  3. save_to_keywordsreco_folder() - 保存到KeywordsRecoRe文件夹")
