#!/usr/bin/env python3
"""
Task Tracker for nfsp00f3r-V5
Batch progress and completion tracking with efficiency metrics.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yaml

class TaskTracker:
    """Track batch progress and completion with efficiency metrics."""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.tracking_file = self.workspace_root / "docs" / "mem" / "task_tracking.json"
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing tracking data
        self.tracking_data = self.load_tracking_data()

    def load_tracking_data(self) -> Dict:
        """Load existing task tracking data."""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass

        # Default tracking structure
        return {
            "session_info": {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_sessions": 0
            },
            "batches": {},
            "efficiency_metrics": {
                "total_batches_completed": 0,
                "average_batch_time_minutes": 0,
                "success_rate_percentage": 100,
                "api_calls_saved": 0
            },
            "active_session": None
        }

    def start_session(self, session_name: str = None) -> str:
        """Start a new tracking session."""
        if not session_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"session_{timestamp}"

        session_data = {
            "session_id": session_name,
            "started": datetime.now().isoformat(),
            "status": "active",
            "batches_completed": [],
            "current_batch": None,
            "efficiency_score": 0
        }

        self.tracking_data["active_session"] = session_data
        self.tracking_data["session_info"]["total_sessions"] += 1
        self.tracking_data["session_info"]["last_updated"] = datetime.now().isoformat()

        self.save_tracking_data()

        print(f"🚀 Started tracking session: {session_name}")
        return session_name

    def start_batch(self, batch_id: str, batch_name: str, tasks: List[str]) -> bool:
        """Start tracking a new batch."""
        if not self.tracking_data.get("active_session"):
            print("❌ No active session. Start a session first.")
            return False

        batch_data = {
            "batch_id": batch_id,
            "batch_name": batch_name,
            "tasks": [
                {
                    "task_id": i + 1,
                    "description": task,
                    "status": "pending",
                    "started": None,
                    "completed": None,
                    "duration_seconds": 0
                } for i, task in enumerate(tasks)
            ],
            "started": datetime.now().isoformat(),
            "status": "in_progress",
            "completed": None,
            "total_duration_seconds": 0
        }

        self.tracking_data["batches"][batch_id] = batch_data
        self.tracking_data["active_session"]["current_batch"] = batch_id
        self.save_tracking_data()

        print(f"📁 Started batch: {batch_name} ({len(tasks)} tasks)")
        return True

    def start_task(self, batch_id: str, task_id: int) -> bool:
        """Mark a task as started."""
        if batch_id not in self.tracking_data["batches"]:
            print(f"❌ Batch {batch_id} not found")
            return False

        batch = self.tracking_data["batches"][batch_id]

        if 1 <= task_id <= len(batch["tasks"]):
            task = batch["tasks"][task_id - 1]
            task["status"] = "in_progress"
            task["started"] = datetime.now().isoformat()

            self.save_tracking_data()
            print(f"▶️  Started task {task_id}: {task['description'][:50]}...")
            return True

        print(f"❌ Invalid task ID: {task_id}")
        return False

    def complete_task(self, batch_id: str, task_id: int, success: bool = True) -> bool:
        """Mark a task as completed."""
        if batch_id not in self.tracking_data["batches"]:
            print(f"❌ Batch {batch_id} not found")
            return False

        batch = self.tracking_data["batches"][batch_id]

        if 1 <= task_id <= len(batch["tasks"]):
            task = batch["tasks"][task_id - 1]

            if task["started"]:
                start_time = datetime.fromisoformat(task["started"])
                duration = (datetime.now() - start_time).total_seconds()
                task["duration_seconds"] = round(duration, 2)

            task["status"] = "completed" if success else "failed"
            task["completed"] = datetime.now().isoformat()

            self.save_tracking_data()

            status_emoji = "✅" if success else "❌"
            print(f"{status_emoji} Completed task {task_id}: {task['description'][:50]}...")

            # Check if batch is complete
            self.check_batch_completion(batch_id)
            return True

        print(f"❌ Invalid task ID: {task_id}")
        return False

    def complete_batch(self, batch_id: str, success: bool = True) -> bool:
        """Mark entire batch as completed."""
        if batch_id not in self.tracking_data["batches"]:
            print(f"❌ Batch {batch_id} not found")
            return False

        batch = self.tracking_data["batches"][batch_id]

        # Calculate total duration
        start_time = datetime.fromisoformat(batch["started"])
        total_duration = (datetime.now() - start_time).total_seconds()

        batch["status"] = "completed" if success else "failed"
        batch["completed"] = datetime.now().isoformat()
        batch["total_duration_seconds"] = round(total_duration, 2)

        # Mark all pending tasks as completed
        for task in batch["tasks"]:
            if task["status"] == "pending":
                task["status"] = "completed" if success else "failed"
                task["completed"] = datetime.now().isoformat()

        # Update session tracking
        if self.tracking_data.get("active_session"):
            session = self.tracking_data["active_session"]
            session["batches_completed"].append(batch_id)
            if session["current_batch"] == batch_id:
                session["current_batch"] = None

        # Update efficiency metrics
        self.update_efficiency_metrics()
        self.save_tracking_data()

        duration_minutes = total_duration / 60
        status_emoji = "🎉" if success else "❌"
        print(f"{status_emoji} Batch completed: {batch['batch_name']} ({duration_minutes:.1f}m)")

        return True

    def check_batch_completion(self, batch_id: str):
        """Check if all tasks in batch are completed."""
        batch = self.tracking_data["batches"][batch_id]

        all_completed = all(
            task["status"] in ["completed", "failed"]
            for task in batch["tasks"]
        )

        if all_completed and batch["status"] == "in_progress":
            success = all(task["status"] == "completed" for task in batch["tasks"])
            self.complete_batch(batch_id, success)

    def update_efficiency_metrics(self):
        """Update overall efficiency metrics."""
        completed_batches = [
            batch for batch in self.tracking_data["batches"].values()
            if batch["status"] in ["completed", "failed"]
        ]

        if completed_batches:
            # Calculate average batch time
            total_time = sum(
                batch.get("total_duration_seconds", 0)
                for batch in completed_batches
            )
            avg_time_minutes = (total_time / len(completed_batches)) / 60

            # Calculate success rate
            successful_batches = [
                batch for batch in completed_batches
                if batch["status"] == "completed"
            ]
            success_rate = (len(successful_batches) / len(completed_batches)) * 100

            # Estimate API calls saved through batching
            total_tasks = sum(len(batch["tasks"]) for batch in completed_batches)
            estimated_api_calls_saved = max(0, total_tasks - len(completed_batches))

            self.tracking_data["efficiency_metrics"].update({
                "total_batches_completed": len(completed_batches),
                "average_batch_time_minutes": round(avg_time_minutes, 2),
                "success_rate_percentage": round(success_rate, 1),
                "api_calls_saved": estimated_api_calls_saved
            })

    def get_status_report(self) -> Dict:
        """Generate comprehensive status report."""
        active_session = self.tracking_data.get("active_session")

        report = {
            "timestamp": datetime.now().isoformat(),
            "session_active": active_session is not None,
            "efficiency_metrics": self.tracking_data["efficiency_metrics"],
            "batch_summary": {}
        }

        if active_session:
            report["current_session"] = {
                "session_id": active_session["session_id"],
                "started": active_session["started"],
                "current_batch": active_session.get("current_batch"),
                "batches_completed": len(active_session["batches_completed"])
            }

        # Batch summaries
        for batch_id, batch in self.tracking_data["batches"].items():
            completed_tasks = sum(
                1 for task in batch["tasks"]
                if task["status"] == "completed"
            )

            report["batch_summary"][batch_id] = {
                "name": batch["batch_name"],
                "status": batch["status"],
                "progress": f"{completed_tasks}/{len(batch['tasks'])}",
                "duration_minutes": round(batch.get("total_duration_seconds", 0) / 60, 1)
            }

        return report

    def print_status_report(self):
        """Print formatted status report."""
        report = self.get_status_report()

        print("\n" + "="*60)
        print("📊 TASK TRACKING STATUS REPORT")
        print("="*60)

        print(f"📅 Generated: {report['timestamp']}")
        print(f"🚀 Session Active: {report['session_active']}")

        if report.get("current_session"):
            session = report["current_session"]
            print(f"📝 Current Session: {session['session_id']}")
            print(f"🔄 Current Batch: {session.get('current_batch', 'None')}")
            print(f"✅ Batches Completed: {session['batches_completed']}")

        print("\n📊 Efficiency Metrics:")
        metrics = report["efficiency_metrics"]
        print(f"  🏆 Total Batches: {metrics['total_batches_completed']}")
        print(f"  ⏱️  Avg Time: {metrics['average_batch_time_minutes']}m")
        print(f"  ✅ Success Rate: {metrics['success_rate_percentage']}%")
        print(f"  📞 API Calls Saved: {metrics['api_calls_saved']}")

        if report["batch_summary"]:
            print("\n📁 Batch Summary:")
            for batch_id, summary in report["batch_summary"].items():
                status_emoji = {
                    "completed": "✅",
                    "in_progress": "🔄",
                    "failed": "❌",
                    "pending": "⏳"
                }.get(summary["status"], "📁")

                print(f"  {status_emoji} {summary['name']} - {summary['progress']} ({summary['duration_minutes']}m)")

        print("="*60)

    def save_tracking_data(self):
        """Save tracking data to file."""
        self.tracking_data["session_info"]["last_updated"] = datetime.now().isoformat()

        with open(self.tracking_file, 'w') as f:
            json.dump(self.tracking_data, f, indent=2)

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python task_tracker.py <command> [args]")
        print("Commands: start-session, start-batch, start-task, complete-task, complete-batch, status")
        sys.exit(1)

    command = sys.argv[1]
    workspace_root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

    tracker = TaskTracker(workspace_root)

    if command == "start-session":
        session_name = sys.argv[3] if len(sys.argv) > 3 else None
        tracker.start_session(session_name)

    elif command == "start-batch":
        if len(sys.argv) < 5:
            print("Usage: python task_tracker.py start-batch <workspace> <batch_id> <batch_name>")
            sys.exit(1)

        batch_id = sys.argv[3]
        batch_name = sys.argv[4]
        tasks = sys.argv[5:] if len(sys.argv) > 5 else ["Task 1", "Task 2", "Task 3"]
        tracker.start_batch(batch_id, batch_name, tasks)

    elif command == "complete-task":
        if len(sys.argv) < 5:
            print("Usage: python task_tracker.py complete-task <workspace> <batch_id> <task_id>")
            sys.exit(1)

        batch_id = sys.argv[3]
        task_id = int(sys.argv[4])
        success = sys.argv[5].lower() != 'false' if len(sys.argv) > 5 else True
        tracker.complete_task(batch_id, task_id, success)

    elif command == "status":
        tracker.print_status_report()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
