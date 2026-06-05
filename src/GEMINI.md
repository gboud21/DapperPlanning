# GLOBAL ARCHITECTURE: DAPPER PLANNING
- **Pattern:** Event-Driven MVC with CQRS (Command Bus + Event Dispatcher).
- **Golden Rule:** Views NEVER mutate Domain models. Controllers NEVER directly call View methods.

## BLUEPRINT: CQRS DATA FLOW
```python
# 1. VIEW triggers intent
self.command_bus.execute(SaveItemCommand(item_id=1, title='New'))

# 2. CONTROLLER mutates domain
def handle_save(self, cmd: SaveItemCommand):
    item = self.workspace.get(cmd.item_id)
    item.title = cmd.title
    self.dispatcher.dispatch(ModelHierarchyUpdatedEvent())

# 3. VIEW reacts to past-tense event
def on_update(self, event: ModelHierarchyUpdatedEvent):
    self.tree.refresh()
```
