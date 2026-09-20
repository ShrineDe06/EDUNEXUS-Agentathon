import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server import app, schedule_memory
from backend.services.email_service import send_study_reminder

class TestSchedulingAndProgress(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.student_id = "test_sched_progress_student"
        self.email = "student_tester@edunexus.ai"

    def test_01_schedule_memory_crud(self):
        # Create schedule directly
        sched = schedule_memory.create_schedule(
            student_id=self.student_id,
            topic="Dynamic Programming",
            mode="revise",
            date="2026-09-25",
            time_slots=["10:00 AM", "04:30 PM"],
            email=self.email,
            note="Focus on Memoization"
        )
        self.assertIsNotNone(sched["id"])
        self.assertEqual(sched["topic"], "Dynamic Programming")
        self.assertEqual(len(sched["time_slots"]), 2)

        # List schedules
        schedules = schedule_memory.list_schedules(self.student_id)
        self.assertTrue(any(s["id"] == sched["id"] for s in schedules))

        # Delete schedule
        deleted = schedule_memory.delete_schedule(sched["id"])
        self.assertTrue(deleted)

    def test_02_email_service(self):
        result = send_study_reminder(
            to_email=self.email,
            student_name="Tester",
            topic="Binary Search Trees",
            mode="test",
            date="2026-09-26",
            time_slots=["09:00 AM", "06:00 PM"],
            note="Test after lunch"
        )
        self.assertTrue(result["success"])
        self.assertTrue(result["delivered"])

    def test_03_api_schedule_endpoints(self):
        # POST /api/schedule/create
        payload = {
            "student_id": self.student_id,
            "topic": "Graph Algorithms",
            "mode": "test",
            "date": "2026-09-27",
            "time_slots": ["11:00 AM", "05:00 PM"],
            "email": self.email,
            "student_name": "Alex",
            "note": "Prepare Dijkstra and BFS",
            "send_notification": True
        }
        res = self.client.post("/api/schedule/create", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        sched_id = data["schedule"]["id"]
        self.assertIn("email_delivery", data)

        # GET /api/schedule/list
        list_res = self.client.get(f"/api/schedule/list/{self.student_id}")
        self.assertEqual(list_res.status_code, 200)
        items = list_res.json()
        self.assertTrue(any(i["id"] == sched_id for i in items))

        # DELETE /api/schedule/{sched_id}
        del_res = self.client.delete(f"/api/schedule/{sched_id}")
        self.assertEqual(del_res.status_code, 200)

    def test_04_api_progress_summary(self):
        res = self.client.get(f"/api/progress/summary/{self.student_id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("metrics", data)
        self.assertIn("topics_breakdown", data)
        self.assertIn("scheduled_timetable", data)
        self.assertIn("feedback", data)

if __name__ == "__main__":
    unittest.main()
