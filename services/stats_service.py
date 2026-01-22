import os
import json

class GlobalTracker:
    def __init__(self, stats_path=r"data\global_stats.json"):
        self.stats_path = stats_path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.stats_path):
            try:
                with open(self.stats_path, 'r') as f:
                    data = json.load(f)
                    # Migrasi jika data lama tidak punya category_stats
                    if "category_stats" not in data:
                        # Asumsikan semua deteksi sebelumnya adalah trash utk startup
                        total = data.get("total_detections", 0)
                        data["category_stats"] = {"trash": total, "bio": 0, "rov": 0}
                    return data
            except Exception:
                pass
        return {
            "total_detections": 0, 
            "total_media": 0, 
            "category_stats": {"trash": 0, "bio": 0, "rov": 0},
            "leaderboard": {}
        }

    def _save(self):
        # Create directory if not exists
        os.makedirs(os.path.dirname(self.stats_path), exist_ok=True)
        with open(self.stats_path, 'w') as f:
            json.dump(self.data, f)

    def record(self, user, detections, class_counts=None):
        if not user or user.strip() == "":
            user = "EcoCitizen"
        
        self.data["total_detections"] += detections
        self.data["total_media"] += 1
        
        # Categorize class counts if provided
        if class_counts:
            for name, count in class_counts.items():
                n = str(name).lower()
                if any(x in n for x in ['trash', 'plastic', 'waste', 'bottle', 'can']):
                    self.data["category_stats"]["trash"] += count
                elif any(x in n for x in ['bio', 'fish', 'plant', 'coral', 'biology']):
                    self.data["category_stats"]["bio"] += count
                elif any(x in n for x in ['rov', 'robot', 'vehicle']):
                    self.data["category_stats"]["rov"] += count
                else:
                    self.data["category_stats"]["trash"] += count
        else:
            # Fallback if no class_counts, assume trash for generic detections
            self.data["category_stats"]["trash"] += detections

        user_stats = self.data["leaderboard"].get(user, 0)
        self.data["leaderboard"][user] = user_stats + detections
        self._save()

    def get_stats(self):
        # Return top 5 contributors
        sorted_lb = sorted(self.data["leaderboard"].items(), key=lambda x: x[1], reverse=True)[:5]
        return {
            "total_detections": self.data["total_detections"],
            "total_media": self.data["total_media"],
            "category_stats": self.data["category_stats"],
            "leaderboard": sorted_lb
        }
