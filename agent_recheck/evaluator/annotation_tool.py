# -*- coding: utf-8 -*-
"""
测试集标注工具

用于标注测试数据，支持：
1. 文本高亮标注
2. 问题分类
3. 严重程度标注
4. 导出为标准格式
"""

from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import os

from .accuracy_evaluator import Annotation


class AnnotationStatus(Enum):
    """标注状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"


class AnnotationTool:
    """标注工具"""

    def __init__(self, project_name: str = "default"):
        self.project_name = project_name
        self.annotations: list[Annotation] = []
        self.documents: dict[str, dict] = {}
        self.status = AnnotationStatus.PENDING

    def load_document(self, doc_id: str, doc_path: str, content: str) -> None:
        """加载文档"""
        self.documents[doc_id] = {
            "doc_id": doc_id,
            "doc_path": doc_path,
            "content": content,
            "length": len(content),
            "loaded_at": datetime.now().isoformat(),
        }

    def add_annotation(
        self,
        doc_id: str,
        start_pos: int,
        end_pos: int,
        category: str,
        severity: str = "medium",
        notes: str = "",
        annotated_by: str = "anonymous",
    ) -> Annotation:
        """添加标注"""
        if doc_id not in self.documents:
            raise ValueError(f"Document not found: {doc_id}")

        doc = self.documents[doc_id]
        content = doc["content"]
        text = content[start_pos:end_pos]

        annotation = Annotation(
            issue_id=f"{doc_id}_{start_pos}_{end_pos}",
            text=text,
            start_pos=start_pos,
            end_pos=end_pos,
            category=category,
            severity=severity,
            is_true_positive=True,
            notes=notes,
            annotated_by=annotated_by,
            annotated_at=datetime.now(),
        )

        self.annotations.append(annotation)
        return annotation

    def update_annotation(
        self,
        issue_id: str,
        category: str = None,
        severity: str = None,
        notes: str = None,
        is_true_positive: bool = None,
    ) -> Annotation:
        """更新标注"""
        for ann in self.annotations:
            if ann.issue_id == issue_id:
                if category is not None:
                    ann.category = category
                if severity is not None:
                    ann.severity = severity
                if notes is not None:
                    ann.notes = notes
                if is_true_positive is not None:
                    ann.is_true_positive = is_true_positive
                return ann

        raise ValueError(f"Annotation not found: {issue_id}")

    def delete_annotation(self, issue_id: str) -> bool:
        """删除标注"""
        for i, ann in enumerate(self.annotations):
            if ann.issue_id == issue_id:
                self.annotations.pop(i)
                return True
        return False

    def get_annotations_by_doc(self, doc_id: str) -> list[Annotation]:
        """获取文档的标注"""
        return [a for a in self.annotations if a.issue_id.startswith(doc_id)]

    def get_annotations_by_category(self, category: str) -> list[Annotation]:
        """按类别获取标注"""
        return [a for a in self.annotations if a.category == category]

    def get_annotations_by_severity(self, severity: str) -> list[Annotation]:
        """按严重程度获取标注"""
        return [a for a in self.annotations if a.severity == severity]

    def export_to_test_case(
        self,
        doc_id: str,
        document_path: str,
        output_path: str = None,
    ) -> dict:
        """导出为测试用例格式"""
        doc_annotations = self.get_annotations_by_doc(doc_id)

        test_case = {
            "case_id": doc_id,
            "document_name": os.path.basename(document_path),
            "document_path": document_path,
            "expected_issues": [
                {
                    "issue_id": a.issue_id,
                    "text": a.text,
                    "start_pos": a.start_pos,
                    "end_pos": a.end_pos,
                    "category": a.category,
                    "severity": a.severity,
                    "is_true_positive": a.is_true_positive,
                    "notes": a.notes,
                    "annotated_by": a.annotated_by,
                    "annotated_at": a.annotated_at.isoformat(),
                }
                for a in doc_annotations
            ],
            "metadata": {
                "total_annotations": len(doc_annotations),
                "exported_at": datetime.now().isoformat(),
            },
        }

        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(test_case, f, ensure_ascii=False, indent=2)

        return test_case

    def export_all(self, output_dir: str = None) -> list[dict]:
        """导出所有测试用例"""
        output_dir = output_dir or f"./tests/fixtures/{self.project_name}"
        os.makedirs(output_dir, exist_ok=True)

        test_cases = []
        for doc_id, doc in self.documents.items():
            test_case = self.export_to_test_case(
                doc_id,
                doc["doc_path"],
                os.path.join(output_dir, f"{doc_id}.json"),
            )
            test_cases.append(test_case)

        metadata = {
            "project_name": self.project_name,
            "total_documents": len(self.documents),
            "total_annotations": len(self.annotations),
            "exported_at": datetime.now().isoformat(),
        }

        with open(os.path.join(output_dir, "_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return test_cases

    def import_from_directory(self, input_dir: str) -> int:
        """从目录导入测试用例"""
        count = 0
        for filename in os.listdir(input_dir):
            if filename.endswith(".json") and not filename.startswith("_"):
                filepath = os.path.join(input_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                doc_id = data["case_id"]
                self.documents[doc_id] = {
                    "doc_id": doc_id,
                    "doc_path": data.get("document_path", ""),
                    "content": "",
                    "loaded_at": datetime.now().isoformat(),
                }

                for ann_data in data.get("expected_issues", []):
                    annotation = Annotation(
                        issue_id=ann_data["issue_id"],
                        text=ann_data["text"],
                        start_pos=ann_data["start_pos"],
                        end_pos=ann_data["end_pos"],
                        category=ann_data["category"],
                        severity=ann_data["severity"],
                        is_true_positive=ann_data.get("is_true_positive", True),
                        notes=ann_data.get("notes", ""),
                        annotated_by=ann_data.get("annotated_by", ""),
                    )
                    self.annotations.append(annotation)

                count += 1

        return count

    def get_statistics(self) -> dict:
        """获取统计信息"""
        by_category = {}
        by_severity = {}

        for ann in self.annotations:
            by_category[ann.category] = by_category.get(ann.category, 0) + 1
            by_severity[ann.severity] = by_severity.get(ann.severity, 0) + 1

        return {
            "total_annotations": len(self.annotations),
            "total_documents": len(self.documents),
            "by_category": by_category,
            "by_severity": by_severity,
        }


class BatchAnnotationTool(AnnotationTool):
    """批量标注工具"""

    def __init__(self, project_name: str = "batch"):
        super().__init__(project_name)
        self.batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def process_directory(
        self,
        input_dir: str,
        output_dir: str = None,
        extensions: list[str] = None,
    ) -> dict:
        """处理目录下的所有文档"""
        extensions = extensions or [".docx", ".pdf"]
        output_dir = output_dir or f"./tests/fixtures/batch_{self.batch_id}"

        results = {
            "batch_id": self.batch_id,
            "processed": 0,
            "failed": 0,
            "total_annotations": 0,
        }

        from ..analyzer.parser.docx_parser import DocxParser
        from ..analyzer.parser.pdf_parser import PdfParser

        for filename in os.listdir(input_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in extensions:
                continue

            filepath = os.path.join(input_dir, filename)
            doc_id = os.path.splitext(filename)[0]

            try:
                if ext == ".docx":
                    parser = DocxParser()
                else:
                    parser = PdfParser()

                doc = parser.parse(filepath)
                content = "\n".join(p.text for p in doc.paragraphs)

                self.load_document(doc_id, filepath, content)
                results["processed"] += 1

            except Exception as e:
                results["failed"] += 1
                results[f"error_{filename}"] = str(e)

        test_cases = self.export_all(output_dir)
        results["total_annotations"] = len(self.annotations)
        results["output_dir"] = output_dir

        return results

    def auto_suggest_annotations(
        self,
        rules: list[dict],
        doc_id: str,
    ) -> list[dict]:
        """基于规则自动建议标注"""
        if doc_id not in self.documents:
            return []

        content = self.documents[doc_id]["content"]
        suggestions = []

        for rule in rules:
            patterns = rule.get("patterns", [])
            for pattern in patterns:
                import re
                try:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        suggestions.append({
                            "issue_id": f"suggest_{rule['id']}_{match.start()}",
                            "text": match.group(),
                            "start_pos": match.start(),
                            "end_pos": match.end(),
                            "category": rule.get("category", "unknown"),
                            "severity": rule.get("severity", "medium"),
                            "rule_id": rule.get("id", "unknown"),
                            "confidence": 0.9,
                        })
                except re.error:
                    continue

        return suggestions

    def review_suggestions(
        self,
        suggestions: list[dict],
        accepted: bool = True,
    ) -> int:
        """审核建议"""
        count = 0
        for suggestion in suggestions:
            if accepted:
                doc_id = suggestion["issue_id"].split("_")[1]
                self.add_annotation(
                    doc_id=doc_id,
                    start_pos=suggestion["start_pos"],
                    end_pos=suggestion["end_pos"],
                    category=suggestion["category"],
                    severity=suggestion["severity"],
                    notes=f"Auto-suggested by rule: {suggestion.get('rule_id')}",
                )
                count += 1

        return count
