import csv
import json
from dataclasses import asdict
from abc import ABC, abstractmethod
from typing import List, Any, Optional
from src.domain.entities import Epic
from src.infrastructure.storage.transformers import HierarchyFlattener, HierarchyBuilder
from src.infrastructure.telemetry.logger import logger

class DataAdapter(ABC):
    @abstractmethod
    def export_data(self, filepath: str, data: List[Epic], active_product_name: str = None, products: List[Any] = None, members: List[Any] = None, deleted_remote_items: List[dict] = None, labels: Dict[str, Any] = None):
        pass

    @abstractmethod
    def import_data(self, filepath: str) -> tuple[List[Epic], Optional[str], List[Any], List[Any], List[dict], Dict[str, Any]]:
        pass

class CSVAdapter(DataAdapter):
    def export_data(self, filepath: str, data: List[Epic], active_product_name: str = None, products: List[Any] = None, members: List[Any] = None, deleted_remote_items: List[dict] = None, labels: Dict[str, Any] = None):
        # CSV doesn't support active_product_name metadata easily, so we ignore it for now
        fieldnames = ['Item Type', 'ID', 'Parent ID', 'Title', 'Description', 'Team', 'Products', 'Capabilities', 'Labels', 'Weight', 'Status', 'Assignee ID']
        rows = HierarchyFlattener.flatten(data)
        with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def import_data(self, filepath: str) -> tuple[List[Epic], Optional[str], List[Any], List[Any], List[dict], Dict[str, Any]]:
        with open(filepath, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            return HierarchyBuilder.build_from_flat_dict(rows), None, [], [], [], {}

class JSONAdapter(DataAdapter):
    def export_data(self, filepath: str, data: List[Epic], active_product_name: str = None, products: List[Any] = None, members: List[Any] = None, deleted_remote_items: List[dict] = None, labels: Dict[str, Any] = None):
        from dataclasses import asdict
        
        def _serialize_recursive(item):
            item_type = type(item).__name__
            if item_type == "Epic":
                logger.info(f"Serializing Epic: {item.title} (ID: {item.id}) - Features count: {len(item.features)}")
                for feature in item.features:
                    _serialize_recursive(feature)
            elif item_type == "Feature":
                logger.info(f"Serializing Feature: {item.title} (ID: {item.id}) - Stories count: {len(item.stories)}")
                for story in item.stories:
                    _serialize_recursive(story)
            elif item_type == "Story":
                logger.info(f"Serializing Story: {item.title} (ID: {item.id})")
            return asdict(item)

        logger.info(f"JSONAdapter.export_data: Starting traversal of {len(data)} root items.")
        epics_json = [_serialize_recursive(p) for p in data]
        
        json_data = {
            "active_product_name": active_product_name,
            "products": [asdict(p) for p in products] if products else [],
            "members": [asdict(m) for m in members] if members else [],
            "labels": {name: asdict(label) for name, label in labels.items()} if labels else {},
            "epics": epics_json,
            "deleted_remote_items": deleted_remote_items or []
        }
        logger.info(f"JSONAdapter.export_data: Data dictionary keys: {list(json_data.keys())} - Epics in dict: {len(json_data['epics'])}")
        with open(filepath, mode='w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, indent=4)
        logger.info(f"Workspace successfully exported to {filepath}")

    def import_data(self, filepath: str) -> tuple[List[Epic], Optional[str], List[Any], List[Any], List[dict], Dict[str, Any]]:
        from src.domain.entities import Product, Member, Label
        with open(filepath, mode='r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
            if isinstance(data, dict) and "epics" in data:
                products = [Product(**p) for p in data.get("products", [])]
                members = [Member(**m) for m in data.get("members", [])]
                labels = {name: Label(**l) for name, l in data.get("labels", {}).items()}
                deleted = data.get("deleted_remote_items", [])
                return HierarchyBuilder.build_from_nested_dict(data["epics"]), data.get("active_product_name"), products, members, deleted, labels
            else:
                # Backward compatibility for old format (just a list of epics)
                return HierarchyBuilder.build_from_nested_dict(data), None, [], [], [], {}

class DataAdapterFactory:
    @staticmethod
    def get_adapter(extension: str) -> DataAdapter:
        if extension == '.csv':
            return CSVAdapter()
        elif extension == '.json':
            return JSONAdapter()
        else:
            raise ValueError(f"Unsupported file format: {extension}")
