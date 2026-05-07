import csv
import json
from dataclasses import asdict
from abc import ABC, abstractmethod
from typing import List, Any
from src.models.entities import Epic
from src.utils.transformers import HierarchyFlattener, HierarchyBuilder

class DataAdapter(ABC):
    @abstractmethod
    def export_data(self, filepath: str, data: List[Epic]):
        pass

    @abstractmethod
    def import_data(self, filepath: str) -> List[Epic]:
        pass

class CSVAdapter(DataAdapter):
    def export_data(self, filepath: str, data: List[Epic]):
        fieldnames = ['Item Type', 'ID', 'Parent ID', 'Title', 'Description', 'Team', 'Products', 'Capabilities']
        rows = HierarchyFlattener.flatten(data)
        with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def import_data(self, filepath: str) -> List[Epic]:
        with open(filepath, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            return HierarchyBuilder.build_from_flat_dict(rows)

class JSONAdapter(DataAdapter):
    def export_data(self, filepath: str, data: List[Epic]):
        json_data = [asdict(p) for p in data]
        with open(filepath, mode='w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, indent=4)

    def import_data(self, filepath: str) -> List[Epic]:
        with open(filepath, mode='r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
            return HierarchyBuilder.build_from_nested_dict(data)

class DataAdapterFactory:
    @staticmethod
    def get_adapter(extension: str) -> DataAdapter:
        if extension == '.csv':
            return CSVAdapter()
        elif extension == '.json':
            return JSONAdapter()
        else:
            raise ValueError(f"Unsupported file format: {extension}")
