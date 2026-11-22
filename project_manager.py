from storage import load_json, save_json

SAVE_FILE = "projects.json"


class Project:
    def __init__(self, name, subtasks=None):
        self.name = name
        self.subtasks = subtasks if subtasks is not None else []

    def add_subtask(self, name):
        self.subtasks.append({"name": name, "done": False})

    def toggle_subtask(self, index):
        self.subtasks[index]["done"] = not self.subtasks[index]["done"]

    def remove_subtask(self, index):
        self.subtasks.pop(index)

    def progress(self):
        if not self.subtasks:
            return 0.0
        done = sum(1 for t in self.subtasks if t["done"])
        return done / len(self.subtasks)

    def progress_text(self):
        done = sum(1 for t in self.subtasks if t["done"])
        return f"{done}/{len(self.subtasks)} tasks ({round(self.progress() * 100)}%)"

    def is_complete(self):
        return len(self.subtasks) > 0 and self.progress() == 1.0

    def to_dict(self):
        return {"name": self.name, "subtasks": self.subtasks}

    @staticmethod
    def from_dict(d):
        return Project(d["name"], d.get("subtasks", []))


class ProjectManager:
    def __init__(self, save_file=SAVE_FILE):
        self.save_file = save_file
        self.projects = [Project.from_dict(d) for d in load_json(save_file, [])]

    def save(self):
        save_json(self.save_file, [p.to_dict() for p in self.projects])

    def add_project(self, name):
        self.projects.append(Project(name))
        self.save()

    def remove_project(self, index):
        self.projects.pop(index)
        self.save()