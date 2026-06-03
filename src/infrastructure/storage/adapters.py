import csv
import json
from dataclasses import asdict
from abc import ABC, abstractmethod
from typing import List, Any, Optional
from src.domain.entities import Epic
from src.infrastructure.storage.transformers import HierarchyFlattener, HierarchyBuilder

class DataAdapter(ABC):
    @abstractmethod
    def export_data(self, filepath: str, data: List[Epic], active_product_name: str = None, products: List[Any] = None):
        pass

    @abstractmethod
    def import_data(self, filepath: str) -> tuple[List[Epic], Optional[str], List[Any]]:
        pass

class CSVAdapter(DataAdapter):
    def export_data(self, filepath: str, data: List[Epic], active_product_name: str = None, products: List[Any] = None):
        # CSV doesn't support active_product_name metadata easily, so we ignore it for now
        fieldnames = ['Item Type', 'ID', 'Parent ID', 'Title', 'Description', 'Team', 'Products', 'Capabilities']
        rows = HierarchyFlattener.flatten(data)
        with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def import_data(self, filepath: str) -> tuple[List[Epic], Optional[str], List[Any]]:
        with open(filepath, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            return HierarchyBuilder.build_from_flat_dict(rows), None, []

class JSONAdapter(DataAdapter):
    def export_data(self, filepath: str, data: List[Epic], active_product_name: str = None, products: List[Any] = None):
        from dataclasses import asdict
        json_data = {
            "active_product_name": active_product_name,
            "products": [asdict(p) for p in products] if products else [],
            "epics": [asdict(p) for p in data]
        }
        with open(filepath, mode='w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, indent=4)

    def import_data(self, filepath: str) -> tuple[List[Epic], Optional[str], List[Any]]:
        from src.domain.entities import Product
        with open(filepath, mode='r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
            if isinstance(data, dict) and "epics" in data:
                products = [Product(**p) for p in data.get("products", [])]
                return HierarchyBuilder.build_from_nested_dict(data["epics"]), data.get("active_product_name"), products
            else:
                # Backward compatibility for old format (just a list of epics)
                return HierarchyBuilder.build_from_nested_dict(data), None, []

class DataAdapterFactory:
    @staticmethod
    def get_adapter(extension: str) -> DataAdapter:
        if extension == '.csv':
            return CSVAdapter()
        elif extension == '.json':
            return JSONAdapter()
        else:
            raise ValueError(f"Unsupported file format: {extension}")
