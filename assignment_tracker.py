from datetime import datetime
from storage import load_json, save_json

DATE_FORMAT = "%Y-%m-%d %H:%M"      
SAVE_FILE = "assignments.json"


class Assignment:
    def __init__(self, title, deadline, description="", done=False):
        self.title = title
        self.deadline = deadline          
        self.description = description
        self.done = done

    def time_left(self):
        return self.deadline - datetime.now()

    def time_left_text(self):
        if self.done:
            return "Done ✓"
        seconds = int(self.time_left().total_seconds())
        if seconds < 0:
            return "Overdue!"
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        if days > 0:
            return f"{days}d {hours}h left"
        return f"{hours}h {minutes}m left"

    def is_urgent(self):
        secs = self.time_left().total_seconds()
        return not self.done and 0 <= secs < 24 * 3600

    def to_dict(self):
        return {
            "title": self.title,
            "deadline": self.deadline.strftime(DATE_FORMAT),
            "description": self.description,
            "done": self.done,
        }

    @staticmethod
    def from_dict(d):
        return Assignment(
            d["title"],
            datetime.strptime(d["deadline"], DATE_FORMAT),
            d.get("description", ""),
            d.get("done", False),
        )


class AssignmentTracker:
    def __init__(self, save_file=SAVE_FILE):
        self.save_file = save_file
        self.assignments = [Assignment.from_dict(d) for d in load_json(save_file, [])]

    def save(self):
        save_json(self.save_file, [a.to_dict() for a in self.assignments])

    def add(self, title, deadline_text, description=""):
        deadline = datetime.strptime(deadline_text, DATE_FORMAT)
        self.assignments.append(Assignment(title, deadline, description))
        self.save()

    def remove(self, index):
        self.assignments.pop(index)
        self.save()

    def toggle_done(self, index):
        self.assignments[index].done = not self.assignments[index].done
        self.save()

    def sorted_list(self):
        return sorted(self.assignments, key=lambda a: (a.done, a.deadline))