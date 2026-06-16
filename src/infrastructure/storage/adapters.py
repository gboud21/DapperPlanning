import csv
import json
from dataclasses import asdict
from abc import ABC, abstractmethod
from typing import List, Any, Optional, Dict
from src.domain.entities import Epic
from src.infrastructure.storage.transformers import HierarchyFlattener, HierarchyBuilder
from src.infrastructure.telemetry.logger import logger

class DataAdapter(ABC):
    @abstractmethod
    def export_data(self, filepath: str, data: List[Epic], active_product_name: str = None, products: List[Any] = None, members: List[Any] = None, deleted_remote_items: List[dict] = None, labels: Dict[str, Any] = None, iterations: List[Any] = None, hidden_iteration_ids: List[int] = None, shadow_hierarchy: Dict[str, Any] = None, product_teams: List[Any] = None, member_capacities: List[Any] = None):
        pass

    @abstractmethod
    def import_data(self, filepath: str) -> tuple[List[Epic], Optional[str], List[Any], List[Any], List[dict], Dict[str, Any], List[Any], List[int], Dict[str, Any], List[Any], List[Any]]:
        pass

class CSVAdapter(DataAdapter):
    def export_data(self, filepath: str, data: List[Epic], active_product_name: str = None, products: List[Any] = None, members: List[Any] = None, deleted_remote_items: List[dict] = None, labels: Dict[str, Any] = None, iterations: List[Any] = None, hidden_iteration_ids: List[int] = None, shadow_hierarchy: Dict[str, Any] = None, product_teams: List[Any] = None, member_capacities: List[Any] = None):
        # CSV doesn't support active_product_name metadata easily, so we ignore it for now
        fieldnames = ['Item Type', 'ID', 'Parent ID', 'Title', 'Description', 'Team', 'Products', 'Capabilities', 'Labels', 'Weight', 'Status', 'Assignee ID', 'Iteration ID']
        rows = HierarchyFlattener.flatten(data)
        with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def import_data(self, filepath: str) -> tuple[List[Epic], Optional[str], List[Any], List[Any], List[dict], Dict[str, Any], List[Any], List[int], Dict[str, Any], List[Any], List[Any]]:
        with open(filepath, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            return HierarchyBuilder.build_from_flat_dict(rows), None, [], [], [], {}, [], [], {}, [], []

class JSONAdapter(DataAdapter):
    def export_data(self, filepath: str, data: List[Epic], active_product_name: str = None, products: List[Any] = None, members: List[Any] = None, deleted_remote_items: List[dict] = None, labels: Dict[str, Any] = None, iterations: List[Any] = None, hidden_iteration_ids: List[int] = None, shadow_hierarchy: Dict[str, Any] = None, product_teams: List[Any] = None, member_capacities: List[Any] = None):
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
            "iterations": [asdict(i) for i in iterations] if iterations else [],
            "hidden_iteration_ids": hidden_iteration_ids or [],
            "shadow_hierarchy": shadow_hierarchy or {},
            "product_teams": [asdict(t) for t in product_teams] if product_teams else [],
            "member_capacities": [asdict(c) for c in member_capacities] if member_capacities else [],
            "epics": epics_json,
            "deleted_remote_items": deleted_remote_items or []
        }
        logger.info(f"JSONAdapter.export_data: Data dictionary keys: {list(json_data.keys())} - Epics in dict: {len(json_data['epics'])}")
        with open(filepath, mode='w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, indent=4)
        logger.info(f"Workspace successfully exported to {filepath}")

    def import_data(self, filepath: str) -> tuple[List[Epic], Optional[str], List[Any], List[Any], List[dict], Dict[str, Any], List[Any], List[int], Dict[str, Any], List[Any], List[Any]]:
        from src.domain.entities import Product, Member, Label, Iteration, ProductTeam, TeamMemberCapacity
        with open(filepath, mode='r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
            if isinstance(data, dict) and "epics" in data:
                products = [Product(**p) for p in data.get("products", [])]
                members = [Member(**m) for m in data.get("members", [])]
                labels = {name: Label(**l) for name, l in data.get("labels", {}).items()}
                iterations = [Iteration(**i) for i in data.get("iterations", [])]
                hidden_ids = data.get("hidden_iteration_ids", [])
                shadow = data.get("shadow_hierarchy", {})
                product_teams = [ProductTeam(**t) for t in data.get("product_teams", [])]
                member_capacities = [TeamMemberCapacity(**c) for c in data.get("member_capacities", [])]
                deleted = data.get("deleted_remote_items", [])
                return HierarchyBuilder.build_from_nested_dict(data["epics"]), data.get("active_product_name"), products, members, deleted, labels, iterations, hidden_ids, shadow, product_teams, member_capacities
            else:
                # Backward compatibility for old format (just a list of epics)
                return HierarchyBuilder.build_from_nested_dict(data), None, [], [], [], {}, [], [], {}, [], []

class DataAdapterFactory:
    @staticmethod
    def get_adapter(extension: str) -> DataAdapter:
        if extension == '.csv':
            return CSVAdapter()
        elif extension == '.json':
            return JSONAdapter()
        else:
            raise ValueError(f"Unsupported file format: {extension}")
